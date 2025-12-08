"""
일봉 데이터 + 단순 이동평균(MA20/MA60) 기반 전략 백테스트.

전략 (롱 전용):
  - MA20이 MA60을 상향돌파(골든크로스)하면 다음날부터 1배 롱 진입
  - MA20이 MA60을 하향돌파(데드크로스)하면 다음날 전량 청산
  - 포지션 보유 중에는 다음날 수익률만큼 계좌 가치 반영
"""

from typing import Dict

import pandas as pd
from sqlalchemy import text

from db_utils import get_engine, load_config_stocks


def load_daily_prices(engine, stock_code: str) -> pd.DataFrame:
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


def backtest_ma_strategy(
    engine,
    stock_code: str,
    stock_name: str,
    short_window: int = 20,
    long_window: int = 60,
) -> Dict:
    print(f"\n{'='*60}")
    print(f"{stock_name} ({stock_code}) - MA{short_window}/MA{long_window} 백테스트")
    print(f"{'='*60}")

    df = load_daily_prices(engine, stock_code)
    if df.empty:
        print("  데이터 없음")
        return {}

    df["ma_short"] = df["close"].rolling(short_window).mean()
    df["ma_long"] = df["close"].rolling(long_window).mean()
    df.dropna(inplace=True)
    df.reset_index(drop=True, inplace=True)

    equity = 1.0
    in_position = False
    equity_curve = []
    trades = 0

    # 하루씩 순회, 내일 수익률 적용
    for i in range(len(df) - 1):
        today = df.iloc[i]
        tomorrow = df.iloc[i + 1]

        # 교차 신호는 오늘 종가 기준 MA로 판단, 진입/청산은 내일부터 반영
        if not in_position:
            # 골든크로스: 오늘 short>long 이고 어제는 아니었던 경우
            if i > 0:
                yest = df.iloc[i - 1]
                if yest["ma_short"] <= yest["ma_long"] and today["ma_short"] > today["ma_long"]:
                    in_position = True
                    trades += 1
        else:
            # 데드크로스: 오늘 short<long 이고 어제는 아니었던 경우 → 청산
            if i > 0:
                yest = df.iloc[i - 1]
                if yest["ma_short"] >= yest["ma_long"] and today["ma_short"] < today["ma_long"]:
                    in_position = False

        # 포지션 보유 중이면 내일 수익률 적용
        daily_ret = (tomorrow["close"] - today["close"]) / today["close"]
        if in_position:
            equity *= (1.0 + daily_ret)

        equity_curve.append({"datetime": tomorrow["datetime"], "equity": equity, "in_position": int(in_position)})

    if not equity_curve:
        print("  유효 구간이 없어 결과 없음")
        return {}

    eq_df = pd.DataFrame(equity_curve)
    out_path = f"{stock_name}_daily_ma_backtest_equity.csv"
    eq_df.to_csv(out_path, index=False, encoding="utf-8-sig")

    total_return = equity - 1.0
    print("\n결과 요약:")
    print(f"  초기 자본: 1.0 (normalized)")
    print(f"  최종 자본: {equity:.4f}")
    print(f"  총 수익률: {total_return*100:.2f}%")
    print(f"  거래 횟수(진입 횟수): {trades}")

    return {
        "equity_final": equity,
        "total_return": total_return,
        "num_trades": trades,
        "equity_curve_path": out_path,
    }


def main():
    print(
        """
    ============================================================
      일봉 MA20/MA60 기반 롱 전용 백테스트
    ============================================================
    """
    )
    engine = get_engine()
    stocks = load_config_stocks()

    results = {}
    for s in stocks:
        code = s["code"]
        name = s["name"]
        res = backtest_ma_strategy(engine, code, name, short_window=20, long_window=60)
        results[name] = res

    print("\n전체 요약:")
    for name, r in results.items():
        if r:
            print(f"  {name}: 최종 {r['equity_final']:.4f} (수익률 {r['total_return']*100:.2f}%), 거래 {r['num_trades']}")
        else:
            print(f"  {name}: 실패")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


