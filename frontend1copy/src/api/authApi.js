// src/api/authApi.js
import api from "./axiosInstance";

// 회원가입
export const registerUser = async (username, password, name) => {
  const res = await api.post("/signup", { username, password, name });
  return res.data;
};

// 로그인
export const loginUser = async (username, password) => {
  const res = await api.post("/login", { username, password });

  // FastAPI 응답: { token, name }
  localStorage.setItem("stuckai_token", res.data.token);
  localStorage.setItem("stuckai_name", res.data.name);

  return res.data;
};

// 자동 로그인 체크
export const checkAuth = async () => {
  const token = localStorage.getItem("stuckai_token");
  if (!token) return null;

  const res = await api.get(`/me?token=${token}`);
  return res.data;
};

// 로그아웃
export const logoutUser = () => {
  localStorage.removeItem("stuckai_token");
  localStorage.removeItem("stuckai_name");
};