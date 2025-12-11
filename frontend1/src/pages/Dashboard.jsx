import { useState, useEffect } from "react";
import api from "../api/axiosInstance";
import "../index.css";

export default function Dashboard() {
  const [balance, setBalance] = useState(null);
  const [balanceParsed, setBalanceParsed] = useState(null);

  const [accountNo, setAccountNo] = useState("");
  const [productCode, setProductCode] = useState("");
  const [savedAccount, setSavedAccount] = useState(null);

  const [orderStock, setOrderStock] = useState("");
  const [orderQty, setOrderQty] = useState(1);
  const [orderSide, setOrderSide] = useState("BUY");
  const [orderResult, setOrderResult] = useState(null);

  const [history, setHistory] = useState([]);
  const [historyFilter, setHistoryFilter] = useState("");

  // 리스크 설정 상태값
  const [riskStock, setRiskStock] = useState("ALL");
  const [riskMaxQty, setRiskMaxQty] = useState("");
  const [riskMaxPct, setRiskMaxPct] = useState("");
  const [riskMaxDailyBuy, setRiskMaxDailyBuy] = useState(""); // ⬅️ 추가됨
  const [riskActive, setRiskActive] = useState("on");
  const [riskKey, setRiskKey] = useState("");
  const [riskList, setRiskList] = useState([]);

  const [autoTradeEnabled, setAutoTradeEnabled] = useState(false);
  const [autoTradeResult, setAutoTradeResult] = useState(null);

  // --------------------------
  // 1) 계좌 잔고 조회
  // --------------------------
  const fetchBalance = async () => {
    try {
      const res = await api.get("/accounts/balance");
      setBalance(res.data);

      const holdings = Array.isArray(res.data.output1) ? res.data.output1 : [];
      const summary = Array.isArray(res.data.output2) ? res.data.output2[0] : {};

      setBalanceParsed({ holdings, summary });
    } catch (err) {
      alert("잔고 조회 실패");
    }
  };

  // --------------------------
  // 2) 계좌 설정 로드
  // --------------------------
  const loadAccount = async () => {
    try {
      const token = localStorage.getItem("stuckai_token");
      const res = await api.get(`/me/account?token=${token}`);
      if (res.data?.has_config) setSavedAccount(res.data);
    } catch (_) {}
  };

  useEffect(() => {
    loadAccount();
  }, []);

  // --------------------------
  // 3) 계좌 저장
  // --------------------------
  const saveAccount = async () => {
    try {
      const token = localStorage.getItem("stuckai_token");
      const res = await api.put(`/me/account?token=${token}`, {
        account_no: accountNo,
        account_code: productCode,
      });
      setSavedAccount(res.data);
      alert("계좌 설정 저장됨");
    } catch (err) {
      alert("계좌 저장 실패");
    }
  };

  // --------------------------
  // 4) 시장가 주문
  // --------------------------
  const sendOrder = async () => {
    try {
      const res = await api.post("/orders/market", {
        stock_code: orderStock,
        quantity: Number(orderQty),
        side: orderSide,
      });
      setOrderResult(res.data);
      alert("주문 성공");
    } catch (err) {
      alert("주문 실패");
      setOrderResult(err.response?.data || {});
    }
  };

  // --------------------------
  // 5) 거래 내역
  // --------------------------
  const fetchHistory = async () => {
    try {
      const res = await api.get("/orders/history", {
        params: { stock_code: historyFilter || undefined },
      });
      setHistory(res.data);
    } catch (err) {
      alert("내역 조회 실패");
    }
  };

  // --------------------------
  // 6) 리스크 설정 저장
  // --------------------------
  const saveRisk = async () => {
  try {
    const stock = riskStock || "ALL"; // 종목코드 없으면 ALL
    
    const payload = {
      max_position_shares: riskMaxQty ? Number(riskMaxQty) : null,
      max_weight_pct: riskMaxPct ? Number(riskMaxPct) : null,
      max_daily_buy_amount: riskMaxDailyBuy ? Number(riskMaxDailyBuy) : null,
      active: riskActive === "on",
    };

    const headers = {};
    if (riskKey) headers["X-API-Key"] = riskKey;

    await api.put(`/settings/risk/${stock}`, payload, { headers });

    alert("리스크 규칙 저장됨");
  } catch (err) {
    console.error(err);
    alert("리스크 저장 실패");
  }
};

  // --------------------------
  // 6-2) 리스크 조회
  // --------------------------
  const loadRisk = async () => {
    try {
      const res = await api.get("/settings/risk");
      setRiskList(res.data);
    } catch (_) {}
  };

  // --------------------------
  // 7) 자동매매 실행
  // --------------------------
  const runAutoTrade = async () => {
    if (!autoTradeEnabled) return alert("자동매매 OFF입니다.");

    try {
      const API_KEY = import.meta.env.VITE_API_KEY;
      const res = await api.post(
        "/trade/auto",
        {},
        { headers: { "X-API-Key": API_KEY } }
      );
      setAutoTradeResult(res.data);
    } catch (err) {
      alert("자동매매 실패");
    }
  };

  // --------------------------
  // 8) 성과 요약
  // --------------------------
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

  const formatAutoTradeResult = (data) => {
    if (!data) return "";
    let text = "🟦 자동매매 결과 요약\n";

    if (data.stdout) {
      text += "\n📄 실행 로그:\n";
      text += data.stdout.trim();
    } else {
      text += "\n • 실행 로그 없음";
    }

    text += `\n\n✔ 실행 코드: ${data.returncode}`;
    return text;
  };

  // ===================================================
  // 렌더링
  // ===================================================
  return (
    <div className="dash-wrap">
      <header className="dash-header">
        <div className="dash-title">StuckAI Trading Dashboard</div>
        <div className="dash-sub">SAC + KIS Demo</div>
      </header>

      <div className="dash-nav">
        <button onClick={() => (window.location.href = "/")}>홈</button>
        <button onClick={() => (window.location.href = "/dashboard")}>
          마이페이지
        </button>
        <button
          onClick={() => {
            localStorage.removeItem("stuckai_token");
            localStorage.removeItem("stuckai_name");
            window.location.href = "/login-page";
          }}
        >
          로그아웃
        </button>
      </div>

      <main className="dash-main">
        {/* ----------------------------- */}
        {/* 1) 잔고 */}
        {/* ----------------------------- */}
        <section className="dash-card">
          <div className="dash-card-header">
            <h2>계좌 잔고 / 포지션</h2>
            <button onClick={fetchBalance}>잔고 조회</button>
          </div>

          {balanceParsed && (
            <>
              <div className="dash-summary">
                예수금:{" "}
                {balanceParsed.summary?.dnca_tot_amt?.toLocaleString() || "-"}
                원
              </div>

              <table className="dash-table">
                <thead>
                  <tr>
                    <th>종목코드</th>
                    <th>종목명</th>
                    <th>보유수량</th>
                    <th>평균매입가</th>
                    <th>평가손익</th>
                  </tr>
                </thead>
                <tbody>
                  {balanceParsed.holdings.map((x) => (
                    <tr key={x.pdno}>
                      <td>{x.pdno}</td>
                      <td>{x.prdt_name}</td>
                      <td>{x.hldg_qty}</td>
                      <td>{x.pchs_avg_pric}</td>
                      <td>{x.evlu_pfls_amt}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </section>

        {/* ----------------------------- */}
        {/* 2) 계좌 설정 */}
        {/* ----------------------------- */}
        <section className="dash-card">
          <h2>내 KIS 계좌 설정</h2>

          <div className="dash-grid2">
            <input
              placeholder="계좌번호"
              value={accountNo}
              onChange={(e) => setAccountNo(e.target.value)}
            />

            <input
              placeholder="상품코드"
              value={productCode}
              onChange={(e) => setProductCode(e.target.value)}
            />

            <button onClick={saveAccount}>저장</button>
          </div>

          {savedAccount && (
  <p className="dash-small">
    저장된 계좌: {savedAccount.account_no_masked} / {savedAccount.account_code}
  </p>
)}
        </section>

        {/* ----------------------------- */}
        {/* 3) 자동매매 */}
        {/* ----------------------------- */}
        <section className="dash-card">
          <h2 className="dash-flex-between">
            자동매매 실행
            <label className="dash-switch">
              <input
                type="checkbox"
                checked={autoTradeEnabled}
                onChange={() => setAutoTradeEnabled(!autoTradeEnabled)}
              />
              <span></span>
            </label>
          </h2>

          <button
            disabled={!autoTradeEnabled}
            onClick={runAutoTrade}
            className="dash-btn"
          >
            자동매매 실행
          </button>

          {autoTradeResult && (
            <div className="dash-auto-summary">
              {formatAutoTradeResult(autoTradeResult)
                .split("\n")
                .map((line, idx) => (
                  <div key={idx}>{line}</div>
                ))}
            </div>
          )}
        </section>

        {/* ----------------------------- */}
        {/* 4) 시장가 주문 */}
        {/* ----------------------------- */}
        <section className="dash-card">
          <h2>시장가 주문 테스트</h2>

          <div className="dash-grid3">
            <input
              placeholder="종목코드"
              value={orderStock}
              onChange={(e) => setOrderStock(e.target.value)}
            />

            <input
              type="number"
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

          <button onClick={sendOrder} className="dash-btn">
            시장가 주문 전송
          </button>

          {orderResult && (
            <pre className="dash-pre">
              {JSON.stringify(orderResult, null, 2)}
            </pre>
          )}
        </section>

        {/* ----------------------------- */}
        {/* 5) 거래 내역 */}
        {/* ----------------------------- */}
        <section className="dash-card">
          <div className="dash-card-header">
            <h2>거래 내역</h2>
            <button onClick={fetchHistory}>새로고침</button>
          </div>

          <input
            className="dash-input"
            placeholder="종목코드 필터"
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
              {history.map((x) => (
                <tr key={x.id}>
                  <td>{new Date(x.created_at).toLocaleString()}</td>
                  <td>{x.stock_code}</td>
                  <td>{x.quantity}</td>
                  <td>{x.side}</td>
                  <td>{x.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        {/* ----------------------------- */}
        {/* 성과 요약 */}
        {/* ----------------------------- */}
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
                      <td>
                        {Math.round(snap.total_value || 0).toLocaleString()}
                      </td>
                      <td>{Math.round(snap.cash || 0).toLocaleString()}</td>
                      <td>
                        {Math.round(snap.total_buy_amount || 0).toLocaleString()}
                      </td>
                      <td>
                        {Math.round(snap.total_eval_amount || 0).toLocaleString()}
                      </td>
                      <td>
                        {(Math.round(snap.total_pnl) >= 0 ? "+" : "") +
                          Math.round(snap.total_pnl || 0).toLocaleString()}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </section>

        {/* ----------------------------- */}
        {/* 리스크 설정 */}
        {/* ----------------------------- */}
        <section className="dash-card">
          <div className="dash-card-header">
            <h2>리스크 설정</h2>
            <button onClick={loadRisk}>새로고침</button>
          </div>

          <div className="dash-grid2">
            <input
              placeholder="종목코드 또는 ALL"
              value={riskStock}
              onChange={(e) => setRiskStock(e.target.value)}
            />

            <input
              placeholder="최대 수량"
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
              placeholder="API Key"
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
      </main>
    </div>
  );
}