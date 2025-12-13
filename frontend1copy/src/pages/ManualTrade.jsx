// src/pages/ManualTrade.jsx
import { useState } from "react";
import api from "../api/axiosInstance";
import "../index.css";

export default function ManualTrade() {
  /* ===============================
     주문 상태
  =============================== */
  const [orderStock, setOrderStock] = useState("");
  const [orderQty, setOrderQty] = useState(1);
  const [orderSide, setOrderSide] = useState("BUY");
  const [orderResult, setOrderResult] = useState(null);
  const [sending, setSending] = useState(false);

  /* ===============================
     거래 내역 상태
  =============================== */
  const [history, setHistory] = useState([]);
  const [historyFilter, setHistoryFilter] = useState("");
  const [loadingHistory, setLoadingHistory] = useState(false);

  /* ===============================
     시장가 주문
  =============================== */
  const sendOrder = async () => {
    if (!orderStock) return alert("종목코드를 입력하세요.");

    try {
      setSending(true);

      const res = await api.post("/orders/market", {
        stock_code: orderStock,
        quantity: Number(orderQty),
        side: orderSide,
      });

      setOrderResult(res.data);
      alert("주문 성공");

      // 주문 후 거래내역 자동 갱신
      fetchHistory();
    } catch (err) {
      alert("주문 실패");
      setOrderResult(err.response?.data || {});
    } finally {
      setSending(false);
    }
  };

  /* ===============================
     거래 내역 조회
  =============================== */
  const fetchHistory = async () => {
    try {
      setLoadingHistory(true);

      const res = await api.get("/orders/history", {
        params: {
          stock_code: historyFilter || undefined,
        },
      });

      setHistory(res.data || []);
    } catch (err) {
      alert("거래 내역 조회 실패");
    } finally {
      setLoadingHistory(false);
    }
  };

  /* ===================================================
     렌더링
  =================================================== */
  return (
    <div className="dash-wrap">
      <header className="dash-header">
        <div className="dash-title">수동 매매 (시장가 주문)</div>
        <div className="dash-sub">
          직접 시장가 주문을 실행하고 거래 내역을 확인합니다.
        </div>
      </header>

      <main className="dash-main">
        {/* ===============================
            1️⃣ 시장가 주문
        =============================== */}
        <section className="dash-card">
          <h2>시장가 주문</h2>

          <div className="dash-grid3">
            <input
              placeholder="종목코드 (예: 005930)"
              value={orderStock}
              onChange={(e) => setOrderStock(e.target.value)}
            />

            <input
              type="number"
              min={1}
              value={orderQty}
              onChange={(e) => setOrderQty(e.target.value)}
            />

            <select
              value={orderSide}
              onChange={(e) => setOrderSide(e.target.value)}
            >
              <option value="BUY">BUY</option>
              <option value="SELL">SELL</option>
            </select>
          </div>

          <button
            className="dash-btn"
            onClick={sendOrder}
            disabled={sending}
          >
            {sending ? "주문 중..." : "시장가 주문 실행"}
          </button>

          {orderResult && (
            <pre className="dash-pre">
              {JSON.stringify(orderResult, null, 2)}
            </pre>
          )}
        </section>

        {/* ===============================
            2️⃣ 거래 내역
        =============================== */}
        <section className="dash-card">
          <div className="dash-card-header">
            <h2>거래 내역</h2>
            <button onClick={fetchHistory} disabled={loadingHistory}>
              {loadingHistory ? "로딩 중..." : "새로고침"}
            </button>
          </div>

          <input
            className="dash-input"
            placeholder="종목코드 필터 (선택)"
            value={historyFilter}
            onChange={(e) => setHistoryFilter(e.target.value)}
          />

          <table className="dash-table">
            <thead>
              <tr>
                <th>시간</th>
                <th>종목코드</th>
                <th>수량</th>
                <th>방향</th>
                <th>상태</th>
              </tr>
            </thead>

            <tbody>
              {history.length === 0 ? (
                <tr>
                  <td colSpan="5" style={{ textAlign: "center" }}>
                    거래 내역이 없습니다.
                  </td>
                </tr>
              ) : (
                history.map((x) => (
                  <tr key={x.id}>
                    <td>{new Date(x.created_at).toLocaleString()}</td>
                    <td>{x.stock_code}</td>
                    <td>{x.quantity}</td>
                    <td>{x.side}</td>
                    <td>{x.status}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </section>
      </main>
    </div>
  );
}