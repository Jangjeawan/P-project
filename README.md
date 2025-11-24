# 국내 주식 AI 트레이딩 시스템

삼성전자, 네이버, 현대차의 5분봉 데이터를 활용한 딥러닝 기반 주가 예측 시스템

![Python](https://img.shields.io/badge/Python-3.10-blue)
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.20-orange)
![License](https://img.shields.io/badge/License-MIT-green)

## 📋 프로젝트 개요

한국투자증권 KIS API를 활용하여 국내 주요 주식의 5분봉 데이터를 수집하고, LSTM 딥러닝 모델로 주가를 예측하는 시스템입니다.

### 주요 기능
- 📊 한국투자증권 KIS API를 통한 실시간 데이터 수집
- 🔧 37개 기술적 지표 자동 생성 (MA, RSI, MACD, Bollinger Bands 등)
- 🤖 LSTM 딥러닝 모델 기반 주가 예측
- 📈 시각화 및 백테스팅 지원

## 🎯 대상 종목

- **삼성전자** (005930)
- **네이버** (035420)
- **현대차** (005380)

## 📊 모델 성능

| 종목 | RMSE (실제) | MAE (실제) | R² Score | MAPE |
|------|-------------|------------|----------|------|
| **삼성전자** | 약 3,500원 | 약 2,800원 | 0.75+ | ~1.5% |
| **네이버** | 약 5,200원 | 약 4,800원 | 0.50+ | ~1.8% |
| **현대차** | 약 4,200원 | 약 3,600원 | 0.68+ | ~1.6% |

## 🚀 시작하기

### 1. 환경 설정

```bash
# 저장소 클론
git clone https://github.com/Jangjeawan/P-project.git
cd P-project

# 필요한 패키지 설치
pip install -r requirements.txt
pip install -r requirements_ml.txt
```

### 2. API 키 설정

1. [한국투자증권 Open API](https://apiportal.koreainvestment.com) 접속
2. 회원가입 후 **모의투자** API 신청
3. App Key와 App Secret 발급
4. `.env` 파일 생성:

```bash
KIS_APP_KEY=your_app_key_here
KIS_APP_SECRET=your_app_secret_here
KIS_ACCOUNT_NO=your_account_number
KIS_ACCOUNT_CODE=01
KIS_REAL_MODE=False
```

### 3. 실행

```bash
# 1단계: 데이터 수집
python collect_data.py

# 2단계: 데이터 전처리
python preprocess_data.py

# 3단계: 모델 학습
python train_lstm.py
```

## 📁 프로젝트 구조

```
stuckAI/
├── collect_data.py           # 데이터 수집 메인
├── preprocess_data.py        # 전처리 메인
├── train_lstm.py             # 학습 메인
├── kis_api.py                # KIS API 클라이언트
├── data_collector.py         # 데이터 수집 모듈
├── data_preprocessor.py      # 전처리 모듈
├── technical_indicators.py   # 기술적 지표 계산
├── sequence_generator.py     # 시퀀스 데이터 생성
├── lstm_model.py             # LSTM 모델
├── model_evaluator.py        # 평가 및 시각화
├── prediction_inverter.py    # 역정규화 유틸리티
├── config.yaml               # 설정 파일
├── requirements.txt          # 기본 패키지
├── requirements_ml.txt       # ML 패키지
├── data/                     # 데이터 디렉토리
│   ├── raw/                  # 원본 일봉
│   ├── processed/            # 5분봉 데이터
│   └── preprocessed/         # 전처리 완료 데이터
├── models/                   # 학습된 모델
│   └── checkpoints/          # 체크포인트
└── results/                  # 평가 결과 및 그래프
    ├── 삼성전자/
    ├── 네이버/
    └── 현대차/
```

## 🔧 기술 스택

### 데이터 수집 및 전처리
- **Pandas** 2.1.4 - 데이터 처리
- **NumPy** 1.26.2 - 수치 연산
- **Requests** 2.31.0 - API 통신

### 머신러닝
- **TensorFlow** 2.20.0 - 딥러닝 프레임워크
- **Keras** 3.12.0 - 모델 구축
- **scikit-learn** 1.7.1 - 전처리 및 평가

### 시각화
- **Matplotlib** 3.10.5 - 그래프
- **Seaborn** 0.13.2 - 통계 시각화

## 📈 생성되는 기술적 지표 (37개)

### 이동평균 (6개)
- MA_5, MA_10, MA_20, MA_60
- EMA_12, EMA_26

### 모멘텀 지표 (3개)
- RSI (14일)
- Stochastic K, D

### 추세 지표 (3개)
- MACD, MACD_Signal, MACD_Histogram

### 변동성 지표 (6개)
- Bollinger Bands (Upper, Middle, Lower)
- BB_Width, BB_PctB
- ATR (14일)

### 거래량 지표 (4개)
- Volume_MA_5, Volume_MA_20
- Volume_Ratio
- OBV (On-Balance Volume)

### 수익률 지표 (7개)
- Return, Log_Return
- Return_5d, Return_10d, Return_20d
- HL_Ratio, CO_Ratio

## 🤖 LSTM 모델 아키텍처

```
Model: "Stock_LSTM"
┌─────────────────────────┬────────────────┬─────────────┐
│ Layer (type)            │ Output Shape   │ Param #     │
├─────────────────────────┼────────────────┼─────────────┤
│ LSTM_1 (LSTM)           │ (None, 60, 128)│ 83,456      │
│ Dropout_1 (Dropout)     │ (None, 60, 128)│ 0           │
│ LSTM_2 (LSTM)           │ (None, 60, 64) │ 49,408      │
│ Dropout_2 (Dropout)     │ (None, 60, 64) │ 0           │
│ LSTM_3 (LSTM)           │ (None, 32)     │ 12,416      │
│ Dropout_3 (Dropout)     │ (None, 32)     │ 0           │
│ Dense_1 (Dense)         │ (None, 32)     │ 1,056       │
│ Dropout_Dense (Dropout) │ (None, 32)     │ 0           │
│ Dense_2 (Dense)         │ (None, 16)     │ 528         │
│ Output (Dense)          │ (None, 1)      │ 17          │
└─────────────────────────┴────────────────┴─────────────┘
Total params: 146,881 (573.75 KB)
```

### 하이퍼파라미터
- **시퀀스 길이**: 60 (5분봉 기준 5시간)
- **LSTM Units**: [128, 64, 32]
- **Dropout**: 0.2
- **Learning Rate**: 0.001
- **Batch Size**: 32
- **Optimizer**: Adam
- **Loss**: MSE (Mean Squared Error)

## 📊 결과 확인

학습 완료 후 `results/` 폴더에서 다음을 확인할 수 있습니다:

- **학습 곡선**: 손실 및 MAE 추이
- **예측 결과**: 실제 vs 예측 비교
- **오차 분포**: 예측 오차의 분포
- **평가 메트릭**: CSV 형식의 상세 지표

## ⚠️ 주의사항

1. **API 사용 제한**
   - 초당 20회 호출 제한
   - 일일 호출 한도 확인 필요

2. **데이터 품질**
   - 주말/공휴일 데이터 없음
   - 장중 시간(09:00~15:30)만 수집

3. **투자 결정**
   - ⚠️ **본 시스템은 교육 및 연구 목적으로만 사용**
   - 실제 투자 결정에 사용 시 발생하는 손실에 대해 책임지지 않음

4. **데이터 누수 방지**
   - Train 데이터로만 스케일러 학습
   - Test 데이터는 transform만 적용

## 🔍 주요 개선 사항

### ✅ 전처리 개선
- **데이터 누수 방지**: Train 세트로만 scaler.fit()
- **inverse_transform**: 실제 가격으로 평가
- **정규화**: MinMaxScaler (0-1 범위)

### ✅ 모델 개선
- **Early Stopping**: 과적합 방지
- **Learning Rate Scheduling**: 학습률 자동 조정
- **Dropout**: 0.2로 일반화 성능 향상

## 📚 참고 자료

- [한국투자증권 Open API 문서](https://apiportal.koreainvestment.com)
- [TensorFlow 공식 문서](https://www.tensorflow.org)
- [LSTM 설명](https://colah.github.io/posts/2015-08-Understanding-LSTMs/)

## 📝 라이선스

MIT License

## 👨‍💻 개발자

[Jangjeawan](https://github.com/Jangjeawan)

## 🤝 기여

이슈 및 풀 리퀘스트 환영합니다!

## 📧 문의

프로젝트 관련 문의사항은 Issues를 통해 남겨주세요.

---

⭐ 이 프로젝트가 도움이 되었다면 Star를 눌러주세요!
