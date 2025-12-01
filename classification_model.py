"""
LSTM 기반 분류 모델 (상승 / 하락 / 유지)
"""
import os
from typing import Tuple, List, Dict, Optional

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, models, callbacks


class StockLSTMClassifier:
    """주식 방향성(UP/DOWN/HOLD) 분류를 위한 LSTM 모델"""

    def __init__(
        self,
        input_shape: Tuple[int, int],
        num_classes: int = 3,
        lstm_units: List[int] = None,
        dropout_rate: float = 0.2,
        learning_rate: float = 0.001,
    ):
        """
        Args:
            input_shape: (sequence_length, n_features)
            num_classes: 클래스 수 (기본 3: DOWN/HOLD/UP)
            lstm_units: 각 LSTM 레이어의 유닛 수 리스트
            dropout_rate: 드롭아웃 비율
            learning_rate: 학습률
        """
        if lstm_units is None:
            lstm_units = [128, 64, 32]

        self.input_shape = input_shape
        self.num_classes = num_classes
        self.lstm_units = lstm_units
        self.dropout_rate = dropout_rate
        self.learning_rate = learning_rate

        self.model: Optional[models.Model] = None
        self.history: Optional[keras.callbacks.History] = None

    def build_model(self) -> models.Model:
        """LSTM 분류 모델 구축"""
        model = models.Sequential(name="Stock_LSTM_Classifier")

        # 입력
        model.add(layers.Input(shape=self.input_shape))

        # 첫 번째 LSTM 레이어
        model.add(
            layers.LSTM(
                units=self.lstm_units[0],
                return_sequences=len(self.lstm_units) > 1,
                name="LSTM_1",
            )
        )
        model.add(layers.Dropout(self.dropout_rate, name="Dropout_1"))

        # 추가 LSTM 레이어들
        for i, units in enumerate(self.lstm_units[1:], start=2):
            return_seq = i < len(self.lstm_units)
            model.add(
                layers.LSTM(
                    units=units,
                    return_sequences=return_seq,
                    name=f"LSTM_{i}",
                )
            )
            model.add(layers.Dropout(self.dropout_rate, name=f"Dropout_{i}"))

        # Dense 레이어
        model.add(layers.Dense(32, activation="relu", name="Dense_1"))
        model.add(layers.Dropout(self.dropout_rate, name="Dropout_Dense"))

        # 출력 레이어 (분류용)
        model.add(
            layers.Dense(self.num_classes, activation="softmax", name="Output")
        )

        # 컴파일
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=self.learning_rate),
            loss="sparse_categorical_crossentropy",
            metrics=["accuracy"],
        )

        self.model = model
        return model

    def get_callbacks(
        self,
        model_name: str,
        checkpoint_dir: str = "models/checkpoints_cls",
        patience: int = 15,
    ) -> List[callbacks.Callback]:
        """학습 콜백 설정"""
        os.makedirs(checkpoint_dir, exist_ok=True)

        callback_list: List[callbacks.Callback] = [
            # 모델 체크포인트
            callbacks.ModelCheckpoint(
                filepath=f"{checkpoint_dir}/{model_name}_best.keras",
                monitor="val_loss",
                save_best_only=True,
                mode="min",
                verbose=1,
            ),
            # 조기 종료
            callbacks.EarlyStopping(
                monitor="val_loss",
                patience=patience,
                restore_best_weights=True,
                verbose=1,
            ),
            # 학습률 감소
            callbacks.ReduceLROnPlateau(
                monitor="val_loss",
                factor=0.5,
                patience=7,
                min_lr=1e-6,
                verbose=1,
            ),
        ]

        return callback_list

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        model_name: str,
        epochs: int = 50,
        batch_size: int = 32,
        class_weights: Optional[Dict[int, float]] = None,
        verbose: int = 1,
    ) -> keras.callbacks.History:
        """모델 학습"""
        if self.model is None:
            self.build_model()

        print(f"\n{'='*60}")
        print(f"분류 모델 학습 시작: {model_name}")
        print(f"{'='*60}")
        print(f"\n입력 형태: {X_train.shape}, 클래스 수: {self.num_classes}")

        self.model.summary()

        print("\n학습 설정:")
        print(f"  에포크: {epochs}")
        print(f"  배치 크기: {batch_size}")
        print(f"  학습률: {self.learning_rate}")
        print(f"  드롭아웃: {self.dropout_rate}")
        if class_weights is not None:
            print(f"  클래스 가중치: {class_weights}")

        cb_list = self.get_callbacks(model_name)

        history = self.model.fit(
            X_train,
            y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=cb_list,
            class_weight=class_weights,
            verbose=verbose,
        )

        self.history = history
        return history

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """클래스 확률 예측"""
        if self.model is None:
            raise ValueError("모델이 학습되지 않았습니다.")
        return self.model.predict(X)

    def predict_classes(self, X: np.ndarray) -> np.ndarray:
        """클래스 인덱스 예측"""
        proba = self.predict_proba(X)
        return np.argmax(proba, axis=1)

    def evaluate(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """정확도 및 손실 평가"""
        if self.model is None:
            raise ValueError("모델이 학습되지 않았습니다.")

        loss, acc = self.model.evaluate(X, y, verbose=0)

        # 추가 메트릭 (정밀도/재현율/F1)은 sklearn에서 계산
        y_pred = self.predict_classes(X)
        from sklearn.metrics import (
            precision_recall_fscore_support,
            accuracy_score,
        )

        precision, recall, f1, _ = precision_recall_fscore_support(
            y, y_pred, average="weighted", zero_division=0
        )

        results = {
            "loss": loss,
            "accuracy": acc,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
        }
        return results

    def save_model(self, filepath: str):
        """모델 저장"""
        if self.model is None:
            raise ValueError("저장할 모델이 없습니다.")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        self.model.save(filepath)
        print(f"\n모델 저장: {filepath}")

    @classmethod
    def load_model(cls, filepath: str) -> "StockLSTMClassifier":
        """저장된 모델에서 분류기 인스턴스 생성"""
        model = keras.models.load_model(filepath)
        instance = cls(input_shape=model.input_shape[1:])
        instance.model = model
        return instance



