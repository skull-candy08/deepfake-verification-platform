"""
Media preprocessing utilities for the Deepfake Verification Platform.

Provides helpers to detect media types, extract video frames and audio
tracks, and normalise images before they enter the forensic pipeline.
"""

from __future__ import annotations

import logging
import os
import subprocess
from typing import Optional

import cv2
import numpy as np
from PIL import Image

from backend.config import ALLOWED_EXTENSIONS, IMAGE_MAX_DIMENSION

logger = logging.getLogger(__name__)


# ── public helpers ──────────────────────────────────────────────────────────


def detect_media_type(file_path: str) -> str:
    """Determine the media category of *file_path* by its extension.

    Args:
        file_path: Absolute or relative path to the file.

    Returns:
        One of ``'image'``, ``'video'``, or ``'audio'``.

    Raises:
        ValueError: If the extension does not match any known media type.
    """
    ext = _get_extension(file_path)
    for media_type, extensions in ALLOWED_EXTENSIONS.items():
        if ext in extensions:
            logger.debug("Detected media type '%s' for %s", media_type, file_path)
            return media_type

    raise ValueError(
        f"Unsupported file extension '.{ext}'. "
        f"Allowed extensions: {sorted(ALLOWED_EXTENSIONS)}"
    )


def extract_frames(
    video_path: str,
    output_dir: str,
    fps: int = 1,
) -> list[str]:
    """Extract frames from a video at a given sampling rate.

    Uses OpenCV's :pymod:`cv2` to decode the video and write individual
    JPEG frames into *output_dir*.

    Args:
        video_path: Path to the source video file.
        output_dir: Directory to write extracted frame images.
        fps: Number of frames to capture per second of video.

    Returns:
        Sorted list of absolute paths to the extracted JPEG frames.

    Raises:
        FileNotFoundError: If *video_path* does not exist.
        RuntimeError: If OpenCV cannot open the video.
    """
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"OpenCV failed to open video: {video_path}")

    video_fps: float = cap.get(cv2.CAP_PROP_FPS)
    if video_fps <= 0:
        logger.warning(
            "Could not determine FPS for %s; defaulting to 30.", video_path
        )
        video_fps = 30.0

    # Calculate the interval (in source frames) between captures.
    frame_interval: int = max(1, int(round(video_fps / fps)))

    frame_paths: list[str] = []
    frame_idx: int = 0
    saved_count: int = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            frame_filename = f"frame_{saved_count:06d}.jpg"
            frame_path = os.path.join(output_dir, frame_filename)
            cv2.imwrite(frame_path, frame)
            frame_paths.append(os.path.abspath(frame_path))
            saved_count += 1

        frame_idx += 1

    cap.release()

    logger.info(
        "Extracted %d frames from %s (interval=%d, target_fps=%d)",
        saved_count,
        video_path,
        frame_interval,
        fps,
    )
    return sorted(frame_paths)


def extract_audio(video_path: str, output_path: str) -> Optional[str]:
    """Demux the audio track from a video file using FFmpeg.

    Args:
        video_path: Path to the source video file.
        output_path: Desired path for the extracted audio file (e.g. ``.wav``).

    Returns:
        The *output_path* on success, or ``None`` if the video contains no
        audio track or FFmpeg is not available.

    Raises:
        FileNotFoundError: If *video_path* does not exist.
    """
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",                # overwrite output without asking
        "-i", video_path,
        "-vn",               # drop video stream
        "-acodec", "pcm_s16le",
        "-ar", "16000",      # 16 kHz mono – good for analysis
        "-ac", "1",
        output_path,
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
            check=False,
        )
    except FileNotFoundError:
        logger.error(
            "FFmpeg is not installed or not on PATH. Audio extraction skipped."
        )
        return None

    if result.returncode != 0:
        stderr_text = result.stderr.decode("utf-8", errors="replace")
        # FFmpeg returns non-zero when there is no audio stream.
        if "does not contain any stream" in stderr_text or "Output file is empty" in stderr_text:
            logger.warning("No audio stream found in %s.", video_path)
            return None
        logger.error("FFmpeg error:\n%s", stderr_text)
        return None

    if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
        logger.warning("Audio extraction produced an empty file for %s.", video_path)
        return None

    logger.info("Audio extracted to %s", output_path)
    return output_path


def normalize_image(
    image_path: str,
    max_dim: int = IMAGE_MAX_DIMENSION,
) -> np.ndarray:
    """Load an image and resize it if either dimension exceeds *max_dim*.

    The aspect ratio is preserved.  The returned array is in BGR colour
    space (OpenCV convention) so it can be fed directly into OpenCV-based
    analysis modules.

    Args:
        image_path: Path to the image file.
        max_dim: Maximum allowed width **or** height in pixels.

    Returns:
        A ``numpy.ndarray`` of the (potentially resized) image in BGR.

    Raises:
        FileNotFoundError: If *image_path* does not exist.
        ValueError: If the file cannot be decoded as an image.
    """
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    # Use Pillow for robust format support, then convert to numpy/OpenCV.
    pil_image = Image.open(image_path)
    pil_image = pil_image.convert("RGB")  # ensure 3-channel

    width, height = pil_image.size

    if width > max_dim or height > max_dim:
        scale = max_dim / max(width, height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        pil_image = pil_image.resize(
            (new_width, new_height), Image.LANCZOS
        )
        logger.info(
            "Resized %s from %dx%d → %dx%d",
            image_path,
            width,
            height,
            new_width,
            new_height,
        )

    # Convert RGB (Pillow) → BGR (OpenCV)
    img_array: np.ndarray = np.array(pil_image)[:, :, ::-1].copy()
    return img_array


# ── private helpers ─────────────────────────────────────────────────────────


def _get_extension(file_path: str) -> str:
    """Return the lower-cased extension without the leading dot."""
    _, ext = os.path.splitext(file_path)
    return ext.lstrip(".").lower()
