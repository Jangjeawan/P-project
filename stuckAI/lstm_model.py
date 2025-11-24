"""
LSTM 모델 아키텍처
"""
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, models, callbacks
from typing import Tuple, List
import numpy as np
import os


class StockLSTMModel:
    """주식 가격 예측을 위한 LSTM 모델"""
    
    def __init__(
        self,
        input_shape: Tuple[int, int],
        lstm_units: List[int] = [128, 64, 32],
        dropout_rate: float = 0.2,
        learning_rate: float = 0.001
    ):
        """
        Args:
            input_shape: (sequence_length, n_features)
            lstm_units: 각 LSTM 레이어의 유닛 수
            dropout_rate: 드롭아웃 비율
            learning_rate: 학습률
        """
        self.input_shape = input_shape
        self.lstm_units = lstm_units
        self.dropout_rate = dropout_rate
        self.learning_rate = learning_rate
        self.model = None
        self.history = None
        
    def build_model(self) -> models.Model:
        """LSTM 모델 구축"""
        model = models.Sequential(name='Stock_LSTM')
        
        # 첫 번째 LSTM 레이어
        model.add(layers.Input(shape=self.input_shape))
        model.add(layers.LSTM(
            units=self.lstm_units[0],
            return_sequences=True if len(self.lstm_units) > 1 else False,
            name='LSTM_1'
        ))
        model.add(layers.Dropout(self.dropout_rate, name='Dropout_1'))
        
        # 추가 LSTM 레이어들
        for i, units in enumerate(self.lstm_units[1:], start=2):
            return_seq = i < len(self.lstm_units)
            model.add(layers.LSTM(
                units=units,
                return_sequences=return_seq,
                name=f'LSTM_{i}'
            ))
            model.add(layers.Dropout(self.dropout_rate, name=f'Dropout_{i}'))
        
        # Dense 레이어
        model.add(layers.Dense(32, activation='relu', name='Dense_1'))
        model.add(layers.Dropout(self.dropout_rate, name='Dropout_Dense'))
        model.add(layers.Dense(16, activation='relu', name='Dense_2'))
        
        # 출력 레이어 (회귀)
        model.add(layers.Dense(1, name='Output'))
        
        # 모델 컴파일
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=self.learning_rate),
            loss='mean_squared_error',
            metrics=['mae', 'mse']
        )
        
        self.model = model
        return model
    
    def get_callbacks(
        self,
        model_name: str,
        checkpoint_dir: str = 'models/checkpoints',
        patience: int = 20
    ) -> List[callbacks.Callback]:
        """학습 콜백 설정"""
        os.makedirs(checkpoint_dir, exist_ok=True)
        
        callback_list = [
            # 모델 체크포인트
            callbacks.ModelCheckpoint(
                filepath=f'{checkpoint_dir}/{model_name}_best.keras',
                monitor='val_loss',
                save_best_only=True,
                mode='min',
                verbose=1
            ),
            
            # 조기 종료
            callbacks.EarlyStopping(
                monitor='val_loss',
                patience=patience,
                restore_best_weights=True,
                verbose=1
            ),
            
            # 학습률 감소
            callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=10,
                min_lr=1e-7,
                verbose=1
            )
        ]
        
        return callback_list
    
    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        model_name: str,
        epochs: int = 100,
        batch_size: int = 32,
        verbose: int = 1
    ) -> keras.callbacks.History:
        """모델 학습"""
        if self.model is None:
            self.build_model()
        
        print(f"\n{'='*60}")
        print(f"모델 학습 시작: {model_name}")
        print(f"{'='*60}")
        print(f"\n모델 구조:")
        self.model.summary()
        
        print(f"\n학습 설정:")
        print(f"  에포크: {epochs}")
        print(f"  배치 크기: {batch_size}")
        print(f"  학습률: {self.learning_rate}")
        print(f"  드롭아웃: {self.dropout_rate}")
        
        # 콜백 설정
        callback_list = self.get_callbacks(model_name)
        
        # 학습
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callback_list,
            verbose=verbose
        )
        
        self.history = history
        return history
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """예측"""
        if self.model is None:
            raise ValueError("모델이 학습되지 않았습니다.")
        
        return self.model.predict(X)
    
    def evaluate(self, X: np.ndarray, y: np.ndarray, scaler=None, close_idx: int = 3) -> dict:
        """
        모델 평가 (inverse_transform 지원)
        
        Args:
            X: 입력 데이터
            y: 실제 타겟 (정규화된 값)
            scaler: 스케일러 객체 (inverse_transform용)
            close_idx: close price의 인덱스
        """
        if self.model is None:
            raise ValueError("모델이 학습되지 않았습니다.")
        
        # 정규화된 값으로 평가
        loss, mae, mse = self.model.evaluate(X, y, verbose=0)
        rmse = np.sqrt(mse)
        
        # 예측값
        y_pred = self.predict(X).flatten()
        
        # R² 스코어 (정규화된 값)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2_score = 1 - (ss_res / ss_tot)
        
        # MAPE (정규화된 값, 0으로 나누기 방지)
        mask = y != 0
        mape = np.mean(np.abs((y[mask] - y_pred[mask]) / y[mask])) * 100 if mask.any() else 0
        
        results = {
            'loss': loss,
            'mae': mae,
            'mse': mse,
            'rmse': rmse,
            'r2_score': r2_score,
            'mape': mape
        }
        
        # ✅ inverse_transform 적용한 실제 값으로도 평가
        if scaler is not None:
            y_true_real = self._inverse_transform_target(y, scaler, close_idx)
            y_pred_real = self._inverse_transform_target(y_pred, scaler, close_idx)
            
            # 실제 스케일에서의 메트릭
            mae_real = np.mean(np.abs(y_true_real - y_pred_real))
            mse_real = np.mean((y_true_real - y_pred_real) ** 2)
            rmse_real = np.sqrt(mse_real)
            
            ss_res_real = np.sum((y_true_real - y_pred_real) ** 2)
            ss_tot_real = np.sum((y_true_real - np.mean(y_true_real)) ** 2)
            r2_real = 1 - (ss_res_real / ss_tot_real)
            
            mask_real = y_true_real != 0
            mape_real = np.mean(np.abs((y_true_real[mask_real] - y_pred_real[mask_real]) / y_true_real[mask_real])) * 100
            
            results.update({
                'mae_real': mae_real,
                'rmse_real': rmse_real,
                'r2_real': r2_real,
                'mape_real': mape_real
            })
        
        return results
    
    def _inverse_transform_target(self, values: np.ndarray, scaler, close_idx: int) -> np.ndarray:
        """타겟 값을 원래 스케일로 역변환"""
        values = values.flatten()
        n_features = len(scaler.scale_)
        dummy = np.zeros((len(values), n_features))
        dummy[:, close_idx] = values
        inversed = scaler.inverse_transform(dummy)
        return inversed[:, close_idx]
    
    def save_model(self, filepath: str):
        """모델 저장"""
        if self.model is None:
            raise ValueError("저장할 모델이 없습니다.")
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        self.model.save(filepath)
        print(f"\n모델 저장: {filepath}")
    
    @classmethod
    def load_model(cls, filepath: str) -> 'StockLSTMModel':
        """모델 로드"""
        model = keras.models.load_model(filepath)
        
        # 인스턴스 생성
        instance = cls(input_shape=model.input_shape[1:])
        instance.model = model
        
        return instance


