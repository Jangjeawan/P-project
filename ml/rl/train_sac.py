"""
단일 종목용 SAC 강화학습 트레이딩 학습 스크립트.

예시 실행:
    python train_sac.py --stock_name 삼성전자 --timesteps 200_000
"""

import argparse
import os

import gymnasium as gym
from stable_baselines3 import SAC
from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback
from stable_baselines3.common.vec_env import DummyVecEnv

from rl_trading_env import SingleStockTradingEnv, TradingEnvConfig


def make_env(stock_name: str, split: str = "train", window_size: int = 60) -> gym.Env:
    """
    전처리된 CSV를 기반으로 단일 종목 환경 생성.

    기존 LSTM 학습 스크립트와 동일하게:
        data/preprocessed/<종목>_train.csv
    를 기본으로 사용.
    """
    data_dir = "data/preprocessed"
    csv_path = os.path.join(data_dir, f"{stock_name}_{split}.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    cfg = TradingEnvConfig(
        csv_path=csv_path,
        window_size=window_size,
        initial_cash=1_000_000.0,
        max_position=1.0,
        transaction_cost=0.0005,
        reward_scale=1.0,
    )
    return SingleStockTradingEnv(cfg)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stock_name", type=str, default="삼성전자")
    parser.add_argument("--timesteps", type=int, default=200_000)
    parser.add_argument("--window_size", type=int, default=60)
    parser.add_argument("--log_dir", type=str, default="rl_logs_sac")
    parser.add_argument("--model_dir", type=str, default="rl_models")
    args = parser.parse_args()

    os.makedirs(args.log_dir, exist_ok=True)
    os.makedirs(args.model_dir, exist_ok=True)

    # 학습/평가 환경
    def _train_env_fn():
        return make_env(args.stock_name, split="train", window_size=args.window_size)

    def _eval_env_fn():
        return make_env(args.stock_name, split="val", window_size=args.window_size)

    train_env = DummyVecEnv([_train_env_fn])
    eval_env = DummyVecEnv([_eval_env_fn])

    model = SAC(
        "MlpPolicy",
        train_env,
        verbose=1,
        tensorboard_log=None,  # TensorBoard 로깅 비활성화 (경로 문제 회피)
        gamma=0.99,
        learning_rate=3e-4,
        batch_size=128,
        train_freq=1,
        gradient_steps=1,
        buffer_size=100_000,  # 메모리 사용량 줄이기
        ent_coef="auto",
    )

    # 콜백: 주기적으로 평가 + 체크포인트 저장
    best_dir = os.path.join(args.model_dir, f"sac_{args.stock_name}_best")
    os.makedirs(best_dir, exist_ok=True)

    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=best_dir,  # 종목별 best 모델 디렉토리
        log_path=args.log_dir,
        eval_freq=5_000,
        deterministic=True,
        render=False,
    )
    checkpoint_callback = CheckpointCallback(
        save_freq=20_000,
        save_path=args.model_dir,
        name_prefix=f"sac_{args.stock_name}",
    )

    model.learn(
        total_timesteps=args.timesteps,
        callback=[eval_callback, checkpoint_callback],
    )

    final_path = os.path.join(args.model_dir, f"sac_{args.stock_name}_final")
    model.save(final_path)
    print(f"SAC 모델 저장 완료: {final_path}")


if __name__ == "__main__":
    main()


