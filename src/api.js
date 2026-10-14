import axios from 'axios';

const api = axios.create({ baseURL: 'http://localhost:8000/api' });

// ── Projects ──────────────────────────────────────────────────────────────
export const getProjects      = ()         => api.get('/projects').then(r => r.data);
export const createProject    = (data)     => api.post('/projects', data).then(r => r.data);
export const getProject       = (id)       => api.get(`/projects/${id}`).then(r => r.data);
export const updateProject    = (id, data) => api.put(`/projects/${id}`, data).then(r => r.data);
export const deleteProject    = (id)       => api.delete(`/projects/${id}`).then(r => r.data);

// ── Upload images ─────────────────────────────────────────────────────────
export const uploadImages = (projectId, imageType, files) => {
  const form = new FormData();
  form.append('image_type', imageType);
  Array.from(files).forEach(f => form.append('files', f));
  return api.post(`/projects/${projectId}/upload`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data);
};

// ── Analysis ──────────────────────────────────────────────────────────────
export const analyzeImages    = (projectId) => api.post(`/projects/${projectId}/analyze`).then(r => r.data);
export const getDetections    = (projectId, imageType) =>
  api.get(`/projects/${projectId}/detections`, { params: imageType ? { image_type: imageType } : {} }).then(r => r.data);

// ── Reports ───────────────────────────────────────────────────────────────
export const saveReport       = (projectId, data) => api.post(`/projects/${projectId}/report`, data).then(r => r.data);
export const getReport        = (projectId)       => api.get(`/projects/${projectId}/report`).then(r => r.data);
export const getAllReports     = ()                => api.get('/reports').then(r => r.data);

export const IMAGE_BASE = 'http://localhost:8000';
