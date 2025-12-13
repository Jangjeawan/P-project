import { BrowserRouter, Routes, Route } from "react-router-dom";

import MainLayout from "./Layout/Main_Layout";

import Home from "./pages/Home";
import Dashboard from "./pages/Dashboard";
import Account from "./pages/Account";
import Trade from "./pages/Trade";
import Risk from "./pages/Risk";
import ManualTrade from "./pages/ManualTrade";

import Login from "./pages/Login";
import Signup from "./pages/Signup";

function App() {
  return (
    <BrowserRouter>
      <Routes>

        {/* 🔓 로그인 / 회원가입 (레이아웃 없음) */}
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />

        {/* 🔐 서비스 영역 (사이드바 + 카드 유지) */}
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Home />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="account" element={<Account />} />
          <Route path="trade" element={<Trade />} />
          <Route path="risk" element={<Risk />} />
          <Route path="manual-trade" element={<ManualTrade />} />
        </Route>

      </Routes>
    </BrowserRouter>
  );
}

export default App;