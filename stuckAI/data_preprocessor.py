"""
데이터 전처리 모듈
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, List
from sklearn.preprocessing import MinMaxScaler, StandardScaler
import pickle
from technical_indicators import TechnicalIndicators


class DataPreprocessor:
    """주식 데이터 전처리"""
    
    def __init__(self, data_dir: str = "data/processed"):
        """
        Args:
            data_dir: 데이터 디렉토리 경로
        """
        self.data_dir = Path(data_dir)
        self.scaler = None
        self.feature_columns = None
        
    def load_data(self, filename: str) -> pd.DataFrame:
        """
        데이터 로드
        
        Args:
            filename: 파일명
            
        Returns:
            DataFrame
        """
        filepath = self.data_dir / filename
        df = pd.read_csv(filepath)
        df['datetime'] = pd.to_datetime(df['datetime'])
        return df
    
    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        기술적 지표 추가
        
        Args:
            df: 원본 데이터
            
        Returns:
            지표가 추가된 데이터
        """
        return TechnicalIndicators.add_all_indicators(df)
    
    def remove_nan(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        NaN 값 제거
        
        Args:
            df: DataFrame
            
        Returns:
            NaN이 제거된 DataFrame
        """
        initial_len = len(df)
        df = df.dropna()
        removed = initial_len - len(df)
        
        if removed > 0:
            print(f"  NaN 제거: {removed}개 행 삭제")
        
        return df.reset_index(drop=True)
    
    def normalize_data(
        self,
        df: pd.DataFrame,
        method: str = 'minmax',
        exclude_columns: List[str] = None
    ) -> Tuple[pd.DataFrame, object]:
        """
        데이터 정규화
        
        Args:
            df: DataFrame
            method: 정규화 방법 ('minmax' 또는 'standard')
            exclude_columns: 정규화에서 제외할 컬럼
            
        Returns:
            정규화된 DataFrame, 스케일러
        """
        df = df.copy()
        
        if exclude_columns is None:
            exclude_columns = ['datetime', 'stock_code', 'stock_name']
        
        # 정규화할 컬럼 선택
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        columns_to_scale = [col for col in numeric_columns if col not in exclude_columns]
        
        # 스케일러 선택
        if method == 'minmax':
            scaler = MinMaxScaler(feature_range=(0, 1))
        else:
            scaler = StandardScaler()
        
        # 정규화
        df[columns_to_scale] = scaler.fit_transform(df[columns_to_scale])
        
        print(f"  {method} 정규화 완료: {len(columns_to_scale)}개 특성")
        
        return df, scaler
    
    def split_data(
        self,
        df: pd.DataFrame,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        데이터를 학습/검증/테스트 세트로 분리
        
        Args:
            df: DataFrame
            train_ratio: 학습 데이터 비율
            val_ratio: 검증 데이터 비율
            test_ratio: 테스트 데이터 비율
            
        Returns:
            train_df, val_df, test_df
        """
        assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 0.01, \
            "비율의 합이 1이어야 합니다"
        
        n = len(df)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))
        
        train_df = df.iloc[:train_end].copy()
        val_df = df.iloc[train_end:val_end].copy()
        test_df = df.iloc[val_end:].copy()
        
        print(f"\n  데이터 분리:")
        print(f"    학습: {len(train_df):,}개 ({train_ratio*100:.1f}%)")
        print(f"    검증: {len(val_df):,}개 ({val_ratio*100:.1f}%)")
        print(f"    테스트: {len(test_df):,}개 ({test_ratio*100:.1f}%)")
        
        return train_df, val_df, test_df
    
    def create_sequences(
        self,
        data: np.ndarray,
        sequence_length: int = 60,
        prediction_horizon: int = 1
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        시계열 시퀀스 생성
        
        Args:
            data: 입력 데이터
            sequence_length: 시퀀스 길이 (과거 몇 개 데이터를 볼 것인가)
            prediction_horizon: 예측 기간 (몇 스텝 앞을 예측할 것인가)
            
        Returns:
            X (입력 시퀀스), y (타겟)
        """
        X, y = [], []
        
        for i in range(len(data) - sequence_length - prediction_horizon + 1):
            X.append(data[i:(i + sequence_length)])
            y.append(data[i + sequence_length + prediction_horizon - 1])
        
        return np.array(X), np.array(y)
    
    def save_preprocessed_data(
        self,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        test_df: pd.DataFrame,
        stock_name: str,
        output_dir: str = "data/preprocessed"
    ):
        """
        전처리된 데이터 저장
        
        Args:
            train_df: 학습 데이터
            val_df: 검증 데이터
            test_df: 테스트 데이터
            stock_name: 종목명
            output_dir: 출력 디렉토리
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # CSV 저장
        train_df.to_csv(output_path / f"{stock_name}_train.csv", index=False, encoding='utf-8-sig')
        val_df.to_csv(output_path / f"{stock_name}_val.csv", index=False, encoding='utf-8-sig')
        test_df.to_csv(output_path / f"{stock_name}_test.csv", index=False, encoding='utf-8-sig')
        
        print(f"\n  전처리 데이터 저장: {output_path}")
    
    def save_scaler(self, scaler: object, filename: str, output_dir: str = "data/preprocessed"):
        """
        스케일러 저장
        
        Args:
            scaler: 스케일러 객체
            filename: 파일명
            output_dir: 출력 디렉토리
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        filepath = output_path / filename
        with open(filepath, 'wb') as f:
            pickle.dump(scaler, f)
        
        print(f"  스케일러 저장: {filepath}")
    
    def preprocess_stock(
        self,
        filename: str,
        stock_name: str,
        normalize_method: str = 'minmax',
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        종목 데이터 전처리 파이프라인
        
        Args:
            filename: 데이터 파일명
            stock_name: 종목명
            normalize_method: 정규화 방법
            train_ratio: 학습 데이터 비율
            val_ratio: 검증 데이터 비율
            test_ratio: 테스트 데이터 비율
            
        Returns:
            train_df, val_df, test_df
        """
        print(f"\n{'='*60}")
        print(f"{stock_name} 데이터 전처리")
        print(f"{'='*60}")
        
        # 1. 데이터 로드
        print("\n1. 데이터 로드...")
        df = self.load_data(filename)
        print(f"  원본 데이터: {len(df):,}개")
        
        # 2. 기술적 지표 추가
        print("\n2. 기술적 지표 추가...")
        df = self.add_technical_indicators(df)
        
        # 3. NaN 제거
        print("\n3. 결측치 처리...")
        df = self.remove_nan(df)
        print(f"  최종 데이터: {len(df):,}개")
        
        # 4. 데이터 분리 (정규화 전에 분리)
        print("\n4. 데이터 분리...")
        train_df, val_df, test_df = self.split_data(df, train_ratio, val_ratio, test_ratio)
        
        # 5. 정규화 (학습 데이터 기준으로만 fit!)
        print("\n5. 데이터 정규화...")
        
        # 정규화에서 제외할 컬럼
        exclude_cols = ['datetime', 'stock_code', 'stock_name']
        
        # 학습 데이터로 스케일러 학습
        numeric_columns = train_df.select_dtypes(include=[np.number]).columns.tolist()
        columns_to_scale = [col for col in numeric_columns if col not in exclude_cols]
        
        if normalize_method == 'minmax':
            scaler = MinMaxScaler(feature_range=(0, 1))
        else:
            scaler = StandardScaler()
        
        # ✅ 중요: 학습 데이터로만 fit (데이터 누수 방지)
        scaler.fit(train_df[columns_to_scale])
        print(f"  [중요] 스케일러를 학습 데이터로만 fit했습니다 (데이터 누수 방지)")
        
        # 각 데이터셋에 transform만 적용
        train_df[columns_to_scale] = scaler.transform(train_df[columns_to_scale])
        val_df[columns_to_scale] = scaler.transform(val_df[columns_to_scale])
        test_df[columns_to_scale] = scaler.transform(test_df[columns_to_scale])
        
        print(f"  {normalize_method} 정규화 완료: {len(columns_to_scale)}개 특성")
        
        # 스케일러 정보 저장 (나중에 inverse_transform에 사용)
        self.scaler = scaler
        self.columns_to_scale = columns_to_scale
        
        # 6. 저장
        print("\n6. 데이터 저장...")
        self.save_preprocessed_data(train_df, val_df, test_df, stock_name)
        self.save_scaler(scaler, f"{stock_name}_scaler.pkl")
        
        print(f"\n{'='*60}")
        print(f"{stock_name} 전처리 완료!")
        print(f"{'='*60}")
        
        return train_df, val_df, test_df


