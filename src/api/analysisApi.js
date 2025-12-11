import api from "./axiosInstance";

// 차트
export const fetchChart = async (stockCode, limit = 200) => {
  const res = await api.get("/chart", {
    params: { stock_code: stockCode, limit }
  });
  return res.data;
};

// 기술 지표
export const fetchIndicator = async (stockCode) => {
  const res = await api.get("/indicator", {
    params: { stock_code: stockCode }
  });
  return res.data;
};

// 예측/거래 히스토리
export const fetchPredictHistory = async (limit = 50) => {
  const res = await api.get("/history", { params: { limit } });
  return res.data.history;
};