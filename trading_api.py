"""
단순 트레이딩 백엔드 API (FastAPI).

- KIS 모의/실계좌에 시장가 주문을 넣는 엔드포인트
- 계좌 잔고/보유 종목 조회 엔드포인트

강화학습(SAC) 모델은 별도 프로세스에서 신호를 계산하고,
이 API에 주문 요청을 보내는 구조를 가정한다.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query, Header
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from kis_broker import KISBroker, KISConfig
from database import DatabaseManager, TradeOrder, AccountSnapshot, RiskSetting, AutoTradeRun


app = FastAPI(title="StuckAI Trading API", version="0.1.0")

# 전역 싱글톤 인스턴스 (토큰/DB 재사용)
_db_manager: Optional[DatabaseManager] = None
_broker: Optional[KISBroker] = None


def get_db() -> DatabaseManager:
    """전역 DB 매니저 (연결 및 테이블 생성 포함)."""
    global _db_manager
    if _db_manager is None:
        mgr = DatabaseManager()
        mgr.connect()
        mgr.create_tables()
        _db_manager = mgr
    return _db_manager


def get_broker() -> KISBroker:
    """
    KIS 브로커 인스턴스.
    - .env 의 KIS_* 설정을 사용한다.
    - 한 프로세스당 한 번만 생성하여 토큰을 재사용한다.
    """
    global _broker
    if _broker is None:
        cfg = KISConfig.from_env()
        _broker = KISBroker(cfg)
    return _broker


class MarketOrderRequest(BaseModel):
    stock_code: str = Field(..., description="6자리 종목코드 (예: '005930')")
    quantity: int = Field(..., gt=0, description="주문 수량 (양수)")
    side: str = Field(..., description="'BUY' 또는 'SELL'")


class BalanceResponse(BaseModel):
    raw: dict


# ---------------------------------------------------------------------------
# 리스크 한도 설정 (기본값: .env + DB risk_settings)
# ---------------------------------------------------------------------------

DEFAULT_MAX_POSITION_SHARES = int(os.getenv("RISK_MAX_POSITION_SHARES", "10"))
DEFAULT_MAX_WEIGHT_PCT = float(os.getenv("RISK_MAX_WEIGHT_PCT", "0.5"))  # 0~1
DEFAULT_MAX_DAILY_BUY_AMOUNT = float(os.getenv("RISK_MAX_DAILY_BUY_AMOUNT", "0"))  # 0이면 비활성


def check_risk_limit(broker: KISBroker, stock_code: str, side: str, quantity: int):
    """
    간단한 리스크 체크:
      - 매수:
          * 보유수량 + 주문수량 <= MAX_POSITION_SHARES
          * 매수 후 해당 종목 평가금액 비중이 총자산의 50%를 넘지 않도록 제한
      - 매도:
          * 보유수량/매도가능수량 이상으로 팔 수 없음
    """
    bal = broker.get_balance()
    raw = bal if isinstance(bal, dict) else {}
    holdings = raw.get("output1") or []
    summary_list = raw.get("output2") or []
    summary = summary_list[0] if summary_list else {}

    # DB에서 리스크 설정 조회 (종목별 우선, 없으면 "ALL", 다시 없으면 기본값)
    db = get_db()
    session = db.get_session()
    try:
        setting = (
            session.query(RiskSetting)
            .filter(RiskSetting.active.is_(True))
            .filter(RiskSetting.stock_code.in_([stock_code, "ALL"]))
            .order_by(RiskSetting.stock_code.desc())
            .first()
        )
    finally:
        session.close()

    max_shares = DEFAULT_MAX_POSITION_SHARES
    max_weight_pct = DEFAULT_MAX_WEIGHT_PCT
    max_daily_buy_amount = DEFAULT_MAX_DAILY_BUY_AMOUNT
    if setting:
        if setting.max_position_shares is not None:
            max_shares = setting.max_position_shares
        if setting.max_weight_pct is not None:
            max_weight_pct = setting.max_weight_pct
        if setting.max_daily_buy_amount is not None:
            max_daily_buy_amount = setting.max_daily_buy_amount

    current_qty = 0.0
    sellable = 0.0
    current_eval = 0.0
    current_price = None

    total_eval = 0.0
    for h in holdings:
        try:
            ev = float(h.get("evlu_amt") or 0)
        except (TypeError, ValueError):
            ev = 0.0
        total_eval += ev

        if h.get("pdno") == stock_code:
            try:
                current_qty = float(h.get("hldg_qty") or 0)
            except (TypeError, ValueError):
                current_qty = 0.0
            try:
                sellable = float(h.get("ord_psbl_qty") or 0)
            except (TypeError, ValueError):
                sellable = current_qty
            current_eval = ev
            try:
                current_price = float(h.get("prpr") or 0)
            except (TypeError, ValueError):
                current_price = None

    cash_raw = summary.get("dnca_tot_amt") or summary.get("nass_amt") or 0
    try:
        cash = float(cash_raw)
    except (TypeError, ValueError):
        cash = 0.0

    total_value = total_eval + cash

    if side == "BUY":
        # 일일 최대 매수 금액 한도 (옵션)
        if max_daily_buy_amount and max_daily_buy_amount > 0:
            db = get_db()
            session2 = db.get_session()
            try:
                today = datetime.utcnow().date()
                start = datetime.combine(today, datetime.min.time())
                # 오늘 체결된 BUY 주문 금액 합산
                orders = (
                    session2.query(TradeOrder)
                    .filter(
                        TradeOrder.created_at >= start,
                        TradeOrder.side == "BUY",
                        TradeOrder.status == "OK",
                    )
                    .all()
                )
                spent = 0.0
                for o in orders:
                    try:
                        spent += float(o.order_amount or 0)
                    except (TypeError, ValueError):
                        continue

                est_price = current_price or 0.0
                est_amount = est_price * quantity if est_price > 0 else 0.0

                if est_amount > 0 and spent + est_amount > max_daily_buy_amount + 1e-6:
                    remain = max(0.0, max_daily_buy_amount - spent)
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"리스크 한도 초과: 오늘 남은 매수 가능 금액 {int(remain):,}원을 초과합니다. "
                            f"(설정 한도 {int(max_daily_buy_amount):,}원)"
                        ),
                    )
            finally:
                session2.close()

        # 수량 한도
        if current_qty + quantity > max_shares:
            raise HTTPException(
                status_code=400,
                detail=f"리스크 한도 초과: {stock_code} 최대 보유 수량은 {max_shares}주 입니다. (현재 {int(current_qty)}주 보유)",
            )

        # 비중 한도 (50%)
        if total_value > 0:
            # 현재가 확보: 없으면 평균단가로 근사, 그래도 없으면 비중 체크 스킵
            if (current_price is None or current_price <= 0) and current_qty > 0:
                current_price = current_eval / max(current_qty, 1.0)

            if current_price and current_price > 0:
                projected_stock_value = current_eval + current_price * quantity
                projected_total_value = total_value - current_eval + projected_stock_value
                if projected_total_value > 0:
                    weight = projected_stock_value / projected_total_value
                if weight > max_weight_pct + 1e-9:
                        raise HTTPException(
                            status_code=400,
                        detail=(
                            f"리스크 한도 초과: {stock_code} 매수 시 예상 비중이 {weight*100:.1f}%로, "
                            f"종목별 최대 비중 {max_weight_pct*100:.0f}%를 초과합니다."
                        ),
                        )
    else:  # SELL
        if quantity > sellable:
            raise HTTPException(
                status_code=400,
                detail=f"리스크 한도 초과: 보유/매도가능 수량({int(sellable)}주) 이상은 매도할 수 없습니다.",
            )


class PerformanceSnapshot(BaseModel):
    timestamp: datetime
    total_value: float
    cash: float
    total_buy_amount: float
    total_eval_amount: float
    total_pnl: float


class PerformanceSummary(BaseModel):
    start_value: float
    end_value: float
    total_return_pct: float
    max_drawdown_pct: float
    pnl_sum: float


class PerformanceResponse(BaseModel):
    summary: PerformanceSummary
    snapshots: List[PerformanceSnapshot]


class OrderHistoryItem(BaseModel):
    created_at: datetime
    stock_code: str
    stock_name: Optional[str]
    side: str
    quantity: int
    order_price: Optional[float]
    order_amount: Optional[float]
    status: str


class RiskSettingIn(BaseModel):
    max_position_shares: Optional[int] = None
    max_weight_pct: Optional[float] = None
    max_daily_buy_amount: Optional[float] = None
    active: Optional[bool] = True


class RiskSettingOut(BaseModel):
    stock_code: str
    max_position_shares: Optional[int]
    max_weight_pct: Optional[float]
    max_daily_buy_amount: Optional[float]
    active: bool
    created_at: datetime
    updated_at: Optional[datetime]


class AutoTradeRunResult(BaseModel):
    returncode: int
    stdout: str
    stderr: str


class AutoTradeRunItem(BaseModel):
    id: int
    created_at: datetime
    returncode: int


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def dashboard():
    """
    간단 웹 대시보드 (잔고 조회 + 시장가 주문).

    - 브라우저에서 http://localhost:8000/ 으로 접속
    - 우측 상단 버튼으로 잔고 조회
    - 아래 폼으로 간단한 시장가 주문 테스트
    """
    return """
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <title>StuckAI Trading Dashboard</title>
  <style>
    body { font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; padding: 0; background-color: #0f172a; color: #e5e7eb; }
    header { padding: 16px 24px; border-bottom: 1px solid #1f2937; display: flex; justify-content: space-between; align-items: center; }
    .title { font-size: 20px; font-weight: 600; }
    .chip { font-size: 12px; padding: 2px 8px; border-radius: 999px; background: rgba(34,197,94,0.15); color: #4ade80; border: 1px solid rgba(34,197,94,0.4); margin-left: 8px; }
    main { padding: 24px; display: grid; grid-template-columns: 2fr 1.5fr; gap: 24px; }
    .card { background-color: #020617; border-radius: 12px; border: 1px solid #1f2937; padding: 16px 18px; box-shadow: 0 10px 30px rgba(15,23,42,0.7); }
    .card h2 { font-size: 16px; margin: 0 0 8px 0; display: flex; align-items: center; justify-content: space-between; }
    .subtitle { font-size: 12px; color: #9ca3af; margin-bottom: 8px; }
    button { background: linear-gradient(to right, #4ade80, #22c55e); color: #020617; border: none; padding: 6px 12px; border-radius: 8px; font-size: 13px; cursor: pointer; font-weight: 500; }
    button:disabled { opacity: 0.6; cursor: default; }
    input, select { background-color: #020617; border-radius: 8px; border: 1px solid #374151; padding: 6px 8px; color: #e5e7eb; font-size: 13px; width: 100%; box-sizing: border-box; }
    label { font-size: 12px; color: #9ca3af; margin-bottom: 4px; display: block; }
    .grid { display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 12px; margin-top: 8px; }
    pre { background-color: #020617; border-radius: 8px; padding: 8px 10px; font-size: 11px; max-height: 360px; overflow: auto; border: 1px solid #111827; }
    .tag { font-size: 11px; padding: 2px 6px; border-radius: 999px; background: #111827; color: #9ca3af; border: 1px solid #1f2937; }
    .row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
    .small { font-size: 11px; color: #6b7280; }
    .status { font-size: 12px; margin-top: 6px; min-height: 18px; }
    .status.ok { color: #4ade80; }
    .status.err { color: #f97373; }
  </style>
</head>
<body>
  <header>
    <div class="title">
      StuckAI Trading Dashboard
      <span class="chip">SAC + KIS Demo</span>
    </div>
    <div class="row">
      <span class="small">백엔드: FastAPI · 브로커: KIS</span>
    </div>
  </header>
  <main>
    <section class="card">
      <h2>
        계좌 잔고 / 포지션
        <button id="btn-balance">잔고 조회</button>
      </h2>
      <div class="subtitle">KIS OpenAPI에서 현재 잔고/보유 종목을 조회해 요약 테이블로 보여줍니다.</div>
      <div id="balance-summary" class="small" style="margin-bottom:8px;"></div>
      <div id="balance-table"></div>
      <details style="margin-top:10px;">
        <summary class="small">원본 JSON 보기</summary>
        <pre id="balance-output" style="margin-top:6px;">{ 잔고 정보를 불러오려면 상단의 "잔고 조회" 버튼을 누르세요 }</pre>
      </details>
    </section>

    <section class="card">
      <h2>
        성과 요약 (최근 30일)
        <button id="btn-refresh-performance">새로고침</button>
      </h2>
      <div class="subtitle">일별 계좌 총자산과 손익을 기반으로 성과를 요약해 보여줍니다.</div>
      <div id="perf-summary" class="small" style="margin-bottom:8px;"></div>
      <div id="perf-table"></div>
    </section>

    <section class="card">
      <h2>
        시장가 주문 테스트
        <span class="tag">POST /orders/market</span>
      </h2>
      <div class="subtitle">강화학습/전략 엔진이 결정한 주문을 이 엔드포인트로 전달해 실제 체결을 시도합니다.</div>
      <div class="grid">
        <div>
          <label for="stock-code">종목코드</label>
          <input id="stock-code" placeholder="예: 005930" />
        </div>
        <div>
          <label for="quantity">수량</label>
          <input id="quantity" type="number" min="1" step="1" value="1" />
        </div>
        <div>
          <label for="side">방향</label>
          <select id="side">
            <option value="BUY">BUY (매수)</option>
            <option value="SELL">SELL (매도)</option>
          </select>
        </div>
      </div>
      <div class="row" style="margin-top: 12px;">
        <button id="btn-order">시장가 주문 전송</button>
        <span class="small">주의: .env 의 KIS_* 설정에 따라 실제 모의/실계좌 주문이 발생할 수 있습니다.</span>
      </div>
      <div id="order-status" class="status"></div>
      <pre id="order-output">{ 주문 응답이 여기에 표시됩니다 }</pre>
    </section>

    <section class="card">
      <h2>
        거래 내역
        <button id="btn-refresh-orders">새로고침</button>
      </h2>
      <div class="subtitle">최근 자동/수동 주문 기록을 확인할 수 있습니다.</div>
      <div class="row" style="margin-bottom:8px;">
        <div class="small">종목코드로 필터링 (예: 005930)</div>
        <input id="orders-symbol" placeholder="전체" style="max-width:120px;" />
      </div>
      <div id="orders-table"></div>
    </section>

    <section class="card">
      <h2>
        리스크 설정
        <button id="btn-refresh-risk">새로고침</button>
      </h2>
      <div class="subtitle">종목별 최대 보유 수량, 비중 한도 등을 설정합니다.</div>
      <div class="small" style="margin-bottom:8px;">
        - 'ALL' 설정은 공통 기본값으로 사용되며, 종목별 설정이 있으면 그것이 우선합니다.
      </div>
      <div class="grid">
        <div>
          <label for="risk-stock">종목코드 / ALL</label>
          <input id="risk-stock" placeholder="예: 005930 또는 ALL" />
        </div>
        <div>
          <label for="risk-max-shares">최대 보유 수량</label>
          <input id="risk-max-shares" type="number" min="1" step="1" placeholder="비우면 기본값 유지" />
        </div>
        <div>
          <label for="risk-max-weight">최대 비중 (%)</label>
          <input id="risk-max-weight" type="number" min="0" max="100" step="1" placeholder="예: 50" />
        </div>
      </div>
      <div class="grid" style="margin-top:8px;">
        <div>
          <label for="risk-max-daily">일간 최대 매수금액 (원)</label>
          <input id="risk-max-daily" type="number" min="0" step="10000" placeholder="옵션" />
        </div>
        <div>
          <label for="risk-active">활성 여부</label>
          <select id="risk-active">
            <option value="true">활성</option>
            <option value="false">비활성</option>
          </select>
        </div>
        <div>
          <label for="risk-api-key">API Key (보안)</label>
          <input id="risk-api-key" type="password" placeholder="PUT 시 X-API-Key로 사용" />
        </div>
      </div>
      <div class="row" style="margin-top:12px;">
        <button id="btn-save-risk">설정 저장</button>
        <span class="small">주의: 저장 시 API Key 가 필요합니다.</span>
      </div>
      <div id="risk-status" class="status"></div>
      <div id="risk-table" style="margin-top:8px;"></div>
    </section>
  </main>

  <script>
    async function fetchJson(url, options) {
      const res = await fetch(url, options);
      const text = await res.text();
      try {
        return { ok: res.ok, status: res.status, json: JSON.parse(text) };
      } catch (e) {
        return { ok: res.ok, status: res.status, json: { raw: text } };
      }
    }

    const btnBalance = document.getElementById("btn-balance");
    const balanceOut = document.getElementById("balance-output");
    const balanceSummary = document.getElementById("balance-summary");
    const balanceTable = document.getElementById("balance-table");
    const btnOrder = document.getElementById("btn-order");
    const orderOut = document.getElementById("order-output");
    const orderStatus = document.getElementById("order-status");
    const btnPerf = document.getElementById("btn-refresh-performance");
    const perfSummary = document.getElementById("perf-summary");
    const perfTable = document.getElementById("perf-table");
    const btnOrders = document.getElementById("btn-refresh-orders");
    const ordersTable = document.getElementById("orders-table");
    const ordersSymbol = document.getElementById("orders-symbol");
    const btnRiskRefresh = document.getElementById("btn-refresh-risk");
    const btnRiskSave = document.getElementById("btn-save-risk");
    const riskStock = document.getElementById("risk-stock");
    const riskMaxShares = document.getElementById("risk-max-shares");
    const riskMaxWeight = document.getElementById("risk-max-weight");
    const riskMaxDaily = document.getElementById("risk-max-daily");
    const riskActive = document.getElementById("risk-active");
    const riskApiKey = document.getElementById("risk-api-key");
    const riskStatus = document.getElementById("risk-status");
    const riskTable = document.getElementById("risk-table");

    function renderBalanceNice(raw) {
      balanceTable.innerHTML = "";
      balanceSummary.textContent = "";

      if (!raw || typeof raw !== "object") {
        balanceTable.innerHTML = "<div class='small'>잔고 데이터를 해석할 수 없습니다.</div>";
        return;
      }

      const holdings = Array.isArray(raw.output1) ? raw.output1 : [];
      const summaryArr = Array.isArray(raw.output2) ? raw.output2 : [];
      const summary = summaryArr[0] || {};

      // 요약 영역: 총 보유수량, 총 매입금액, 평가금액, 손익
      let totalQty = 0;
      let totalBuyAmt = 0;
      let totalEvalAmt = 0;
      let totalPnl = 0;
      for (const h of holdings) {
        const q = parseFloat(h.hldg_qty || "0");
        const buyAmt = parseFloat(h.pchs_amt || "0");
        const evalAmt = parseFloat(h.evlu_amt || "0");
        const pnl = parseFloat(h.evlu_pfls_amt || "0");
        if (!Number.isNaN(q)) totalQty += q;
        if (!Number.isNaN(buyAmt)) totalBuyAmt += buyAmt;
        if (!Number.isNaN(evalAmt)) totalEvalAmt += evalAmt;
        if (!Number.isNaN(pnl)) totalPnl += pnl;
      }

      const cash = summary.dnca_tot_amt || summary.nass_amt || null;
      const parts = [];
      if (!Number.isNaN(totalQty) && totalQty > 0) {
        parts.push(`총 보유수량: ${totalQty}주`);
      }
      if (!Number.isNaN(totalBuyAmt) && totalBuyAmt !== 0) {
        parts.push(`총 매입금액: ${totalBuyAmt.toLocaleString()}원`);
      }
      if (!Number.isNaN(totalEvalAmt) && totalEvalAmt !== 0) {
        parts.push(`평가금액: ${totalEvalAmt.toLocaleString()}원`);
      }
      if (!Number.isNaN(totalPnl) && totalPnl !== 0) {
        const sign = totalPnl >= 0 ? "+" : "";
        parts.push(`평가손익: ${sign}${totalPnl.toLocaleString()}원`);
      }
      if (cash != null) {
        const cashNum = Number(cash);
        if (!Number.isNaN(cashNum)) {
          parts.push(`예수금: ${cashNum.toLocaleString()}원`);
        }
      }

      if (parts.length) {
        balanceSummary.textContent = parts.join(" · ");
      }

      if (!holdings.length) {
        balanceTable.innerHTML = "<div class='small'>보유 종목이 없습니다.</div>";
        return;
      }

      // 보유 종목 테이블
      const columns = [
        { key: "pdno", label: "종목코드" },
        { key: "prdt_name", label: "종목명" },
        { key: "hldg_qty", label: "보유수량" },
        { key: "ord_psbl_qty", label: "매도가능" },
        { key: "pchs_avg_pric", label: "평균매입가" },
        { key: "evlu_pfls_amt", label: "평가손익" },
      ];

      let html = "<table style='width:100%; border-collapse:collapse; font-size:12px;'>";
      html += "<thead><tr>";
      for (const col of columns) {
        html += `<th style="text-align:left; padding:4px 6px; border-bottom:1px solid #1f2937; color:#9ca3af;">${col.label}</th>`;
      }
      html += "</tr></thead><tbody>";

      for (const row of holdings) {
        html += "<tr>";
        for (const col of columns) {
          const v = row[col.key] != null ? row[col.key] : "";
          html += `<td style="padding:4px 6px; border-bottom:1px solid #111827;">${v}</td>`;
        }
        html += "</tr>";
      }
      html += "</tbody></table>";

      balanceTable.innerHTML = html;
    }

    btnBalance.addEventListener("click", async () => {
      btnBalance.disabled = true;
      balanceOut.textContent = "불러오는 중...";
      balanceTable.innerHTML = "";
      balanceSummary.textContent = "";
      try {
        const res = await fetchJson("/accounts/balance");
        const raw = res.json && res.json.raw ? res.json.raw : res.json;
        balanceOut.textContent = JSON.stringify(raw, null, 2);
        if (res.ok) {
          renderBalanceNice(raw);
        }
      } catch (e) {
        balanceOut.textContent = "에러: " + e;
      } finally {
        btnBalance.disabled = false;
      }
    });

    btnPerf.addEventListener("click", async () => {
      btnPerf.disabled = true;
      perfSummary.textContent = "로딩 중...";
      perfTable.innerHTML = "";
      try {
        const res = await fetchJson("/metrics/performance?days=30");
        if (!res.ok) {
          perfSummary.textContent = "성능 조회 실패: " + (res.json && res.json.detail ? res.json.detail : "오류");
          return;
        }
        const data = res.json;
        const s = data.summary || {};
        const snaps = data.snapshots || [];

        perfSummary.textContent =
          `시작자산: ${Math.round(s.start_value || 0).toLocaleString()}원 · ` +
          `현재자산: ${Math.round(s.end_value || 0).toLocaleString()}원 · ` +
          `누적수익률: ${(s.total_return_pct || 0).toFixed(2)}% · ` +
          `최대낙폭: ${(s.max_drawdown_pct || 0).toFixed(2)}% · ` +
          `누적손익: ${((s.pnl_sum || 0) >= 0 ? "+" : "") + Math.round(s.pnl_sum || 0).toLocaleString()}원`;

        if (!snaps.length) {
          perfTable.innerHTML = "<div class='small'>스냅샷 데이터가 없습니다. 먼저 잔고 조회를 실행해 주세요.</div>";
          return;
        }

        let html = "<table style='width:100%; border-collapse:collapse; font-size:12px;'>";
        html += "<thead><tr>";
        const cols = ["시각", "총자산", "예수금", "총매입", "평가금액", "총손익"];
        for (const c of cols) {
          html += `<th style="text-align:left; padding:4px 6px; border-bottom:1px solid #1f2937; color:#9ca3af;">${c}</th>`;
        }
        html += "</tr></thead><tbody>";
        for (const row of snaps.slice().reverse()) {
          const dt = new Date(row.timestamp);
          const ts = dt.toLocaleString();
          const tv = Math.round(row.total_value || 0).toLocaleString();
          const cash = Math.round(row.cash || 0).toLocaleString();
          const tb = Math.round(row.total_buy_amount || 0).toLocaleString();
          const te = Math.round(row.total_eval_amount || 0).toLocaleString();
          const pnl = Math.round(row.total_pnl || 0);
          const pnlStr = (pnl >= 0 ? "+" : "") + pnl.toLocaleString();
          html += `<tr>
            <td style="padding:4px 6px; border-bottom:1px solid  #111827;">${ts}</td>
            <td style="padding:4px 6px; border-bottom:1px solid  #111827;">${tv}</td>
            <td style="padding:4px 6px; border-bottom:1px solid  #111827;">${cash}</td>
            <td style="padding:4px 6px; border-bottom:1px solid  #111827;">${tb}</td>
            <td style="padding:4px 6px; border-bottom:1px solid  #111827;">${te}</td>
            <td style="padding:4px 6px; border-bottom:1px solid  #111827;">${pnlStr}</td>
          </tr>`;
        }
        html += "</tbody></table>";
        perfTable.innerHTML = html;
      } catch (e) {
        perfSummary.textContent = "에러: " + e;
      } finally {
        btnPerf.disabled = false;
      }
    });

    btnOrders.addEventListener("click", async () => {
      btnOrders.disabled = true;
      ordersTable.innerHTML = "<div class='small'>로딩 중...</div>";
      try {
        const symbol = (ordersSymbol.value || "").trim();
        let url = "/orders/history?limit=100";
        if (symbol) {
          url += "&stock_code=" + encodeURIComponent(symbol);
        }
        const res = await fetchJson(url);
        if (!res.ok) {
          ordersTable.innerHTML = "<div class='small'>주문 내역 조회 실패: " + (res.json && res.json.detail ? res.json.detail : "오류") + "</div>";
          return;
        }
        const rows = Array.isArray(res.json) ? res.json : [];
        if (!rows.length) {
          ordersTable.innerHTML = "<div class='small'>표시할 주문 내역이 없습니다.</div>";
          return;
        }
        let html = "<table style='width:100%; border-collapse:collapse; font-size:12px;'>";
        html += "<thead><tr>";
        const cols = ["시간", "종목코드", "종목명", "방향", "수량", "가격", "금액", "상태"];
        for (const c of cols) {
          html += `<th style="text-align:left; padding:4px 6px; border-bottom:1px solid #1f2937; color:#9ca3af;">${c}</th>`;
        }
        html += "</tr></thead><tbody>";
        for (const o of rows) {
          const dt = new Date(o.created_at);
          const ts = dt.toLocaleString();
          const price = o.order_price != null ? o.order_price.toLocaleString() : "-";
          const amt = o.order_amount != null ? o.order_amount.toLocaleString() : "-";
          html += `<tr>
            <td style="padding:4px 6px; border-bottom:1px solid #111827;">${ts}</td>
            <td style="padding:4px 6px; border-bottom:1px solid #111827;">${o.stock_code}</td>
            <td style="padding:4px 6px; border-bottom:1px solid #111827;">${o.stock_name || ""}</td>
            <td style="padding:4px 6px; border-bottom:1px solid #111827;">${o.side}</td>
            <td style="padding:4px 6px; border-bottom:1px solid #111827;">${o.quantity}</td>
            <td style="padding:4px 6px; border-bottom:1px solid #111827;">${price}</td>
            <td style="padding:4px 6px; border-bottom:1px solid #111827;">${amt}</td>
            <td style="padding:4px 6px; border-bottom:1px solid #111827;">${o.status}</td>
          </tr>`;
        }
        html += "</tbody></table>";
        ordersTable.innerHTML = html;
      } catch (e) {
        ordersTable.innerHTML = "<div class='small'>에러: " + e + "</div>";
      } finally {
        btnOrders.disabled = false;
      }
    });

    async function loadRiskSettings() {
      riskTable.innerHTML = "<div class='small'>로딩 중...</div>";
      try {
        const res = await fetchJson("/settings/risk");
        if (!res.ok) {
          riskTable.innerHTML = "<div class='small'>리스크 설정 조회 실패: " + (res.json && res.json.detail ? res.json.detail : "오류") + "</div>";
          return;
        }
        const rows = Array.isArray(res.json) ? res.json : [];
        if (!rows.length) {
          riskTable.innerHTML = "<div class='small'>설정된 리스크 규칙이 없습니다.</div>";
          return;
        }
        let html = "<table style='width:100%; border-collapse:collapse; font-size:12px;'>";
        html += "<thead><tr>";
        const cols = ["종목코드", "최대수량", "최대비중(%)", "일간매수한도", "활성", "생성", "수정"];
        for (const c of cols) {
          html += `<th style="text-align:left; padding:4px 6px; border-bottom:1px solid #1f2937; color:#9ca3af;">${c}</th>`;
        }
        html += "</tr></thead><tbody>";
        for (const r of rows) {
          const w = r.max_weight_pct != null ? (r.max_weight_pct * 100).toFixed(0) : "-";
          const daily = r.max_daily_buy_amount != null ? Math.round(r.max_daily_buy_amount).toLocaleString() : "-";
          html += `<tr>
            <td style="padding:4px 6px; border-bottom:1px solid #111827;">${r.stock_code}</td>
            <td style="padding:4px 6px; border-bottom:1px solid #111827;">${r.max_position_shares ?? "-"}</td>
            <td style="padding:4px 6px; border-bottom:1px solid #111827;">${w}</td>
            <td style="padding:4px 6px; border-bottom:1px solid #111827;">${daily}</td>
            <td style="padding:4px 6px; border-bottom:1px solid #111827;">${r.active ? "ON" : "OFF"}</td>
            <td style="padding:4px 6px; border-bottom:1px solid #111827;">${r.created_at}</td>
            <td style="padding:4px 6px; border-bottom:1px solid #111827;">${r.updated_at || ""}</td>
          </tr>`;
        }
        html += "</tbody></table>";
        riskTable.innerHTML = html;
      } catch (e) {
        riskTable.innerHTML = "<div class='small'>에러: " + e + "</div>";
      }
    }

    btnRiskRefresh.addEventListener("click", loadRiskSettings);

    btnRiskSave.addEventListener("click", async () => {
      const code = (riskStock.value || "").trim();
      if (!code) {
        riskStatus.textContent = "종목코드 또는 ALL 을 입력하세요.";
        riskStatus.className = "status err";
        return;
      }
      const body = {};
      if (riskMaxShares.value) body.max_position_shares = Number(riskMaxShares.value);
      if (riskMaxWeight.value) body.max_weight_pct = Number(riskMaxWeight.value) / 100.0;
      if (riskMaxDaily.value) body.max_daily_buy_amount = Number(riskMaxDaily.value);
      body.active = riskActive.value === "true";

      const apiKey = (riskApiKey.value || "").trim();
      const headers = { "Content-Type": "application/json" };
      if (apiKey) headers["X-API-Key"] = apiKey;

      btnRiskSave.disabled = true;
      riskStatus.textContent = "저장 중...";
      riskStatus.className = "status";
      try {
        const res = await fetchJson(`/settings/risk/${encodeURIComponent(code)}`, {
          method: "PUT",
          headers,
          body: JSON.stringify(body),
        });
        if (!res.ok) {
          riskStatus.textContent = "저장 실패: " + (res.json && res.json.detail ? res.json.detail : "오류");
          riskStatus.className = "status err";
          return;
        }
        riskStatus.textContent = "저장 완료";
        riskStatus.className = "status ok";
        await loadRiskSettings();
      } catch (e) {
        riskStatus.textContent = "에러: " + e;
        riskStatus.className = "status err";
      } finally {
        btnRiskSave.disabled = false;
      }
    });

    btnOrder.addEventListener("click", async () => {
      const code = (document.getElementById("stock-code").value || "").trim();
      const qty = parseInt(document.getElementById("quantity").value || "0", 10);
      const side = document.getElementById("side").value;

      if (!code) {
        orderStatus.textContent = "종목코드를 입력하세요.";
        orderStatus.className = "status err";
        return;
      }
      if (!qty || qty <= 0) {
        orderStatus.textContent = "1 이상 수량을 입력하세요.";
        orderStatus.className = "status err";
        return;
      }

      btnOrder.disabled = true;
      orderStatus.textContent = "주문 전송 중...";
      orderStatus.className = "status";
      orderOut.textContent = "";

      try {
        const res = await fetchJson("/orders/market", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ stock_code: code, quantity: qty, side })
        });
        orderOut.textContent = JSON.stringify(res.json, null, 2);
        if (res.ok) {
          orderStatus.textContent = "주문 성공 (status " + res.status + ")";
          orderStatus.className = "status ok";
        } else {
          orderStatus.textContent = "주문 실패 (status " + res.status + ")";
          orderStatus.className = "status err";
        }
      } catch (e) {
        orderStatus.textContent = "요청 에러: " + e;
        orderStatus.className = "status err";
      } finally {
        btnOrder.disabled = false;
      }
    });
  </script>
</body>
</html>
    """


@app.post("/orders/market")
def place_market_order(
    req: MarketOrderRequest,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    """
    단순 시장가 주문 엔드포인트.

    강화학습/전략 엔진은:
      1) 어떤 종목을 얼마만큼 매수/매도할지 결정하고
      2) 이 엔드포인트에 POST를 보내 실제 주문을 실행한다.

    주문 결과는 `trade_orders` 테이블에 로그로 저장된다.
    """
    # 간단한 API 키 인증 (옵션)
    expected_key = os.getenv("API_KEY")
    if expected_key and x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="유효하지 않은 API Key 입니다.")

    broker = get_broker()
    db = get_db()

    side = req.side.upper()
    if side not in ("BUY", "SELL"):
        raise HTTPException(status_code=400, detail="side 는 'BUY' 또는 'SELL' 이어야 합니다.")

    # 리스크 한도 체크
    check_risk_limit(broker, stock_code=req.stock_code, side=side, quantity=req.quantity)

    try:
        if side == "BUY":
            res = broker.buy_market(stock_code=req.stock_code, quantity=req.quantity)
        else:
            res = broker.sell_market(stock_code=req.stock_code, quantity=req.quantity)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"KIS 주문 실패: {e}")

    # 주문 로그 저장
    session = db.get_session()
    try:
        output = res.get("output") if isinstance(res, dict) else None
        stock_name = output.get("PDNAME") if isinstance(output, dict) else None
        order_price = None
        order_amount = None
        if isinstance(output, dict):
            try:
                order_price = float(output.get("ORD_UNPR") or 0)
                qty = float(output.get("ORD_QTY") or req.quantity)
                order_amount = order_price * qty
            except Exception:
                pass
        order = TradeOrder(
            stock_code=req.stock_code,
            stock_name=stock_name,
            side=side,
            quantity=req.quantity,
            order_price=order_price,
            order_amount=order_amount,
            status="OK" if isinstance(res, dict) and res.get("rt_cd") in (None, "0") else "ERROR",
            raw_response=json.dumps(res, ensure_ascii=False),
        )
        session.add(order)
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()

    return {"status": "ok", "response": res}


@app.get("/accounts/balance", response_model=BalanceResponse)
def get_account_balance():
    """
    KIS 계좌 잔고/보유 종목 조회.

    조회 결과는 `account_snapshots` 테이블에 요약 형태로 저장된다.
    """
    broker = get_broker()
    db = get_db()
    try:
        bal = broker.get_balance()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"KIS 잔고 조회 실패: {e}")

    # 스냅샷 저장
    raw = bal if isinstance(bal, dict) else {}
    holdings = raw.get("output1") or []
    summary_list = raw.get("output2") or []
    summary = summary_list[0] if summary_list else {}

    total_buy = 0.0
    total_eval = 0.0
    total_pnl = 0.0
    for h in holdings:
        try:
            buy_amt = float(h.get("pchs_amt") or 0)
            eval_amt = float(h.get("evlu_amt") or 0)
            pnl = float(h.get("evlu_pfls_amt") or 0)
        except (TypeError, ValueError):
            continue
        total_buy += buy_amt
        total_eval += eval_amt
        total_pnl += pnl

    cash_raw = summary.get("dnca_tot_amt") or summary.get("nass_amt") or 0
    try:
        cash = float(cash_raw)
    except (TypeError, ValueError):
        cash = 0.0

    total_value = total_eval + cash

    session = db.get_session()
    try:
        snap = AccountSnapshot(
            total_value=total_value,
            cash=cash,
            total_buy_amount=total_buy,
            total_eval_amount=total_eval,
            total_pnl=total_pnl,
            raw_response=json.dumps(raw, ensure_ascii=False),
        )
        session.add(snap)
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()

    return BalanceResponse(raw=bal)


@app.get("/metrics/performance", response_model=PerformanceResponse)
def get_performance(days: int = Query(30, ge=1, le=365)):
    """
    최근 N일간의 계좌 성과 요약 및 스냅샷을 반환.

    - days: 최근 N일 (기본 30일)
    """
    db = get_db()
    session = db.get_session()
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        rows = (
            session.query(AccountSnapshot)
            .filter(AccountSnapshot.created_at >= cutoff)
            .order_by(AccountSnapshot.created_at.asc())
            .all()
        )
    finally:
        session.close()

    if not rows:
        return PerformanceResponse(
            summary=PerformanceSummary(
                start_value=0.0, end_value=0.0, total_return_pct=0.0, max_drawdown_pct=0.0, pnl_sum=0.0
            ),
            snapshots=[],
        )

    snaps: List[PerformanceSnapshot] = []
    equity: List[float] = []
    for r in rows:
        snaps.append(
            PerformanceSnapshot(
                timestamp=r.created_at,
                total_value=r.total_value or 0.0,
                cash=r.cash or 0.0,
                total_buy_amount=r.total_buy_amount or 0.0,
                total_eval_amount=r.total_eval_amount or 0.0,
                total_pnl=r.total_pnl or 0.0,
            )
        )
        equity.append(r.total_value or 0.0)

    start_val = equity[0]
    end_val = equity[-1]
    total_return_pct = ((end_val - start_val) / start_val * 100.0) if start_val not in (0, None) else 0.0

    # 최대 낙폭 계산
    max_peak = equity[0]
    max_dd = 0.0
    for v in equity:
        if v > max_peak:
            max_peak = v
        if max_peak > 0:
            dd = (max_peak - v) / max_peak * 100.0
            if dd > max_dd:
                max_dd = dd

    pnl_sum = sum((s.total_pnl for s in snaps))

    summary = PerformanceSummary(
        start_value=start_val,
        end_value=end_val,
        total_return_pct=total_return_pct,
        max_drawdown_pct=max_dd,
        pnl_sum=pnl_sum,
    )

    return PerformanceResponse(summary=summary, snapshots=snaps)


@app.get("/orders/history", response_model=List[OrderHistoryItem])
def get_order_history(
    stock_code: Optional[str] = Query(default=None, description="필터링할 종목코드 (예: 005930)"),
    limit: int = Query(100, ge=1, le=1000),
):
    """최근 주문 내역 조회. stock_code 로 필터링 가능."""
    db = get_db()
    session = db.get_session()
    try:
        q = session.query(TradeOrder).order_by(TradeOrder.created_at.desc())
        if stock_code:
            q = q.filter(TradeOrder.stock_code == stock_code)
        rows = q.limit(limit).all()
    finally:
        session.close()

    result: List[OrderHistoryItem] = []
    for r in rows:
        result.append(
            OrderHistoryItem(
                created_at=r.created_at,
                stock_code=r.stock_code,
                stock_name=r.stock_name,
                side=r.side,
                quantity=r.quantity,
                order_price=r.order_price,
                order_amount=r.order_amount,
                status=r.status,
            )
        )
    return result


@app.post("/auto-trade/run-once", response_model=AutoTradeRunResult)
def run_auto_trade_once(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    """
    일일 자동 매매 스크립트를 1회 실행합니다.

    내부적으로 `python auto_trader.py`를 서브프로세스로 실행합니다.
    실행 로그는 stdout/stderr 로 반환됩니다.
    """
    # API Key 검증
    expected_key = os.getenv("API_KEY")
    if expected_key and x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="유효하지 않은 API Key 입니다.")

    script_path = Path(__file__).parent / "auto_trader.py"
    if not script_path.exists():
        raise HTTPException(status_code=500, detail=f"auto_trader 스크립트를 찾을 수 없습니다: {script_path}")

    try:
        proc = subprocess.run(
            ["python", str(script_path)],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired as e:
        raise HTTPException(status_code=500, detail=f"auto_trader 실행 시간 초과: {e}")

    # 실행 결과를 DB에 기록
    db = get_db()
    session = db.get_session()
    try:
        run = AutoTradeRun(
            returncode=proc.returncode,
            stdout=proc.stdout[-2000:],  # 로그가 너무 길 경우 끝부분만 저장
            stderr=proc.stderr[-2000:],
        )
        session.add(run)
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()

    return AutoTradeRunResult(returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)


@app.get("/auto-trade/status", response_model=List[AutoTradeRunItem])
def get_auto_trade_status(limit: int = Query(5, ge=1, le=50)):
    """
    최근 자동매매 실행 이력을 반환합니다.

    - returncode == 0 이면 정상 종료, 그 외는 오류.
    """
    db = get_db()
    session = db.get_session()
    try:
        rows = (
            session.query(AutoTradeRun)
            .order_by(AutoTradeRun.created_at.desc())
            .limit(limit)
            .all()
        )
    finally:
        session.close()

    result: List[AutoTradeRunItem] = []
    for r in rows:
        result.append(
            AutoTradeRunItem(
                id=r.id,
                created_at=r.created_at,
                returncode=r.returncode,
            )
        )
    return result


@app.get("/settings/risk", response_model=List[RiskSettingOut])
def list_risk_settings(stock_code: Optional[str] = Query(default=None, description="필터링할 종목코드 (예: 005930 또는 ALL)")):
    """
    현재 저장된 리스크/포지션 한도 설정 목록 조회.

    - stock_code 를 지정하면 해당 종목(또는 'ALL')만 반환
    """
    db = get_db()
    session = db.get_session()
    try:
        q = session.query(RiskSetting)
        if stock_code:
            q = q.filter(RiskSetting.stock_code == stock_code)
        rows = q.order_by(RiskSetting.stock_code.asc()).all()
    finally:
        session.close()

    result: List[RiskSettingOut] = []
    for r in rows:
        result.append(
            RiskSettingOut(
                stock_code=r.stock_code,
                max_position_shares=r.max_position_shares,
                max_weight_pct=r.max_weight_pct,
                max_daily_buy_amount=r.max_daily_buy_amount,
                active=bool(r.active),
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
        )
    return result


@app.put("/settings/risk/{stock_code}", response_model=RiskSettingOut)
def upsert_risk_setting(
    stock_code: str,
    body: RiskSettingIn,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    """
    특정 종목(또는 'ALL')에 대한 리스크 한도 설정을 생성/수정한다.

    - stock_code: '005930', '035420', 'ALL' 등
    - body 에서 지정된 필드만 갱신 (나머지는 유지)
    """
    expected_key = os.getenv("API_KEY")
    if expected_key and x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="유효하지 않은 API Key 입니다.")

    db = get_db()
    session = db.get_session()
    try:
        setting = session.query(RiskSetting).filter(RiskSetting.stock_code == stock_code).first()
        if setting is None:
            setting = RiskSetting(stock_code=stock_code)

        if body.max_position_shares is not None:
            setting.max_position_shares = body.max_position_shares
        if body.max_weight_pct is not None:
            setting.max_weight_pct = body.max_weight_pct
        if body.max_daily_buy_amount is not None:
            setting.max_daily_buy_amount = body.max_daily_buy_amount
        if body.active is not None:
            setting.active = body.active

        session.add(setting)
        session.commit()
        session.refresh(setting)
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"리스크 설정 저장 실패: {e}")
    finally:
        session.close()

    return RiskSettingOut(
        stock_code=setting.stock_code,
        max_position_shares=setting.max_position_shares,
        max_weight_pct=setting.max_weight_pct,
        max_daily_buy_amount=setting.max_daily_buy_amount,
        active=bool(setting.active),
        created_at=setting.created_at,
        updated_at=setting.updated_at,
    )
