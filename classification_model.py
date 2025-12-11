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
    """주식 가격 방향성 분류를 위한 LSTM 모델"""

    def __init__(
        self,
        input_shape: Tuple[int, int],
        num_classes: int = 3,
        lstm_units: Optional[List[int]] = None,
        dropout_rate: float = 0.2,
        learning_rate: float = 0.001,
    ):
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
        model = models.Sequential(name="Stock_LSTM_Classifier")
        model.add(layers.Input(shape=self.input_shape))

        # 첫 번째 LSTM
        model.add(
            layers.LSTM(
                units=self.lstm_units[0],
                return_sequences=len(self.lstm_units) > 1,
                name="LSTM_1",
            )
        )
        model.add(layers.Dropout(self.dropout_rate, name="Dropout_1"))

        # 추가 LSTM 레이어
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

        # Dense
        model.add(layers.Dense(32, activation="relu", name="Dense_1"))
        model.add(layers.Dropout(self.dropout_rate, name="Dropout_Dense"))

        # 출력 (softmax)
        model.add(layers.Dense(self.num_classes, activation="softmax", name="Output"))

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
        checkpoint_dir: str = "models/checkpoints_daily",
        patience: int = 15,
    ) -> List[callbacks.Callback]:
        os.makedirs(checkpoint_dir, exist_ok=True)

        cbs: List[callbacks.Callback] = [
            callbacks.ModelCheckpoint(
                filepath=f"{checkpoint_dir}/{model_name}_best.keras",
                monitor="val_loss",
                save_best_only=True,
                mode="min",
                verbose=1,
            ),
            callbacks.EarlyStopping(
                monitor="val_loss",
                patience=patience,
                restore_best_weights=True,
                verbose=1,
            ),
            callbacks.ReduceLROnPlateau(
                monitor="val_loss",
                factor=0.5,
                patience=7,
                min_lr=1e-6,
                verbose=1,
            ),
        ]
        return cbs

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
        if self.model is None:
            self.build_model()

        print(f"\n{'='*60}")
        print(f"모델 학습 시작: {model_name}")
        print(f"{'='*60}")
        print(f"입력 형태: {X_train.shape}, 클래스 수: {self.num_classes}")
        self.model.summary()

        cbs = self.get_callbacks(model_name)

        history = self.model.fit(
            X_train,
            y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=cbs,
            class_weight=class_weights,
            verbose=verbose,
        )

        self.history = history
        return history

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise ValueError("모델이 학습되지 않았습니다.")
        return self.model.predict(X)

    def predict_classes(self, X: np.ndarray) -> np.ndarray:
        probs = self.predict_proba(X)
        return np.argmax(probs, axis=1)

    def evaluate(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        if self.model is None:
            raise ValueError("모델이 학습되지 않았습니다.")

        loss, acc = self.model.evaluate(X, y, verbose=0)
        from sklearn.metrics import precision_recall_fscore_support

        y_pred = self.predict_classes(X)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y, y_pred, average="weighted", zero_division=0
        )

        return {
            "loss": loss,
            "accuracy": acc,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
        }

    def save_model(self, filepath: str):
        if self.model is None:
            raise ValueError("저장할 모델이 없습니다.")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        self.model.save(filepath)
        print(f"\n모델 저장: {filepath}")

    @classmethod
    def load_model(cls, filepath: str) -> "StockLSTMClassifier":
        model = keras.models.load_model(filepath)
        instance = cls(input_shape=model.input_shape[1:])
        instance.model = model
        return instance













