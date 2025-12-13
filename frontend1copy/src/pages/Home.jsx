// src/pages/Home.jsx
import React, { useEffect, useRef } from "react";

export default function Home() {
  const canvasRef = useRef(null);

  /* ===============================
     샘플 차트 (기존 그대로)
  =============================== */
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !canvas.getContext) return;

    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;

    // 배경
    ctx.fillStyle = "#020617";
    ctx.fillRect(0, 0, w, h);

    // 축
    ctx.strokeStyle = "#1f2937";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(32, 12);
    ctx.lineTo(32, h - 18);
    ctx.lineTo(w - 8, h - 18);
    ctx.stroke();

    // 데이터
    const points = [
      0.12, 0.18, 0.15, 0.23, 0.28, 0.32,
      0.29, 0.37, 0.41, 0.38, 0.44, 0.48
    ];
    const n = points.length;

    // 라인 그라데이션
    const lineGrad = ctx.createLinearGradient(0, 0, w, 0);
    lineGrad.addColorStop(0, "#3b82f6");
    lineGrad.addColorStop(1, "#06b6d4");

    ctx.strokeStyle = lineGrad;
    ctx.lineWidth = 2;
    ctx.beginPath();

    for (let i = 0; i < n; i++) {
      const x = 32 + (w - 48) * (i / (n - 1));
      const y = (h - 26) - (h - 40) * points[i];
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.stroke();

    // 영역 채우기
    const gradient = ctx.createLinearGradient(0, 20, 0, h - 18);
    gradient.addColorStop(0, "rgba(59,130,246,0.22)");
    gradient.addColorStop(1, "rgba(15,23,42,0)");

    ctx.fillStyle = gradient;
    ctx.lineTo(32 + (w - 48), h - 18);
    ctx.lineTo(32, h - 18);
    ctx.closePath();
    ctx.fill();
  }, []);

  return (
    <>
      {/* ===============================
          HERO
      =============================== */}
      <section className="hero">
        <div>
          <div className="hero-title">
            강화학습이 스스로 학습한 주식 자동매매 엔진
          </div>

          <div className="hero-sub">
            삼성전자 · 네이버 · 현대차 3종목에 대해  
            Soft Actor-Critic 기반으로 학습된 RL 에이전트가  
            매일 포지션을 결정하고 KIS OpenAPI를 통해 주문을 집행합니다.
          </div>

          <div className="hero-tags">
            <span className="pill">Reinforcement Learning · SAC</span>
            <span className="pill">KIS OpenAPI 연동</span>
            <span className="pill">자동 리밸런싱</span>
            <span className="pill">리스크 한도 관리</span>
          </div>
        </div>

        <div className="hero-chart-wrap">
          <div className="hero-chart-title">
            <span>샘플 운용 곡선 (시뮬레이션)</span>
            <div className="dot-wrap">
              <span className="dot" />
              <span>전략 순자산</span>
            </div>
          </div>
          <canvas ref={canvasRef} width={360} height={180} />
        </div>
      </section>

      {/* ===============================
          성과 요약
      =============================== */}
      <section className="hero-metrics">
        <div>
          <div className="metric-label">Backtest 누적 수익률 (예시)</div>
          <div className="metric-value">+38.4%</div>
        </div>

        <div>
          <div className="metric-label">최대 낙폭 관리</div>
          <div className="metric-value">-12.7%</div>
        </div>

        <div>
          <div className="metric-label">운영 종목 수</div>
          <div className="metric-value">3개</div>
        </div>
      </section>
      {/* ===============================
    사용 방법 안내
=============================== */}
<section className="hero-metrics" style={{ marginTop: "48px" }}>
  <div>
    <div className="metric-label">1. 로그인 및 계좌 등록</div>
    <div className="metric-value" style={{ fontSize: "1rem", fontWeight: 500 }}>
      계좌 및 매매 관련 기능은 로그인 후 이용할 수 있으며,<br />
      KIS OpenAPI 모의투자or실계좌를 등록해야 매매 기능이 활성화됩니다.
    </div>
  </div>

  <div>
    <div className="metric-label">2. 자동매매 ON / OFF</div>
    <div className="metric-value" style={{ fontSize: "1rem", fontWeight: 500 }}>
      계좌 등록 이후 SAC 모델이<br />
      하루 단위로 매수·매도 여부를 판단하여 자동으로 주문합니다.<br />
      자동매매는 언제든지 ON / OFF로 제어할 수 있습니다.
    </div>
  </div>

  <div>
    <div className="metric-label">3. 수동 매매 지원</div>
    <div className="metric-value" style={{ fontSize: "1rem", fontWeight: 500 }}>
      자동매매와 별도로 사용자가 직접<br />
      시장가 주문을 통해 수동 매수·매도도 가능합니다.<br />
      (계좌 미등록 시 매매 기능은 비활성화됩니다.)
    </div>
  </div>
</section>
    </>
  );
}
