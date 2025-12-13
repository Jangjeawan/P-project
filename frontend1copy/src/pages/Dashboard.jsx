// src/pages/Dashboard.jsx
import { useEffect, useState } from "react";
import Chart from "react-apexcharts";
import { fetchChart, fetchIndicator } from "../api/analysisApi";

export default function Dashboard() {
  const [stockCode, setStockCode] = useState("005930");
  const [candles, setCandles] = useState([]);
  const [indicator, setIndicator] = useState(null);

  const STOCKS = [
    { code: "005930", name: "삼성전자" },
    { code: "035420", name: "네이버" },
    { code: "005380", name: "현대차" },
  ];

  const loadData = async () => {
    try {
      const [chartRes, indiRes] = await Promise.all([
        fetchChart(stockCode),
        fetchIndicator(stockCode),
      ]);

      setCandles(chartRes.candles || []);
      setIndicator(indiRes);
    } catch (e) {
      alert("차트/지표 로드 실패");
      console.error(e);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // ApexCharts series/options 준비
  const chartSeries = [
    {
      name: "Price",
      type: "candlestick",
      data: candles.map((c) => ({
        x: new Date(c.datetime),
        y: [c.open, c.high, c.low, c.close],
      })),
    },
    {
      name: "Close",
      type: "line",
      data: candles.map((c) => ({
        x: new Date(c.datetime),
        y: c.close,
      })),
    },
  ];

  const chartOptions = {
    chart: {
      type: "candlestick",
      height: 350,
      toolbar: { show: true, tools: { zoom: true, pan: true, reset: true } },
      zoom: { enabled: true },
      theme: "dark"
    },
    xaxis: { type: "datetime", theme: "dark" },
    yaxis: { tooltip: { enabled: true }, theme: "dark" },
    tooltip: { shared: true, enabled: true, theme: "dark" },
    stroke: { width: [1, 2] , theme: "dark"},
    grid: { borderColor: "#f1f1f1", theme: "dark" },
  };

  return (
    <div>
      <h2>📊 현재 차트 & 기술지표</h2>

      {/* 종목 선택 */}
      <div style={{ marginBottom: 12, display: "flex", gap: 8 }}>
        <select
          value={stockCode}
          onChange={(e) => setStockCode(e.target.value)}
          className="stock-select"
        >
          {STOCKS.map((s) => (
            <option key={s.code} value={s.code}>
              {s.name}
            </option>
          ))}
        </select>

        <button className="primary-btn" onClick={loadData}>
          조회
        </button>
      </div>

      {/* 차트 */}
      <div className="dash-card">
        <h3>가격 차트 (OHLC + Close)</h3>
        {candles.length ? (
          <Chart options={chartOptions} series={chartSeries} type="candlestick" height={350} />
        ) : (
          <p>차트 데이터 없음</p>
        )}
      </div>

      {/* 지표 */}
      <div className="dash-card">
        <h3>기술적 지표</h3>
        {indicator ? (
          <ul className="indicator-list">
            {Object.entries(indicator)
              .filter(([k]) => k !== "stock_code")
              .map(([k, v]) => (
                <li key={k}>
                  <strong>{k}</strong>: {v !== null ? v.toFixed(2) : "-"}
                </li>
              ))}
          </ul>
        ) : (
          <p>지표 없음</p>
        )}
      </div>
    </div>
  );
}
