"""Cleanup service for temporary files and old analysis data."""
import os
import time
import logging
from pathlib import Path
from config import UPLOAD_DIR, OUTPUT_DIR

logger = logging.getLogger(__name__)


def cleanup_old_files(directory: str, max_age_hours: int = 24) -> int:
    """Remove files older than max_age_hours. Returns count of removed files."""
    removed = 0
    cutoff = time.time() - (max_age_hours * 3600)
    if not os.path.isdir(directory):
        return 0
    for root, dirs, files in os.walk(directory, topdown=False):
        for fname in files:
            fpath = os.path.join(root, fname)
            try:
                if os.path.getmtime(fpath) < cutoff:
                    os.remove(fpath)
                    removed += 1
            except OSError as e:
                logger.warning("cleanup: failed to remove %s: %s", fpath, e)
        # Remove empty directories
        for dname in dirs:
            dpath = os.path.join(root, dname)
            try:
                if not os.listdir(dpath):
                    os.rmdir(dpath)
            except OSError:
                pass
    return removed


def run_cleanup(max_age_hours: int = 24):
    """Run cleanup on all temporary directories."""
    u = cleanup_old_files(UPLOAD_DIR, max_age_hours)
    o = cleanup_old_files(OUTPUT_DIR, max_age_hours)
    logger.info("Cleanup complete: removed %d uploads, %d outputs", u, o)
    return u + o
