"""
예측 결과 역정규화 유틸리티
"""
import numpy as np
import pandas as pd
import pickle
from pathlib import Path
from typing import Tuple


class PredictionInverter:
    """예측값을 원래 스케일로 변환"""
    
    def __init__(self, scaler_path: str):
        """
        Args:
            scaler_path: 스케일러 pickle 파일 경로
        """
        with open(scaler_path, 'rb') as f:
            self.scaler = pickle.load(f)
    
    def inverse_transform_predictions(
        self,
        predictions: np.ndarray,
        feature_idx: int = 3  # close price의 인덱스
    ) -> np.ndarray:
        """
        예측값을 원래 스케일로 역변환
        
        Args:
            predictions: 정규화된 예측값
            feature_idx: close price의 피처 인덱스
            
        Returns:
            역변환된 예측값
        """
        # 예측값이 1D인 경우 reshape
        if predictions.ndim == 1:
            predictions = predictions.reshape(-1, 1)
        
        # 스케일러의 특성 수만큼 더미 배열 생성
        n_features = len(self.scaler.scale_)
        dummy = np.zeros((predictions.shape[0], n_features))
        
        # close price 위치에 예측값 넣기
        dummy[:, feature_idx] = predictions.flatten()
        
        # inverse_transform
        inversed = self.scaler.inverse_transform(dummy)
        
        # close price만 추출
        return inversed[:, feature_idx]
    
    def inverse_transform_close_only(
        self,
        values: np.ndarray
    ) -> np.ndarray:
        """
        close price만 역변환 (간단 버전)
        
        Args:
            values: 정규화된 close price 값들
            
        Returns:
            역변환된 값들
        """
        # MinMaxScaler의 경우
        # value = (x - min) / (max - min)
        # x = value * (max - min) + min
        
        close_idx = 3  # close의 인덱스
        scale = self.scaler.scale_[close_idx]
        min_val = self.scaler.min_[close_idx]
        
        # 역변환
        return values * scale + min_val

