import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { loginUser } from "../api/authApi";

export default function Login() {
  const navigate = useNavigate();

  const [form, setForm] = useState({ username: "", password: "" });
  const [status, setStatus] = useState("");
  const [userName, setUserName] = useState("");

  useEffect(() => {
    const saved = localStorage.getItem("stuckai_name") || "";
    setUserName(saved);
  }, []);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async () => {
    setStatus("");

    if (!form.username || !form.password) {
      setStatus("아이디와 비밀번호를 입력하세요.");
      return;
    }

    setStatus("로그인 중...");

    try {
      const data = await loginUser(form.username, form.password);

      setStatus("로그인 성공!");
      setTimeout(() => navigate("/"), 500);
    } catch (err) {
      const msg = err.response?.data?.detail || "알 수 없는 오류";
      setStatus("로그인 실패: " + msg);
    }
  };

  return (
    <div className="auth-page">
      <div className="wrap">
        <div className="auth-card" style={{ maxWidth: "480px" }}>
          <h2 style={{ marginBottom: "16px" }}>로그인</h2>

          <div className="section">
            <label>아이디</label>
            <input
              name="username"
              placeholder="아이디 입력"
              value={form.username}
              onChange={handleChange}
            />

            <label style={{ marginTop: "14px" }}>비밀번호</label>
            <input
              name="password"
              type="password"
              placeholder="비밀번호 입력"
              value={form.password}
              onChange={handleChange}
            />

            {status && (
              <div
                style={{
                  marginTop: "14px",
                  color: status.includes("성공") ? "#4ade80" : "#f87171",
                }}
              >
                {status}
              </div>
            )}

            <button
              className="btn-main"
              style={{ marginTop: "20px", width: "100%" }}
              onClick={handleSubmit}
            >
              로그인
            </button>

            <button
              className="btn-outline"
              style={{ marginTop: "12px", width: "100%" }}
              onClick={() => navigate("/signup")}
            >
              회원가입 페이지로 이동
            </button>

            {/* 🔥 홈으로 돌아가기 버튼 추가 */}
            <button
              className="btn-outline"
              style={{ marginTop: "12px", width: "100%" }}
              onClick={() => navigate("/")}
            >
              홈으로 돌아가기
            </button>

            <div style={{ marginTop: "14px", fontSize: "13px", color: "#9ca3af" }}>
              현재 로그인: {userName || "없음"}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}