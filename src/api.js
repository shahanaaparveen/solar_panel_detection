import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
const api = axios.create({ baseURL: API_BASE_URL });
let accessToken = null;

api.interceptors.request.use(config => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`;
  return config;
});

// The host OIDC integration supplies its short-lived access token in memory.
export const setAccessToken = token => { accessToken = token || null; };

export const getProjectImageObjectUrl = async (projectId, imageId) => {
  const response = await api.get(`/projects/${projectId}/images/${imageId}/content`, { responseType: 'blob' });
  return URL.createObjectURL(response.data);
};

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
export const analyzeImages    = (projectId, requestId) => api.post(`/projects/${projectId}/analyze`, null, { headers: { 'Idempotency-Key': requestId } }).then(r => r.data);
export const getAnalysisJob   = (projectId, jobId) => api.get(`/projects/${projectId}/analysis/${jobId}`).then(r => r.data);
export const retryAnalysis    = (projectId, jobId) => api.post(`/projects/${projectId}/analysis/${jobId}/retry`).then(r => r.data);
export const getDetections    = (projectId, imageType, jobId) =>
  api.get(`/projects/${projectId}/detections`, { params: { ...(imageType ? { image_type: imageType } : {}), ...(jobId ? { job_id: jobId } : {}) } }).then(r => r.data);
export const getPanels        = (projectId) => api.get(`/projects/${projectId}/panels`).then(r => r.data);
export const getFindings      = (projectId, jobId) => api.get(`/projects/${projectId}/findings`, { params: jobId ? { job_id: jobId } : {} }).then(r => r.data);
export const registerImages   = (projectId, rgbImageId, thermalImageId) => api.post(`/projects/${projectId}/registration`, null, { params: { reference_image_id: rgbImageId, moving_image_id: thermalImageId } }).then(r => r.data);
export const autoRegisterImages = (projectId, options = {}) => api.post(`/projects/${projectId}/registration/auto`, options).then(r => r.data);
export const getRegistrationOverview = (projectId) => api.get(`/projects/${projectId}/registration`).then(r => r.data);
export const analyzeProjectMapping = (projectId, options = {}) => api.post(`/projects/${projectId}/mapping/analyze`, options).then(r => r.data);
export const getProjectMapping = (projectId, jobId) => api.get(`/projects/${projectId}/mapping`, { params: jobId ? { job_id: jobId } : {} }).then(r => r.data);
export const getMappingQuality = (projectId, jobId) => api.get(`/projects/${projectId}/mapping/quality`, { params: jobId ? { job_id: jobId } : {} }).then(r => r.data);
export const analyzeProjectAssociation = (projectId, options = {}) => api.post(`/projects/${projectId}/association/analyze`, options).then(r => r.data);
export const getAssociationSummary = (projectId, jobId) => api.get(`/projects/${projectId}/association/summary`, { params: jobId ? { job_id: jobId } : {} }).then(r => r.data);
export const getModelReadiness = () => api.get('/models/readiness').then(r => r.data);

// ── Reports ───────────────────────────────────────────────────────────────
export const saveReport       = (projectId, data) => api.post(`/projects/${projectId}/report`, data).then(r => r.data);
export const getReport        = (projectId)       => api.get(`/projects/${projectId}/report`).then(r => r.data);
export const getAllReports     = ()                => api.get('/reports').then(r => r.data);
