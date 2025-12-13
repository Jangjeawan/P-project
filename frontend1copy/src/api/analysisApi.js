// src/api/analysisApi.js
import api from "./axiosInstance";

export const fetchChart = (stockCode) =>
  api.get("/chart", {
    params: { stock_code: stockCode, limit: 120 },
  }).then(res => res.data);

export const fetchIndicator = (stockCode) =>
  api.get("/indicator", {
    params: { stock_code: stockCode },
  }).then(res => res.data);