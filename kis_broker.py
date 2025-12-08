"""
KIS(한국투자증권) 국내주식 주문/잔고 전용 브로커 모듈.

역할:
  - KIS 모의/실전 계좌로 '주문 요청'을 보내고
  - 현재 잔고/보유 주식을 조회하는 최소 API 레이어

데이터 수집/모델 학습/백테스트는 그대로:
  - 수집: collect_yahoo_data.py (Yahoo Finance → PostgreSQL)
  - 전처리: daily_preprocess_classification.py
  - 학습: train_daily_classification.py
  - 백테스트: backtest_daily.py, backtest_daily_ma.py

이 모듈은 나중에 백테스트/실시간 신호 코드에서
VirtualAccount 대신 실제 KIS 계좌로 주문을 보낼 때 사용한다.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv


@dataclass
class KISConfig:
    """
    KIS 계좌/환경 설정.

    필수 환경변수 (.env):
      - KIS_APP_KEY
      - KIS_APP_SECRET
      - KIS_ACCOUNT_NO        예: "12345678"
      - KIS_ACCOUNT_CODE      예: "01"
      - KIS_REAL_MODE         "True" / "False" (기본 False: 모의투자)

    주문/잔고용 TR ID 는 증권사 문서에 따라 다르므로
    아래 환경변수를 통해 주입하도록 한다 (모의/실전 각각 별도일 수 있음).
      - KIS_TR_ID_ORDER_CASH_BUY
      - KIS_TR_ID_ORDER_CASH_SELL
      - KIS_TR_ID_INQUIRE_BALANCE
    """

    app_key: str
    app_secret: str
    account_no: str
    account_code: str
    real_mode: bool = False

    tr_id_order_cash_buy: str = ""
    tr_id_order_cash_sell: str = ""
    tr_id_inquire_balance: str = ""

    @classmethod
    def from_env(cls) -> "KISConfig":
        load_dotenv()

        app_key = os.getenv("KIS_APP_KEY", "")
        app_secret = os.getenv("KIS_APP_SECRET", "")
        account_no = os.getenv("KIS_ACCOUNT_NO", "")
        account_code = os.getenv("KIS_ACCOUNT_CODE", "")
        real_mode = os.getenv("KIS_REAL_MODE", "False").lower() == "true"

        tr_buy = os.getenv("KIS_TR_ID_ORDER_CASH_BUY", "")
        tr_sell = os.getenv("KIS_TR_ID_ORDER_CASH_SELL", "")
        tr_bal = os.getenv("KIS_TR_ID_INQUIRE_BALANCE", "")

        if not app_key or not app_secret:
            raise ValueError("KIS_APP_KEY / KIS_APP_SECRET 이 .env 에 설정되어야 합니다.")
        if not account_no or not account_code:
            raise ValueError("KIS_ACCOUNT_NO / KIS_ACCOUNT_CODE 가 .env 에 설정되어야 합니다.")

        return cls(
            app_key=app_key,
            app_secret=app_secret,
            account_no=account_no,
            account_code=account_code,
            real_mode=real_mode,
            tr_id_order_cash_buy=tr_buy,
            tr_id_order_cash_sell=tr_sell,
            tr_id_inquire_balance=tr_bal,
        )


class KISBroker:
    """
    KIS 국내주식 주문/잔고 조회 래퍼.

    - 인증/토큰 관리
    - 현금 주문 (매수/매도)
    - 잔고 조회
    """

    def __init__(self, config: Optional[KISConfig] = None):
        self.config = config or KISConfig.from_env()
        self.base_url = (
            "https://openapi.koreainvestment.com:9443"
            if self.config.real_mode
            else "https://openapivts.koreainvestment.com:29443"
        )

        self._access_token: Optional[str] = None
        self._token_expired_at: Optional[datetime] = None

    # ------------------------------------------------------------------ #
    # 내부 유틸: 토큰 / 헤더
    # ------------------------------------------------------------------ #
    def _get_access_token(self) -> str:
        """접근 토큰을 발급/캐시."""
        if self._access_token and self._token_expired_at:
            if datetime.now() < self._token_expired_at:
                return self._access_token

        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        data = {
            "grant_type": "client_credentials",
            "appkey": self.config.app_key,
            "appsecret": self.config.app_secret,
        }

        resp = requests.post(url, headers=headers, data=json.dumps(data))
        if resp.status_code != 200:
            raise RuntimeError(f"KIS 토큰 발급 실패: {resp.status_code} {resp.text}")

        js = resp.json()
        access_token = js.get("access_token")
        if not access_token:
            raise RuntimeError(f"KIS 토큰 응답에 access_token 이 없습니다: {js}")

        self._access_token = access_token
        # 24시간 유효하므로, 여유를 두고 23시간 후 만료로 취급
        self._token_expired_at = datetime.now() + timedelta(hours=23)
        return access_token

    def _headers(self, tr_id: str) -> Dict[str, str]:
        """KIS REST 호출용 공통 헤더 생성."""
        return {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self._get_access_token()}",
            "appkey": self.config.app_key,
            "appsecret": self.config.app_secret,
            "tr_id": tr_id,
        }

    # ------------------------------------------------------------------ #
    # 주문 관련
    # ------------------------------------------------------------------ #
    def place_cash_order(
        self,
        side: str,
        stock_code: str,
        quantity: int,
        price: int = 0,
        ord_dvsn: str = "01",
        tr_id_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        현금 주문 (매수/매도) 공통 함수.

        Args:
            side: "BUY" 또는 "SELL"
            stock_code: 6자리 종목코드 (예: "005930")
            quantity: 주문 수량
            price: 주문 단가 (시장가의 경우 0)
            ord_dvsn: 주문 구분 (예: "01" 지정가, "03" 시장가 등 - KIS 문서 참조)
            tr_id_override: 특정 TR ID 를 강제로 지정하고 싶을 때 사용

        Returns:
            KIS API 응답 JSON(dict)
        """
        if side not in {"BUY", "SELL"}:
            raise ValueError("side 는 'BUY' 또는 'SELL' 이어야 합니다.")
        if quantity <= 0:
            raise ValueError("quantity 는 1 이상이어야 합니다.")

        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"

        if tr_id_override:
            tr_id = tr_id_override
        else:
            if side == "BUY":
                tr_id = self.config.tr_id_order_cash_buy
            else:
                tr_id = self.config.tr_id_order_cash_sell

        if not tr_id:
            raise ValueError(
                "주문 TR ID 가 설정되지 않았습니다. "
                "KIS_TR_ID_ORDER_CASH_BUY / KIS_TR_ID_ORDER_CASH_SELL 환경변수를 확인하세요."
            )

        headers = self._headers(tr_id)

        body = {
            # 계좌 정보
            "CANO": self.config.account_no,
            "ACNT_PRDT_CD": self.config.account_code,
            # 종목/수량
            "PDNO": stock_code,
            "ORD_DVSN": ord_dvsn,          # 지정가/시장가 등
            "ORD_QTY": str(quantity),
            "ORD_UNPR": str(price),        # 시장가 주문 시 "0"
        }

        resp = requests.post(url, headers=headers, data=json.dumps(body))
        try:
            js = resp.json()
        except Exception:
            js = {"raw": resp.text}

        if resp.status_code != 200 or js.get("rt_cd") not in (None, "0"):
            # KIS 표준 응답 형식을 그대로 노출해서 디버깅하기 쉽게 둔다.
            raise RuntimeError(f"KIS 주문 실패: status={resp.status_code}, body={js}")

        return js

    def buy_market(
        self,
        stock_code: str,
        quantity: int,
        tr_id_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        시장가 매수 주문 (ORD_DVSN='03', ORD_UNPR=0).
        """
        return self.place_cash_order(
            side="BUY",
            stock_code=stock_code,
            quantity=quantity,
            price=0,
            ord_dvsn="03",
            tr_id_override=tr_id_override,
        )

    def sell_market(
        self,
        stock_code: str,
        quantity: int,
        tr_id_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        시장가 매도 주문 (ORD_DVSN='03', ORD_UNPR=0).
        """
        return self.place_cash_order(
            side="SELL",
            stock_code=stock_code,
            quantity=quantity,
            price=0,
            ord_dvsn="03",
            tr_id_override=tr_id_override,
        )

    # ------------------------------------------------------------------ #
    # 잔고 조회
    # ------------------------------------------------------------------ #
    def get_balance(self, tr_id_override: Optional[str] = None) -> Dict[str, Any]:
        """
        계좌 잔고/보유 주식 조회.

        실제 TR ID / 파라미터는 KIS OpenAPI 문서를 참조해 조정해야 한다.
        여기서는 핵심 구조만 제공한다.
        """
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-balance"

        if tr_id_override:
            tr_id = tr_id_override
        else:
            tr_id = self.config.tr_id_inquire_balance

        if not tr_id:
            raise ValueError(
                "잔고 조회 TR ID 가 설정되지 않았습니다. "
                "KIS_TR_ID_INQUIRE_BALANCE 환경변수를 확인하세요."
            )

        headers = self._headers(tr_id)

        params = {
            "CANO": self.config.account_no,
            "ACNT_PRDT_CD": self.config.account_code,
            # 나머지 파라미터는 KIS 문서에 맞게 필요시 추가 (예: AFHR_FLPR_YN, OFL_YN 등)
        }

        resp = requests.get(url, headers=headers, params=params)
        try:
            js = resp.json()
        except Exception:
            js = {"raw": resp.text}

        if resp.status_code != 200 or js.get("rt_cd") not in (None, "0"):
            raise RuntimeError(f"KIS 잔고 조회 실패: status={resp.status_code}, body={js}")

        return js


def _demo():
    """
    간단 테스트용 진입점.

    실제 실행 전:
      - .env 에 KIS_* 환경변수 설정
      - 모의계좌 TR ID 값들을 KIS 문서 보고 세팅

    예)
      KIS_APP_KEY=...
      KIS_APP_SECRET=...
      KIS_ACCOUNT_NO=12345678
      KIS_ACCOUNT_CODE=01
      KIS_REAL_MODE=False
      KIS_TR_ID_ORDER_CASH_BUY=...
      KIS_TR_ID_ORDER_CASH_SELL=...
      KIS_TR_ID_INQUIRE_BALANCE=...
    """
    cfg = KISConfig.from_env()
    broker = KISBroker(cfg)

    print("토큰 테스트용 잔고 조회 시도...")
    try:
        bal = broker.get_balance()
        print("잔고 응답:", json.dumps(bal, ensure_ascii=False, indent=2))
    except Exception as e:
        print("잔고 조회 실패:", e)


if __name__ == "__main__":
    _demo()



