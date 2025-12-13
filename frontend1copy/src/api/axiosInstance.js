// src/api/axiosInstance.js
import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000",
});

// 모든 요청에 자동으로 토큰 포함
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("stuckai_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;