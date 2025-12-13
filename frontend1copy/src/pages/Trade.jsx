// src/pages/Trade.jsx
import { useEffect, useState } from "react";
import api from "../api/axiosInstance";

export default function Trade() {
  /* ===============================
     자동매매 ON / OFF (프론트 상태)
  =============================== */
  const [autoTradeEnabled, setAutoTradeEnabled] = useState(false);
  const [autoTradeResult, setAutoTradeResult] = useState(null);

  const runAutoTrade = async () => {
  if (!autoTradeEnabled) {
    alert("자동매매 OFF입니다.");
    return;
  }

  try {
    const API_KEY = import.meta.env.VITE_API_KEY;
    const res = await api.post(
      "/trade/auto",
      {},
      { headers: { "X-API-Key": API_KEY } }
    );
    setAutoTradeResult(res.data);
    alert("자동매매 1회 실행 완료");
    console.log(res.data); // 로그 확인용
  } catch (err) {
    alert("자동매매 실행 실패");
    console.error(err);
  }
};

  /* ===============================
     성과 요약 (🔥 기존 대시보드 코드 그대로)
  =============================== */
  const [perf, setPerf] = useState(null);
  const [perfSnapshots, setPerfSnapshots] = useState([]);

  const fetchPerformance = async () => {
    try {
      const res = await api.get("/metrics/performance", {
        params: { days: 30 },
      });
      setPerf(res.data.summary);
      setPerfSnapshots(res.data.snapshots || []);
    } catch (err) {
      alert("성과 요약 조회 실패");
    }
  };
  const loadAutoTradeConfig = async () => {
  try {
    const res = await api.get("/auto-trade/config");
    if (typeof res.data.enabled === "boolean") {
      setAutoTradeEnabled(res.data.enabled);
    }
  } catch (err) {
    alert("자동매매 상태 로드 실패");
  }
};
const toggleAutoTrade = async () => {
  const next = !autoTradeEnabled;
  setAutoTradeEnabled(next); // UI 선반영

  try {
    const API_KEY = import.meta.env.VITE_API_KEY;
    await api.put(
      "/auto-trade/config",
      { enabled: next },
      { headers: { "X-API-Key": API_KEY } }
    );
  } catch (err) {
    setAutoTradeEnabled(!next); // 실패 시 롤백
    alert("자동매매 설정 저장 실패");
  }
};

  useEffect(() => {
    fetchPerformance();
    loadAutoTradeConfig();
  }, []);

  return (
    <>
      {/* ===============================
          PAGE HEADER
      =============================== */}
      <div className="dash-header">
        <div className="dash-title">자동매매</div>
        <div className="dash-sub">
          강화학습 기반 자동매매 상태 및 성과 요약
        </div>
      </div>

      {/* ===============================
          자동매매 ON / OFF
      =============================== */}
      <section className="dash-card">
        <h2 className="dash-flex-between">
          자동매매 상태
          <label className="dash-switch">
            <input
              type="checkbox"
              checked={autoTradeEnabled}
              onChange={toggleAutoTrade}
            />
            <span></span>
          </label>
        </h2>

        <p className="dash-small">
          현재 상태:{" "}
          <strong>{autoTradeEnabled ? "ON (활성)" : "OFF (비활성)"}</strong>
        </p>
  <button className="dash-btn" onClick={runAutoTrade}>
  수동 1회 실행
</button>

{!autoTradeEnabled && (
  <p className="dash-small" style={{ color: "red" }}>
    자동매매가 OFF 상태라 실행할 수 없습니다.
  </p>)}
       
      </section>
      {autoTradeResult && (
   <div className="dash-auto-summary" style={{ marginTop: 16 }}>
  <strong style={{ fontSize: 16 }}>📄 자동매매 결과 요약</strong>

  <div
    style={{
      marginTop: 8,
      padding: 12,
      maxHeight: 400,       // 최대 높이 지정
      overflowY: "auto",    // 스크롤 보장
      backgroundColor: "#1f1f1f",
      borderRadius: 8,
      color: "#fff",        // 글씨 흰색
      boxShadow: "0 2px 6px rgba(0,0,0,0.3)",
    }}
  >
    {autoTradeResult && autoTradeResult.length > 0 ? (
      autoTradeResult.map((item, idx) => {
        let actionText = "";
        let actionColor = "#fff";

        if (item.action > 0.3) {
          actionText = "매수";
          actionColor = "#22c55e"; // 초록
        } else if (item.action < -0.3) {
          actionText = "매도";
          actionColor = "#ef4444"; // 빨강
        } else {
          actionText = "관망";
          actionColor = "#facc15"; // 노랑
        }

        return (
          <div
            key={idx}
            style={{
              padding: 8,
              marginBottom: 8,
              border: "1px solid #333",
              borderRadius: 6,
              backgroundColor: "#2a2a2a",
            }}
          >
            <div>
              <strong>{item.stock}</strong> ({item.code || "코드 없음"})
            </div>
            <div>
              SAC 모델 행동값: <strong>{item.action.toFixed(2)}</strong> →{" "}
              <strong style={{ color: actionColor }}>{actionText}</strong>
            </div>
            <div>예상 보상: {item.reward?.toFixed(2) || "-"}</div>
          </div>
        );
      })
    ) : (
      <div>결과가 없습니다.</div>
    )}
  </div>
</div>
)}
      

      {/* ===============================
          성과 요약 (🔥 그대로 이식)
      =============================== */}
      <section className="dash-card">
        <div className="dash-card-header">
          <h2>성과 요약 (최근 30일)</h2>
          <button onClick={fetchPerformance}>새로고침</button>
        </div>

        {perf && (
          <div className="dash-summary">
            시작자산:{" "}
            {Math.round(perf.start_value || 0).toLocaleString()}원 ·
            현재자산:{" "}
            {Math.round(perf.end_value || 0).toLocaleString()}원 ·
            누적수익률: {(perf.total_return_pct || 0).toFixed(2)}% ·
            최대낙폭: {(perf.max_drawdown_pct || 0).toFixed(2)}% ·
            누적손익:{" "}
            {(perf.pnl_sum >= 0 ? "+" : "") +
              Math.round(perf.pnl_sum || 0).toLocaleString()}
            원
          </div>
        )}

        {perfSnapshots.length > 0 && (
          <table className="dash-table">
            <thead>
              <tr>
                <th>날짜</th>
                <th>총자산</th>
                <th>예수금</th>
                <th>총매입</th>
                <th>평가금액</th>
                <th>총손익</th>
              </tr>
            </thead>
            <tbody>
              {perfSnapshots.map((snap) => {
                const dt = new Date(snap.timestamp);
                return (
                  <tr key={snap.timestamp}>
                    <td>{dt.toLocaleString()}</td>
                    <td>{Math.round(snap.total_value).toLocaleString()}</td>
                    <td>{Math.round(snap.cash).toLocaleString()}</td>
                    <td>{Math.round(snap.total_buy_amount).toLocaleString()}</td>
                    <td>{Math.round(snap.total_eval_amount).toLocaleString()}</td>
                    <td>
                      {(Math.round(snap.total_pnl) >= 0 ? "+" : "") +
                        Math.round(snap.total_pnl).toLocaleString()}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>
    </>
  );
}