"""
일봉 기준 상승/하락/유지 분류 LSTM 학습 스크립트.

입력:
  - data/daily_classification/<종목명>_train_daily_class.csv
  - 위 전처리 스크립트에서 생성됨 (정규화 + target 포함)
"""

import os
import sys

import numpy as np
import pandas as pd
from sklearn.utils import class_weight
from sklearn.metrics import classification_report, confusion_matrix

from sequence_generator import SequenceGenerator
from classification_model import StockLSTMClassifier


def load_daily_class_data(stock_name: str):
    base_dir = "data/daily_classification"
    train_path = os.path.join(base_dir, f"{stock_name}_train_daily_class.csv")
    val_path = os.path.join(base_dir, f"{stock_name}_val_daily_class.csv")
    test_path = os.path.join(base_dir, f"{stock_name}_test_daily_class.csv")

    train_df = pd.read_csv(train_path)
    val_df = pd.read_csv(val_path)
    test_df = pd.read_csv(test_path)

    # datetime 컬럼은 시퀀스에서 쓰일 수 있으니 일단 정렬만 보장
    for df in (train_df, val_df, test_df):
        if "datetime" in df.columns:
            df["datetime"] = pd.to_datetime(df["datetime"])
            df.sort_values("datetime", inplace=True)

    return train_df, val_df, test_df


def build_daily_sequences(
    stock_name: str,
    sequence_length: int = 60,
):
    print(f"\n{'='*60}")
    print(f"{stock_name} - 일봉 분류용 시퀀스 생성")
    print(f"{'='*60}")

    train_df, val_df, test_df = load_daily_class_data(stock_name)

    exclude_cols = ["datetime", "target"]
    feature_cols = [c for c in train_df.columns if c not in exclude_cols]

    X_train_raw = train_df[feature_cols].values
    X_val_raw = val_df[feature_cols].values
    X_test_raw = test_df[feature_cols].values

    y_train_raw = train_df["target"].values
    y_val_raw = val_df["target"].values
    y_test_raw = test_df["target"].values

    seq_gen = SequenceGenerator(sequence_length=sequence_length, prediction_horizon=1)

    X_train, y_train = seq_gen.create_sequences_with_labels(X_train_raw, y_train_raw)
    X_val, y_val = seq_gen.create_sequences_with_labels(X_val_raw, y_val_raw)
    X_test, y_test = seq_gen.create_sequences_with_labels(X_test_raw, y_test_raw)

    print("\n시퀀스 형태:")
    print(f"  학습: {X_train.shape}, 타겟: {y_train.shape}")
    print(f"  검증: {X_val.shape}, 타겟: {y_val.shape}")
    print(f"  테스트: {X_test.shape}, 타겟: {y_test.shape}")

    return (X_train, y_train), (X_val, y_val), (X_test, y_test), feature_cols


def train_daily_for_stock(
    stock_name: str,
    sequence_length: int = 60,
    lstm_units=None,
    dropout_rate: float = 0.2,
    learning_rate: float = 0.001,
    epochs: int = 40,
    batch_size: int = 32,
):
    if lstm_units is None:
        lstm_units = [128, 64, 32]

    (X_train, y_train), (X_val, y_val), (X_test, y_test), feature_cols = (
        build_daily_sequences(stock_name, sequence_length)
    )

    # 클래스 가중치
    classes = np.unique(y_train)
    cw = class_weight.compute_class_weight(
        class_weight="balanced", classes=classes, y=y_train
    )
    class_weights = {int(c): float(w) for c, w in zip(classes, cw)}

    # 모델 생성
    input_shape = (X_train.shape[1], X_train.shape[2])
    model = StockLSTMClassifier(
        input_shape=input_shape,
        num_classes=3,
        lstm_units=lstm_units,
        dropout_rate=dropout_rate,
        learning_rate=learning_rate,
    )

    history = model.train(
        X_train,
        y_train,
        X_val,
        y_val,
        model_name=f"{stock_name}_daily_cls",
        epochs=epochs,
        batch_size=batch_size,
        class_weights=class_weights,
        verbose=1,
    )

    # 저장
    save_path = os.path.join("models", f"{stock_name}_daily_lstm_cls.keras")
    model.save_model(save_path)

    # 평가
    print(f"\n{stock_name} - 검증 데이터 평가")
    val_results = model.evaluate(X_val, y_val)
    print(val_results)

    print(f"\n{stock_name} - 테스트 데이터 평가")
    test_results = model.evaluate(X_test, y_test)
    print(test_results)

    # 분류 리포트
    y_pred = model.predict_classes(X_test)
    print("\n분류 리포트 (테스트):")
    print(classification_report(y_test, y_pred, digits=4))
    print("혼동 행렬:")
    print(confusion_matrix(y_test, y_pred))

    return model, history, (X_test, y_test, y_pred)


def main():
    print(
        """
    ============================================================
      일봉 상승/하락/유지 분류 LSTM 학습
    ============================================================
    """
    )

    config = {
        "sequence_length": 60,
        "lstm_units": [128, 64, 32],
        "dropout_rate": 0.2,
        "learning_rate": 0.001,
        "epochs": 40,
        "batch_size": 32,
    }

    print("\n학습 설정:")
    for k, v in config.items():
        print(f"  {k}: {v}")

    stocks = ["삼성전자", "네이버", "현대차"]
    results = {}

    for name in stocks:
        try:
            model, history, pack = train_daily_for_stock(
                stock_name=name,
                sequence_length=config["sequence_length"],
                lstm_units=config["lstm_units"],
                dropout_rate=config["dropout_rate"],
                learning_rate=config["learning_rate"],
                epochs=config["epochs"],
                batch_size=config["batch_size"],
            )
            results[name] = {"success": True}
        except Exception as e:
            print(f"\n[ERROR] {name} 학습 실패: {e}")
            import traceback

            traceback.print_exc()
            results[name] = {"success": False, "error": str(e)}

    print(f"\n{'='*60}")
    print("일봉 분류 학습 요약")
    print(f"{'='*60}\n")
    for name, r in results.items():
        if r.get("success"):
            print(f"[OK] {name}")
        else:
            print(f"[FAIL] {name}: {r.get('error')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())







