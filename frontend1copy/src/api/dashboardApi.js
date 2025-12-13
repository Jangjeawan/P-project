import api from "./axiosInstance";

/* ==============================
   1) 계좌 잔고 조회
   GET /accounts/balance
============================== */
export const getBalance = async () => {
  const res = await api.get("/accounts/balance");
  return res.data;
};

/* ==============================
   2) 시장가 주문
   POST /orders/market
============================== */
export const sendMarketOrder = async (payload) => {
  const res = await api.post("/orders/market", payload);
  return res.data;
};

/* ==============================
   3) 거래 내역 조회
   GET /orders/history
============================== */
export const getTradeHistory = async (symbol = "", limit = 100) => {
  let url = `/orders/history?limit=${limit}`;
  if (symbol.trim()) url += `&stock_code=${symbol.trim()}`;

  const res = await api.get(url);
  return res.data;
};

/* ==============================
   4) 리스크 설정 조회
   GET /settings/risk
============================== */
export const getRiskSettings = async () => {
  const res = await api.get("/settings/risk");
  return res.data;
};

/* ==============================
   5) 리스크 설정 저장
   PUT /settings/risk/{code}
============================== */
export const saveRiskSetting = async (code, payload, apiKey = "") => {
  const headers = {};
  if (apiKey) headers["X-API-Key"] = apiKey;

  const res = await api.put(`/settings/risk/${code}`, payload, { headers });
  return res.data;
};

export const runAutoTrade = async (apiKey = "") => {
  const headers = {};
  if (apiKey) headers["X-API-Key"] = apiKey;

  const res = await api.post("/trade/auto", {}, { headers });
  return res.data;
};

/* ==============================
   7) 성과 요약 조회 (최근 X일)
   GET /metrics/performance?days=30
============================== */
export const getPerformanceSummary = async (days = 30) => {
  const res = await api.get("/metrics/performance", {
    params: { days },
  });
  return res.data;   // { summary: {...}, snapshots: [...] }
};