// src/pages/Home.jsx
import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

export default function Home() {
  const [userName, setUserName] = useState("");
  const canvasRef = useRef(null);
  const navigate = useNavigate();

  // 로그인 여부 체크
  const isLoggedIn = !!localStorage.getItem("stuckai_token");

  // localStorage에서 유저 이름 로드
  useEffect(() => {
    try {
      const name = localStorage.getItem("stuckai_name") || "";
      setUserName(name);
    } catch (e) {
      console.warn(e);
    }
  }, []);

  // 캔버스 샘플 차트
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !canvas.getContext) return;

    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;

    ctx.fillStyle = "#020617";
    ctx.fillRect(0, 0, w, h);

    ctx.strokeStyle = "#1f2937";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(32, 12);
    ctx.lineTo(32, h - 18);
    ctx.lineTo(w - 8, h - 18);
    ctx.stroke();

    const points = [0.12, 0.18, 0.15, 0.23, 0.28, 0.32, 0.29, 0.37, 0.41, 0.38, 0.44, 0.48];
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
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // 영역 그라데이션
    const gradient = ctx.createLinearGradient(0, 20, 0, h - 18);
    gradient.addColorStop(0, "rgba(59,130,246,0.22)");
    gradient.addColorStop(1, "rgba(15,23,42,0)");

    ctx.fillStyle = gradient;

    ctx.beginPath();
    for (let i = 0; i < n; i++) {
      const x = 32 + (w - 48) * (i / (n - 1));
      const y = (h - 26) - (h - 40) * points[i];
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.lineTo(32 + (w - 48), h - 18);
    ctx.lineTo(32, h - 18);
    ctx.closePath();
    ctx.fill();
  }, []);

  return (
    <div className="home-root">
      <div className="wrap">
        <div className="card">

          {/* HEADER */}
          <div className="header">
            <div>
              <div className="title">stuckAI</div>
              <div className="subtitle">
                SAC 강화학습 + KIS OpenAPI 기반 자동 매매 데모 서비스입니다.
              </div>
            </div>

            {/* 오른쪽 버튼 영역 */}
            <div
              style={{
                textAlign: "right",
                display: "flex",
                flexDirection: "column",
                alignItems: "flex-end",
                gap: "6px",
              }}
            >
              {/* 🔵 로그인된 경우 → 홈 / 마이페이지 / 로그아웃 */}
              {isLoggedIn && (
                <div style={{ display: "flex", gap: "8px", marginBottom: "2px" }}>
                  <button className="btn-outline" onClick={() => navigate("/")}>
                    홈
                  </button>
                  <button className="btn-outline" onClick={() => navigate("/dashboard")}>
                    마이페이지
                  </button>
                  <button
                    className="btn-outline"
                    onClick={() => {
                      localStorage.removeItem("stuckai_token");
                      localStorage.removeItem("stuckai_name");
                      setUserName("");
                      navigate("/login", { replace: true });
                    }}
                  >
                    로그아웃
                  </button>
                </div>
              )}

              {/* 개발용 표시 */}
              <div className="chip">로컬 개발용</div>

              {/* 🟥 비로그인 상태 → 로그인 / 회원가입 버튼만 */}
              {!isLoggedIn && (
                <div style={{ display: "flex", gap: "8px", marginTop: "4px" }}>
                  <button className="btn-outline" onClick={() => navigate("/login")}>
                    로그인
                  </button>
                  <button className="btn-main" onClick={() => navigate("/signup")}>
                    회원가입
                  </button>
                </div>
              )}

              {/* 현재 로그인 사용자 */}
              <div className="user" style={{ marginTop: 4 }}>
                현재 로그인: {isLoggedIn ? userName : "없음"}
              </div>
            </div>
          </div>

          {/* HERO */}
          <div className="hero">
            <div>
              <div className="hero-title">강화학습이 스스로 학습한 주식 자동매매 엔진</div>
              <div className="hero-sub">
                삼성전자 · 네이버 · 현대차 3종목에 대해 Soft Actor-Critic 기반으로 학습한
                RL 에이전트가 매일 포지션을 결정하고, KIS OpenAPI를 통해 모의계좌에
                주문을 집행합니다.
              </div>

              <div className="hero-tags">
                <span className="pill">Reinforcement Learning · SAC</span>
                <span className="pill">KIS OpenAPI 연동</span>
                <span className="pill">자동 일별 리밸런싱</span>
                <span className="pill">리스크 한도 관리</span>
              </div>

              <div className="hero-metrics">
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
              </div>
            </div>

            {/* 오른쪽 미니 차트 */}
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
          </div>

        {/* PANEL 3개 */}
<div className="grid">

  {/* 01. 회원가입 */}
  <section className="panel">
    <h3>01. 회원가입</h3>
    <p>계정을 만들어야 대시보드에 접근할 수 있습니다.</p>
    <button
      className="btn-main"
      onClick={() => {
        if (isLoggedIn) {
          alert("이미 로그인된 상태입니다.");
          return;
        }
        navigate("/signup");
      }}
    >
      회원가입 페이지로 이동
    </button>
  </section>

  {/* 02. 로그인 */}
  <section className="panel">
    <h3>02. 로그인</h3>
    <p>로그인하면 이름이 상단에 표시됩니다.</p>
    <button
      className="btn-main"
      onClick={() => {
        if (isLoggedIn) {
          alert("이미 로그인된 상태입니다.");
          return;
        }
        navigate("/login");
      }}
    >
      로그인 페이지로 이동
    </button>
  </section>

  {/* 03. 트레이딩 대시보드 */}
  <section className="panel">
    <h3>03. 트레이딩 대시보드</h3>
    <p>잔고, 주문, 보유 종목을 확인할 수 있습니다.</p>
    <button
      className="btn-main"
      onClick={() => {
        if (!isLoggedIn) {
          alert("로그인 후 이용할 수 있습니다.");
          navigate("/login");
          return;
        }
        navigate("/dashboard");
      }}
    >
      대시보드 열기
    </button>
  </section>


</div>

        </div>
      </div>
    </div>
  );
}