"""
일봉 LSTM 분류 모델을 이용한 간단한 일봉 백테스트.

전략 (롱/숏, 1배 비중):
  - 예측 UP(2): 다음날 종가까지 1배 롱 (수익률 = (C_{t+1}-C_t)/C_t)
  - 예측 DOWN(0): 다음날 종가까지 1배 숏 (수익률 = -(C_{t+1}-C_t)/C_t)
  - 예측 HOLD(1): 포지션 없음 (수익률 = 0)

계좌 가치는 초기 1.0에서 시작해 일별로 곱해 나감.
"""

from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd
from sqlalchemy import text
from tensorflow import keras

from db_utils import get_engine, load_config_stocks


def load_price_series(engine, stock_code: str) -> pd.DataFrame:
    query = text(
        """
        SELECT datetime, close
        FROM stock_prices
        WHERE stock_code = :code
        ORDER BY datetime ASC
        """
    )
    with engine.connect() as conn:
        df = pd.read_sql_query(query, conn, params={"code": stock_code})
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def backtest_single_stock(
    engine,
    stock_code: str,
    stock_name: str,
    sequence_length: int = 60,
) -> Dict:
    print(f"\n{'='*60}")
    print(f"{stock_name} ({stock_code}) - 일봉 백테스트")
    print(f"{'='*60}")

    base_dir = Path("data/daily_classification")
    test_path = base_dir / f"{stock_name}_test_daily_class.csv"
    if not test_path.exists():
        raise FileNotFoundError(f"테스트 데이터 없음: {test_path}")

    test_df = pd.read_csv(test_path)
    if "datetime" not in test_df.columns:
        raise ValueError("test CSV에 datetime 컬럼이 없습니다.")

    test_df["datetime"] = pd.to_datetime(test_df["datetime"])
    test_df = test_df.sort_values("datetime").reset_index(drop=True)

    # 피처/타겟 분리 (이미 정규화된 값)
    exclude_cols = ["datetime", "target"]
    feature_cols = [c for c in test_df.columns if c not in exclude_cols]
    data = test_df[feature_cols].values
    labels = test_df["target"].values.astype(int)
    dates = test_df["datetime"].values

    if len(data) <= sequence_length:
        raise ValueError("테스트 샘플이 시퀀스 길이보다 적습니다.")

    # 가격 시계열 로드 (실제 종가)
    price_df = load_price_series(engine, stock_code)
    price_map = {dt: close for dt, close in zip(price_df["datetime"].values, price_df["close"].values)}

    # 모델 로드
    model_path = Path("models") / f"{stock_name}_daily_lstm_cls.keras"
    if not model_path.exists():
        raise FileNotFoundError(f"모델 파일 없음: {model_path}")
    model = keras.models.load_model(model_path)

    equity = 1.0
    equity_curve = []

    n = len(data)
    num_seq = n - sequence_length  # 마지막 시퀀스의 끝이 n-1

    trades = 0
    for i in range(num_seq):
        X_seq = data[i : i + sequence_length]
        dt_end = dates[i + sequence_length - 1]

        # 다음날이 존재해야 함
        if i + sequence_length >= n:
            break
        dt_next = dates[i + sequence_length]

        close_t = price_map.get(dt_end)
        close_next = price_map.get(dt_next)
        if close_t is None or close_next is None:
            continue

        X_input = np.expand_dims(X_seq, axis=0)
        probs = model.predict(X_input, verbose=0)[0]
        p_down, p_hold, p_up = float(probs[0]), float(probs[1]), float(probs[2])

        # -------------------------------
        # 종목별 전략 파라미터
        # -------------------------------
        # 네이버(035420): 기존 전략 유지 (롱/숏 허용, 민감도 높게)
        # 삼성전자/현대차: 롱 전용, 더 보수적인 기준으로 진입
        if stock_code == "035420":
            # 네이버: 롱/숏 모두 허용, 비교적 민감하게
            margin = 0.01   # 1%p 차이로도 방향성 판단
            allow_short = True
        else:
            # 삼성전자 / 현대차: 롱 전용, 중간 정도의 민감도
            margin = 0.02   # 2%p 이상 차이 나야 방향성 있다고 판단
            allow_short = False

        diff_up = p_up - p_down
        diff_down = p_down - p_up

        if diff_up > margin:
            pred_cls = 2  # UP
        elif diff_down > margin:
            pred_cls = 0  # DOWN
        else:
            pred_cls = 1  # HOLD

        # 일일 수익률
        daily_ret = (close_next - close_t) / close_t
        strat_ret = 0.0
        if pred_cls == 2:  # UP → 롱
            strat_ret = daily_ret
            trades += 1
        elif pred_cls == 0 and allow_short:  # DOWN → 숏 (허용 종목만)
            strat_ret = -daily_ret
            trades += 1

        equity *= (1.0 + strat_ret)
        equity_curve.append({"datetime": dt_next, "equity": equity, "signal": pred_cls})

    if not equity_curve:
        print("유효한 시퀀스가 없어 백테스트 결과가 없습니다.")
        return {}

    eq_df = pd.DataFrame(equity_curve)
    eq_df.to_csv(f"{stock_name}_daily_backtest_equity.csv", index=False, encoding="utf-8-sig")

    total_return = equity - 1.0
    print("\n결과 요약:")
    print(f"  초기 자본: 1.0 (normalized)")
    print(f"  최종 자본: {equity:.4f}")
    print(f"  총 수익률: {total_return*100:.2f}%")
    print(f"  거래 횟수: {trades}")

    return {
        "equity_final": equity,
        "total_return": total_return,
        "num_trades": trades,
        "equity_curve_path": f"{stock_name}_daily_backtest_equity.csv",
    }


def main():
    print(
        """
    ============================================================
      일봉 분류 모델 기반 백테스트
    ============================================================
    """
    )
    engine = get_engine()
    stocks = load_config_stocks()

    results = {}
    for s in stocks:
        code = s["code"]
        name = s["name"]
        try:
            res = backtest_single_stock(engine, code, name, sequence_length=60)
            results[name] = res
        except Exception as e:
            print(f"\n[ERROR] {name} 백테스트 실패: {e}")
            results[name] = None

    print("\n전체 요약:")
    for name, r in results.items():
        if r:
            print(f"  {name}: 최종 {r['equity_final']:.4f} (수익률 {r['total_return']*100:.2f}%), 거래 {r['num_trades']}")
        else:
            print(f"  {name}: 실패")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


