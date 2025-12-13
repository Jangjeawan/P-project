// src/pages/Signup.jsx
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { registerUser } from "../api/authApi";

export default function Signup() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    username: "",
    password: "",
    confirm: "",
    name: "",
  });

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleChange = (e) => {
    setForm({
      ...form,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async () => {
    setError("");
    setSuccess("");

    if (!form.username || !form.password || !form.confirm || !form.name) {
      setError("모든 항목을 입력해주세요.");
      return;
    }

    if (form.password !== form.confirm) {
      setError("비밀번호가 일치하지 않습니다.");
      return;
    }

    try {
      await registerUser(form.username, form.password, form.name);

      setSuccess("회원가입이 완료되었습니다!");
      setTimeout(() => navigate("/login"), 800);
    } catch (err) {
      const msg = err.response?.data?.detail || "회원가입 실패";
      setError(msg);
    }
  };

  return (
    <div className="auth-page">
      <div className="wrap">
        <div className="auth-card" style={{ maxWidth: "480px" }}>
          <h2 style={{ marginBottom: "20px" }}>회원가입</h2>
           <label style={{ marginTop: "14px" }}>이름</label>
            <input
              name="name"
              placeholder="이름 입력"
              value={form.name}
              onChange={handleChange}
            />
          <div className="section">
            <label>ID</label>
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

            <label style={{ marginTop: "14px" }}>비밀번호 확인</label>
            <input
              name="confirm"
              type="password"
              placeholder="비밀번호 확인"
              value={form.confirm}
              onChange={handleChange}
            />

            {error && <div style={{ color: "#f87171", marginTop: "12px" }}>{error}</div>}
            {success && <div style={{ color: "#4ade80", marginTop: "12px" }}>{success}</div>}

            <button
              className="btn-main"
              style={{ marginTop: "20px", width: "100%" }}
              onClick={handleSubmit}
            >
              회원가입 하기
            </button>

            <button
              className="btn-outline"
              style={{ marginTop: "12px", width: "100%" }}
              onClick={() => navigate("/login")}
            >
              로그인 페이지로 이동
            </button>

            {/* 🔥 홈으로 이동 버튼 추가 */}
            <button
              className="btn-outline"
              style={{ marginTop: "12px", width: "100%" }}
              onClick={() => navigate("/")}
            >
              홈으로 돌아가기
            </button>

          </div>
        </div>
      </div>
    </div>
  );
}