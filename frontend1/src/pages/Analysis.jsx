import { useState, useEffect } from "react";
import {
  fetchChart,
  fetchIndicator,
  fetchPredictHistory,
} from "../api/analysisApi";

export default function Analysis() {
  const [stockCode, setStockCode] = useState("005930");
  const [chart, setChart] = useState([]);
  const [indicator, setIndicator] = useState(null);
  const [history, setHistory] = useState([]);

  const loadAll = async () => {
    try {
      const [chartData, indicatorData, historyData] = await Promise.all([
        fetchChart(stockCode),
        fetchIndicator(stockCode),
        fetchPredictHistory(),
      ]);

      setChart(chartData.candles);
      setIndicator(indicatorData);
      setHistory(historyData);
    } catch (err) {
      alert("데이터 불러오기 실패");
      console.error(err);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  return (
    <div className="analysis-wrap">
      <h1>📊 종합 분석 페이지</h1>

      {/* 종목 선택 */}
      <div className="analysis-input">
        <input
          value={stockCode}
          onChange={(e) => setStockCode(e.target.value)}
          placeholder="종목코드 입력"
        />
        <button onClick={loadAll}>불러오기</button>
      </div>

      {/* 차트 */}
      <section className="dash-card">
        <h2>캔들 차트 (최근 데이터)</h2>
        <pre className="dash-pre">
          {chart.length > 0
            ? JSON.stringify(chart.slice(-5), null, 2)
            : "차트 데이터 없음"}
        </pre>
      </section>

      {/* 기술적 지표 */}
      <section className="dash-card">
        <h2>기술적 지표</h2>
        {indicator ? (
          <ul className="indicator-list">
            {Object.entries(indicator).map(([k, v]) => (
              <li key={k}>
                <strong>{k}</strong>: {v}
              </li>
            ))}
          </ul>
        ) : (
          <p>지표 없음</p>
        )}
      </section>

      {/* 예측 / 거래 히스토리 */}
      <section className="dash-card">
        <h2>예측 / 거래 히스토리</h2>
        <table className="dash-table">
          <thead>
            <tr>
              <th>시간</th>
              <th>종목</th>
              <th>수량</th>
              <th>방향</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            {history.map((x) => (
              <tr key={x.created_at}>
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
    </div>
  );
}