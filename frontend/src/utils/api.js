import axios from 'axios';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 120000,
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

/**
 * Wraps API calls with consistent error handling.
 */
async function apiRequest(requestFn) {
  try {
    const response = await requestFn();
    return response.data;
  } catch (error) {
    if (error.response) {
      const message =
        error.response.data?.error ||
        error.response.data?.message ||
        `Server error (${error.response.status})`;
      throw new Error(message);
    } else if (error.request) {
      throw new Error(
        'Unable to reach the analysis server. Please ensure the backend is running on port 5000.'
      );
    } else {
      throw new Error(error.message || 'An unexpected error occurred.');
    }
  }
}

/**
 * Upload a media file to the backend.
 * @param {File} file - The file to upload.
 * @param {function} onUploadProgress - Progress callback receiving a percentage (0-100).
 * @returns {Promise<object>} - The upload response containing file_id, etc.
 */
export async function uploadMedia(file, onUploadProgress) {
  const formData = new FormData();
  formData.append('file', file);

  return apiRequest(() =>
    apiClient.post('/api/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (onUploadProgress && progressEvent.total) {
          const percent = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onUploadProgress(percent);
        }
      },
    })
  );
}

/**
 * Trigger analysis on an uploaded file.
 * @param {string} fileId - The ID returned from uploadMedia.
 * @returns {Promise<object>} - The full analysis results.
 */
export async function analyzeMedia(fileId) {
  return apiRequest(() =>
    apiClient.post('/api/analyze', { file_id: fileId })
  );
}

/**
 * Build the full report download URL.
 * @param {string} reportId - The report identifier.
 * @returns {string}
 */
export function getReportUrl(reportId) {
  return `${BASE_URL}/api/report/${reportId}`;
}

export default apiClient;
