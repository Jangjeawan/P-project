# 국내 주식 AI 트레이딩 시스템 (일봉 기반)

삼성전자, 네이버, 현대차 **일봉 데이터**를 이용해
- 상승 / 하락 / 유지를 분류하는 LSTM 모델을 학습하고
- 결과를 바탕으로 일봉 백테스트와 단순 MA 전략을 실행하는 프로젝트입니다.

## 📋 개요

- **데이터 소스**: Yahoo Finance (`005930.KS`, `035420.KS`, `005380.KS`)
- **기간**: 최근 5년 일봉
- **모델**: LSTM 기반 3클래스 분류 (DOWN / HOLD / UP)
- **전략**
  - 네이버: LSTM 분류 결과 기반 롱/숏 전략
  - 삼성전자/현대차: LSTM 또는 MA20/MA60 롱 전용 전략
- **DB**: PostgreSQL (`stock_prices` 테이블)
- **가상계좌**: `virtual_account.py` (추후 KIS 모의계좌 연동 예정)

## 🚀 실행 순서

### 1. 의존성 설치

```bash
pip install -r requirements.txt
pip install -r requirements_ml.txt
```

### 2. 환경 변수 설정 (`.env`)

```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=stuckDB
DB_USER=postgres
DB_PASSWORD=your_password

# (선택) KIS 모의계좌 연동용
KIS_APP_KEY=...
KIS_APP_SECRET=...
KIS_ACCOUNT_NO=...
KIS_ACCOUNT_CODE=01
KIS_REAL_MODE=False
KIS_TR_ID_ORDER_CASH_BUY=...      # KIS 문서 참조
KIS_TR_ID_ORDER_CASH_SELL=...
KIS_TR_ID_INQUIRE_BALANCE=...
```

### 3. 데이터 수집 (Yahoo → PostgreSQL)

```bash
python collect_yahoo_data.py
```

### 4. 일봉 분류용 전처리

```bash
python daily_preprocess_classification.py
```

이 스크립트는 DB의 `stock_prices`에서 일봉을 읽어와:
- 기술적 지표 30여 개를 계산하고
- 다음날 수익률 기준으로 UP/HOLD/DOWN 라벨을 만들고
- 70/15/15 (train/val/test)로 나눈 뒤
- `data/daily_classification/`에 CSV + 스케일러(`*_daily_scaler.pkl`)를 저장합니다.

### 5. 일봉 LSTM 분류 모델 학습

```bash
python train_daily_classification.py
```

각 종목에 대해:
- `models/<종목>_daily_lstm_cls.keras` 모델 파일이 생성됩니다.

### 6. 백테스트

```bash
# LSTM 분류 기반 전략
python backtest_daily.py

# 단순 MA20/MA60 롱 전용 전략
python backtest_daily_ma.py
```

각 종목별로 `*_daily_backtest_equity.csv`, `*_daily_ma_backtest_equity.csv`가 생성되며,
- 날짜별 equity 곡선과 신호를 확인할 수 있습니다.

## 📁 주요 파일 구조

```text
stuckAI/
├─ config.yaml                      # 종목/데이터 경로 설정
├─ requirements.txt
├─ requirements_ml.txt
│
├─ db_utils.py                      # DB 연결, 종목 설정 로딩
├─ technical_indicators.py          # 각종 기술적 지표 계산
├─ sequence_generator.py            # 시퀀스 생성 유틸
│
├─ collect_yahoo_data.py            # Yahoo → PostgreSQL(stock_prices)
├─ reset_db_data.py                 # DB 초기화 보조 스크립트
│
├─ daily_preprocess_classification.py  # 일봉 분류용 전처리 (UP/HOLD/DOWN)
├─ train_daily_classification.py       # 일봉 LSTM 분류 모델 학습
├─ classification_model.py             # LSTM 분류 모델 정의
│
├─ backtest_daily.py                # LSTM 분류 기반 일봉 백테스트
├─ backtest_daily_ma.py             # MA20/60 롱 전용 일봉 백테스트
├─ virtual_account.py               # 가상 계좌 시뮬레이션
├─ kis_broker.py                    # KIS 주문/잔고 조회용 브로커 뼈대
│
├─ data/
│  ├─ raw/                          # 원본 일봉 CSV (옵션)
│  ├─ daily_classification/         # 일봉 분류 전처리 결과 + 스케일러
│  └─ preprocessed/                 # (과거 실험용) 회귀 전처리 결과
│
├─ models/
│  ├─ checkpoints_daily/            # 일봉 분류 모델 체크포인트
│  ├─ 네이버_daily_lstm_cls.keras
│  ├─ 삼성전자_daily_lstm_cls.keras
│  └─ 현대차_daily_lstm_cls.keras
│
└─ results/                         # 평가/백테스트 결과 (이미지, CSV 등)
```

## ⚠️ 주의사항

- 이 프로젝트는 **연구 및 학습 목적**으로만 사용해야 합니다.
- 실제 투자에 사용 시 발생하는 손실은 전적으로 사용자 책임입니다.







