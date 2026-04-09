import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({ baseURL: BASE_URL });

// Attach JWT from in-memory store (never localStorage)
let _token = null;
export const setToken = (t) => { _token = t; };
export const clearToken = () => { _token = null; };

api.interceptors.request.use((config) => {
  if (_token) config.headers.Authorization = `Bearer ${_token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      clearToken();
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

// Auth
export const login = (email, password) =>
  api.post("/api/auth/login", { email, password });

// Patients
export const getPatients = (params) => api.get("/api/patients", { params });
export const getPatient = (id) => api.get(`/api/patients/${id}`);
export const createPatient = (data) => api.post("/api/patients", data);
export const updatePatient = (id, data) => api.patch(`/api/patients/${id}`, data);
export const deletePatient = (id) => api.delete(`/api/patients/${id}`);

// Medications
export const getPatientMedications = (patientId) =>
  api.get(`/api/patients/${patientId}/medications`);

// Dispensing records
export const getDispensingRecords = (patientMedId) =>
  api.get(`/api/patient-medications/${patientMedId}/dispensing-records`);

// Nudge campaigns
export const getNudgeCampaigns = (params) => api.get("/api/analytics/campaigns", { params });

// Escalations
export const getEscalations = (params) => api.get("/api/escalations", { params });
export const updateEscalation = (id, data) => api.patch(`/api/escalations/${id}`, data);

// Prescriptions
export const getPrescriptions = (params) => api.get("/api/prescriptions", { params });
export const getPrescription = (id) => api.get(`/api/prescriptions/${id}`);
export const confirmPrescription = (id, data) =>
  api.patch(`/api/prescriptions/${id}/confirm`, data);
export const rejectPrescription = (id, data) =>
  api.patch(`/api/prescriptions/${id}/reject`, data);
export const uploadPrescription = (patientId, formData) =>
  api.post(`/api/prescriptions?patient_id=${patientId}`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });

// Analytics
export const getAdherenceAnalytics = (params) =>
  api.get("/api/analytics/adherence", { params });
export const getEscalationAnalytics = (params) =>
  api.get("/api/analytics/escalations", { params });

export default api;
