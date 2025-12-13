// src/layout/MainLayout.jsx
import React, { useEffect, useState } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import api from "../api/axiosInstance";

export default function MainLayout() {
  const navigate = useNavigate();

  /* ===============================
     로그인 / 계좌 상태
  =============================== */
  const isLoggedIn = !!localStorage.getItem("stuckai_token");
  const userName = localStorage.getItem("stuckai_name");
  const [hasAccount, setHasAccount] = useState(false);

  /* ===============================
     🔥 계좌 상태 동기화 (핵심)
  =============================== */
  useEffect(() => {
    const syncAccountState = async () => {
      if (!isLoggedIn) {
        setHasAccount(false);
        localStorage.removeItem("stuckai_account");
        return;
      }

      try {
        const token = localStorage.getItem("stuckai_token");
        const res = await api.get(`/me/account?token=${token}`);

        if (res.data?.has_config) {
          setHasAccount(true);
          localStorage.setItem("stuckai_account", "true"); // 가드용 동기화
        } else {
          setHasAccount(false);
          localStorage.removeItem("stuckai_account");
        }
      } catch (err) {
        console.error("계좌 상태 확인 실패", err);
        setHasAccount(false);
        localStorage.removeItem("stuckai_account");
      }
    };

    syncAccountState();
  }, [isLoggedIn]);

  /* ===============================
     🔒 접근 가드
  =============================== */
  const guardedNavigate = (path, options = {}) => {
    const { requireLogin = false, requireAccount = false } = options;

    if (requireLogin && !isLoggedIn) {
      alert("로그인 후 이용할 수 있습니다.");
      navigate("/login");
      return;
    }

    if (requireAccount && !hasAccount) {
      alert("계좌 설정 후 이용할 수 있습니다.");
      navigate("/account");
      return;
    }

    navigate(path);
  };

  return (
    <div className="home-root">
      {/* ===============================
          SIDEBAR
      =============================== */}
      <aside className="sidebar">
        <div className="sidebar-title">stuckAI</div>

        {/* 누구나 */}
        <button
  className={`sidebar-btn ${location.pathname === "/" ? "active" : ""}`} onClick={() => guardedNavigate("/")}>
          <span className="icon">🏠</span>
          <span className="label">홈</span>
        </button>

        <button
  className={`sidebar-btn ${location.pathname === "/dashboard" ? "active" : ""}`} onClick={() => guardedNavigate("/dashboard")}>
          <span className="icon">📊</span>
          <span className="label">차트</span>
        </button>

        {/* 로그인 필요 */}
        <button
  className={`sidebar-btn ${location.pathname === "/account" ? "active" : ""}`}
          onClick={() =>
            guardedNavigate("/account", { requireLogin: true })
          }
        >
          <span className="icon">💳</span>
          <span className="label">계좌</span>
        </button>

        {/* 로그인 + 계좌 필요 */}
        <button
  className={`sidebar-btn ${location.pathname === "/manual-trade" ? "active" : ""}`}
          onClick={() =>
            guardedNavigate("/manual-trade", {
              requireLogin: true,
              requireAccount: true,
            })
          }
        >
          <span className="icon">💱</span>
          <span className="label">수동 매매</span>
        </button>

        <button
  className={`sidebar-btn ${location.pathname === "/trade" ? "active" : ""}`}
          onClick={() =>
            guardedNavigate("/trade", {
              requireLogin: true,
              requireAccount: true,
            })
          }
        >
          <span className="icon">🤖</span>
          <span className="label">자동 매매</span>
        </button>

        <button
  className={`sidebar-btn ${location.pathname === "/risk" ? "active" : ""}`}
          onClick={() =>
            guardedNavigate("/risk", {
              requireLogin: true,
              requireAccount: true,
            })
          }
        >
          <span className="icon">🛡</span>
          <span className="label">리스크 설정</span>
        </button>

       <div className="sidebar-auth">
  {isLoggedIn ? (
    <>
      {/* ✅ 환영 문구 */}
     {userName && (
  
    <div className="welcome-text">
      <strong>{userName}</strong>님 환영합니다 👋
    </div>
      )}

      <button
        className="danger"
        onClick={() => {
          localStorage.removeItem("stuckai_token");
          localStorage.removeItem("stuckai_name");
          localStorage.removeItem("stuckai_account");
          navigate("/login");
        }}
      >
        로그아웃
      </button>
    </>
          ) : (
            <>
              <button onClick={() => navigate("/login")}>
                🔐 로그인
              </button>
              <button onClick={() => navigate("/signup")}>
                ✨ 회원가입
              </button>
            </>
          )}
        </div>
      </aside>

      {/* ===============================
          MAIN CONTENT
      =============================== */}
      <div className="wrap">
        <div className="card">
          <Outlet />
        </div>
      </div>
    </div>
  );
}

