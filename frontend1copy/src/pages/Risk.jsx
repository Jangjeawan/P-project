// src/pages/Risk.jsx
import { useState, useEffect } from "react";
import api from "../api/axiosInstance";

export default function Risk() {
  /* ===============================
     리스크 설정 상태값 (기존 그대로)
  =============================== */
  const [riskStock, setRiskStock] = useState("ALL");
  const [riskMaxQty, setRiskMaxQty] = useState("");
  const [riskMaxPct, setRiskMaxPct] = useState("");
  const [riskMaxDailyBuy, setRiskMaxDailyBuy] = useState("");
  const [riskActive, setRiskActive] = useState("on");
  const [riskKey, setRiskKey] = useState("");
  const [riskList, setRiskList] = useState([]);

  /* ===============================
     리스크 저장 (기존 그대로)
  =============================== */
  const saveRisk = async () => {
    try {
      const stock = riskStock || "ALL";

      const payload = {
        max_position_shares: riskMaxQty ? Number(riskMaxQty) : null,
        max_weight_pct: riskMaxPct ? Number(riskMaxPct) : null,
        max_daily_buy_amount: riskMaxDailyBuy
          ? Number(riskMaxDailyBuy)
          : null,
        active: riskActive === "on",
      };

      const headers = {};
      if (riskKey) headers["X-API-Key"] = riskKey;

      await api.put(`/settings/risk/${stock}`, payload, { headers });

      alert("리스크 규칙 저장됨");
      loadRisk();
    } catch (err) {
      console.error(err);
      alert("리스크 저장 실패");
    }
  };

  /* ===============================
     리스크 조회 (기존 그대로)
  =============================== */
  const loadRisk = async () => {
    try {
      const res = await api.get("/settings/risk");
      setRiskList(res.data);
    } catch (_) {}
  };

  useEffect(() => {
    loadRisk();
  }, []);

  return (
    <>
      {/* ===============================
          PAGE HEADER
      =============================== */}
      <div className="dash-header">
        <div className="dash-title">리스크 설정</div>
        <div className="dash-sub">
          종목별 / 전체 리스크 한도 관리
        </div>
      </div>

      {/* ===============================
          리스크 설정 폼
      =============================== */}
      <section className="dash-card">
        <div className="dash-card-header">
          <h2>리스크 규칙 설정</h2>
          <button onClick={loadRisk}>새로고침</button>
        </div>

        <div className="dash-grid2">
          <input
            placeholder="종목코드 또는 ALL"
            value={riskStock}
            onChange={(e) => setRiskStock(e.target.value)}
          />

          <input
            placeholder="최대 보유 수량"
            value={riskMaxQty}
            onChange={(e) => setRiskMaxQty(e.target.value)}
          />

          <input
            placeholder="최대 비중 (%)"
            value={riskMaxPct}
            onChange={(e) => setRiskMaxPct(e.target.value)}
          />

          <input
            placeholder="일간 최대 매수금액"
            value={riskMaxDailyBuy}
            onChange={(e) => setRiskMaxDailyBuy(e.target.value)}
          />

          <input
            placeholder="API Key (선택)"
            value={riskKey}
            onChange={(e) => setRiskKey(e.target.value)}
          />

          <select
            value={riskActive}
            onChange={(e) => setRiskActive(e.target.value)}
          >
            <option value="on">활성</option>
            <option value="off">비활성</option>
          </select>
        </div>

        <button className="dash-btn" onClick={saveRisk}>
          저장
        </button>
      </section>

      {/* ===============================
          리스크 목록
      =============================== */}
      <section className="dash-card">
        <h2>등록된 리스크 규칙</h2>

        <table className="dash-table">
          <thead>
            <tr>
              <th>종목</th>
              <th>최대 수량</th>
              <th>최대 비중 (%)</th>
              <th>일간 매수 한도</th>
              <th>활성</th>
            </tr>
          </thead>
          <tbody>
            {riskList.map((x) => (
              <tr key={x.stock_code}>
                <td>{x.stock_code}</td>
                <td>{x.max_position_shares}</td>
                <td>{x.max_weight_pct}</td>
                <td>{x.max_daily_buy_amount}</td>
                <td>{x.active ? "ON" : "OFF"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}