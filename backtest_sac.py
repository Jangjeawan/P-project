"""
학습된 SAC 트레이딩 에이전트를 이용해
단일 종목 테스트 구간에서 백테스트를 수행하고,
에쿼티 곡선 / 포지션 / 기본 성과지표를 저장하는 스크립트.

예시:
    python backtest_sac.py --stock_name 삼성전자
"""

import argparse
import os
from typing import List, Dict, Any

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from stable_baselines3 import SAC

from train_sac import make_env


def run_episode(env, model) -> pd.DataFrame:
    """학습된 모델로 env 하나의 에피소드를 실행하고 결과를 DataFrame으로 반환."""
    obs, info = env.reset()
    done = False

    records: List[Dict[str, Any]] = []

    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated

        step_idx = getattr(env, "_current_step", None)

        records.append(
            {
                "step": int(step_idx) if step_idx is not None else len(records),
                "equity": float(info.get("equity", np.nan)),
                "position": float(info.get("position", np.nan)),
                "price_return": float(info.get("price_return", np.nan)),
                "step_return": float(info.get("step_return", np.nan)),
                "reward": float(reward),
                "action": float(action[0]),
            }
        )

    return pd.DataFrame(records)


def compute_metrics(df: pd.DataFrame, initial_equity: float) -> Dict[str, float]:
    """기본 성과지표 계산."""
    equity = df["equity"].values
    returns = np.diff(equity, prepend=initial_equity) / initial_equity

    total_return = equity[-1] / initial_equity - 1.0

    # 최대 낙폭 (MDD)
    running_max = np.maximum.accumulate(equity)
    drawdown = (equity - running_max) / running_max
    max_drawdown = drawdown.min()

    # 샤프 근사 (일간 수익률 기준, 무위험이자율 0 가정)
    if returns.std() > 0:
        sharpe = returns.mean() / returns.std() * np.sqrt(252)
    else:
        sharpe = 0.0

    return {
        "total_return": float(total_return),
        "max_drawdown": float(max_drawdown),
        "sharpe_approx": float(sharpe),
    }


def plot_equity(df: pd.DataFrame, out_path: str, title: str = ""):
    """에쿼티 곡선 저장."""
    x = df["datetime"] if "datetime" in df.columns else df["step"]
    equity = df["equity"]

    plt.figure(figsize=(12, 6))
    plt.plot(x, equity, label="SAC Equity")
    plt.xlabel("Date" if "datetime" in df.columns else "Step")
    plt.ylabel("Equity")
    plt.title(title or "SAC Backtest Equity Curve")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stock_name", type=str, default="삼성전자")
    parser.add_argument("--window_size", type=int, default=60)
    parser.add_argument("--model_path", type=str, default=None)
    args = parser.parse_args()

    # 경로 설정
    base_model_path = os.path.join("rl_models", f"sac_{args.stock_name}_final")
    model_path = args.model_path or base_model_path

    results_dir = os.path.join("results", args.stock_name)
    os.makedirs(results_dir, exist_ok=True)

    # 테스트 환경 생성 (preprocessed test CSV 사용)
    env = make_env(args.stock_name, split="test", window_size=args.window_size)

    # 테스트 CSV에서 datetime / close 로드 (있다면)
    test_csv_path = os.path.join("data", "preprocessed", f"{args.stock_name}_test.csv")
    date_series = None
    close_series = None
    if os.path.exists(test_csv_path):
        test_df = pd.read_csv(test_csv_path)
        if "datetime" in test_df.columns:
            date_series = pd.to_datetime(test_df["datetime"])
        if "close" in test_df.columns:
            close_series = test_df["close"]

    # 모델 로드
    model = SAC.load(model_path, env=env)

    # 에피소드 실행
    df = run_episode(env, model)

    # datetime / close 붙이기 (가능한 경우)
    if date_series is not None:
        idx = df["step"].clip(0, len(date_series) - 1).astype(int)
        df["datetime"] = date_series.iloc[idx].values
    if close_series is not None:
        idx = df["step"].clip(0, len(close_series) - 1).astype(int)
        df["close"] = close_series.iloc[idx].values

    # 메트릭 계산
    initial_equity = env.config.initial_cash
    metrics = compute_metrics(df, initial_equity)

    # CSV 저장
    csv_out = os.path.join(results_dir, f"{args.stock_name}_sac_backtest.csv")
    df.to_csv(csv_out, index=False, encoding="utf-8-sig")

    # 에쿼티 곡선 저장
    png_out = os.path.join(results_dir, f"{args.stock_name}_sac_equity.png")
    plot_equity(df, png_out, title=f"{args.stock_name} SAC Equity Curve")

    # 메트릭 출력
    print("\nSAC 백테스트 결과")
    print("-" * 40)
    print(f"CSV 저장:    {csv_out}")
    print(f"Equity PNG:  {png_out}")
    print(f"최종 수익률: {metrics['total_return'] * 100:.2f}%")
    print(f"최대 낙폭:   {metrics['max_drawdown'] * 100:.2f}%")
    print(f"샤프 근사:   {metrics['sharpe_approx']:.3f}")


if __name__ == "__main__":
    main()





