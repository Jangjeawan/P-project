// src/pages/Account.jsx
import { useState, useEffect } from "react";
import api from "../api/axiosInstance";
import "../index.css";

export default function Account() {
  /* ===============================
     상태
  =============================== */
  const [savedAccount, setSavedAccount] = useState(null);

  // 계좌 설정 입력값
  const [accountNo, setAccountNo] = useState("");
  const [productCode, setProductCode] = useState("");
  const [kisAppKey, setKisAppKey] = useState("");
  const [kisAppSecret, setKisAppSecret] = useState("");
  const [realMode, setRealMode] = useState(false);

  // 잔고 조회
  const [balanceParsed, setBalanceParsed] = useState(null);

  /* ===============================
     1) 계좌 설정 로드
  =============================== */
  const loadAccount = async () => {
  try {
    const token = localStorage.getItem("stuckai_token");
    const res = await api.get(`/me/account?token=${token}`);

    if (res.data?.has_config) {
      setSavedAccount(res.data);
      setRealMode(Boolean(res.data.real_mode));

      // 🔥 이 줄이 빠져 있었음
      localStorage.setItem("stuckai_account", "true");
    } else {
      // 혹시라도 계좌 없으면 제거
      localStorage.removeItem("stuckai_account");
    }
  } catch (_) {
    localStorage.removeItem("stuckai_account");
  }
};
  useEffect(() => {
    loadAccount();
  }, []);

  /* ===============================
     2) 계좌 설정 저장
  =============================== */
  const saveAccount = async () => {
    try {
      const token = localStorage.getItem("stuckai_token");
      const res = await api.put(`/me/account?token=${token}`, {
        account_no: accountNo,
        account_code: productCode,
        kis_app_key: kisAppKey,
        kis_app_secret: kisAppSecret,
        real_mode: realMode,
      });

      setSavedAccount(res.data);
      localStorage.setItem("stuckai_account", "true"); // 🔥 가드용
      alert("계좌 설정 저장 완료");
    } catch (err) {
      alert("계좌 설정 저장 실패");
    }
  };

  /* ===============================
     3) 잔고 조회
  =============================== */
  const fetchBalance = async () => {
    try {
      const res = await api.get("/accounts/balance");
      const raw = res.data.raw || {};

      const holdings = Array.isArray(raw.output1) ? raw.output1 : [];
      const summary = Array.isArray(raw.output2) ? raw.output2[0] : {};

      setBalanceParsed({ holdings, summary });
    } catch (err) {
      alert("잔고 조회 실패");
    }
  };

  /* ===================================================
     렌더링
  =================================================== */
  return (
    <div className="dash-wrap">
      <header className="dash-header">
        <div className="dash-title">계좌 관리</div>
        <div className="dash-sub">KIS 계좌 설정 및 잔고 조회</div>
      </header>

      <main className="dash-main">

        {/* ===============================
            계좌 미설정 → 등록 화면
        =============================== */}
        {!savedAccount && (
          <section className="dash-card">
            <h2>내 KIS 계좌 등록</h2>

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

              <input
                placeholder="KIS App Key"
                value={kisAppKey}
                onChange={(e) => setKisAppKey(e.target.value)}
              />

              <input
                placeholder="KIS App Secret"
                type="password"
                value={kisAppSecret}
                onChange={(e) => setKisAppSecret(e.target.value)}
              />

              <label className="dash-small">
                <input
                  type="checkbox"
                  checked={realMode}
                  onChange={(e) => setRealMode(e.target.checked)}
                />
                &nbsp;실거래 모드 (체크 시 실계좌)
              </label>

              <button onClick={saveAccount}>계좌 등록</button>
            </div>
          </section>
        )}

        {/* ===============================
            계좌 설정 완료 → 조회 화면
        =============================== */}
        {savedAccount && (
          <>
            <section className="dash-card">
              <h2>등록된 계좌 정보</h2>
              <p className="dash-small">
                계좌번호: {savedAccount.account_no_masked} / 상품코드:{" "}
                {savedAccount.account_code} (
                {savedAccount.real_mode ? "실거래" : "모의투자"})
              </p>
            </section>

            <section className="dash-card">
              <div className="dash-card-header">
                <h2>계좌 잔고 / 보유 종목</h2>
                <button onClick={fetchBalance}>잔고 조회</button>
              </div>

              {balanceParsed && (
                <>
                  <div className="dash-summary">
                   <span class="cash-icon">💰</span>{" "}
                    {balanceParsed.summary?.dnca_tot_amt?.toLocaleString() ||
                      "-"}
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
          </>
        )}
      </main>
    </div>
  );
}