"""
분류용 데이터 전처리 (상승/하락/유지)
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, List
from sklearn.preprocessing import MinMaxScaler, StandardScaler, LabelEncoder
import pickle


class ClassificationPreprocessor:
    """주식 상승/하락/유지 분류를 위한 전처리"""
    
    def __init__(self, data_dir: str = "data/processed"):
        self.data_dir = Path(data_dir)
        self.scaler = None
        self.label_encoder = LabelEncoder()
        
    def create_target_labels(
        self,
        df: pd.DataFrame,
        threshold: float = 0.01,  # 1% 기준
        future_steps: int = 1
    ) -> pd.DataFrame:
        """
        타겟 레이블 생성: 상승/하락/유지
        
        Args:
            df: DataFrame
            threshold: 상승/하락 판단 기준 (비율)
            future_steps: 몇 스텝 후를 예측할 것인가
            
        Returns:
            레이블이 추가된 DataFrame
        """
        df = df.copy()
        
        # 미래 종가
        df['future_close'] = df['close'].shift(-future_steps)
        
        # 변화율 계산
        df['price_change'] = (df['future_close'] - df['close']) / df['close']
        
        # 레이블 생성
        def classify(change):
            if pd.isna(change):
                return None
            elif change > threshold:
                return 'UP'      # 상승
            elif change < -threshold:
                return 'DOWN'    # 하락
            else:
                return 'HOLD'    # 유지
        
        df['target'] = df['price_change'].apply(classify)
        
        # 마지막 행들 제거 (미래 데이터 없음)
        df = df.dropna(subset=['target'])
        
        # 통계
        print(f"\n  타겟 분포:")
        target_counts = df['target'].value_counts()
        total = len(df)
        for label in ['UP', 'HOLD', 'DOWN']:
            if label in target_counts.index:
                count = target_counts[label]
                pct = count / total * 100
                print(f"    {label}: {count:,}개 ({pct:.1f}%)")
        
        # 불필요한 컬럼 제거
        df = df.drop(['future_close', 'price_change'], axis=1)
        
        return df
    
    def encode_labels(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        레이블을 숫자로 인코딩
        
        Returns:
            DataFrame, 인코딩된 레이블
        """
        df = df.copy()
        
        # 레이블 인코딩 (DOWN=0, HOLD=1, UP=2)
        y = self.label_encoder.fit_transform(df['target'])
        
        # 인코딩 정보 출력
        print(f"\n  레이블 인코딩:")
        for i, label in enumerate(self.label_encoder.classes_):
            print(f"    {label} → {i}")
        
        # target 컬럼 제거
        df = df.drop('target', axis=1)
        
        return df, y
    
    def preprocess_for_classification(
        self,
        csv_file: str,
        stock_name: str,
        threshold: float = 0.01,
        future_steps: int = 1
    ):
        """
        분류 모델용 전처리 파이프라인
        
        Args:
            csv_file: 원본 CSV 파일
            stock_name: 종목명
            threshold: 상승/하락 기준 (1% = 0.01)
            future_steps: 예측할 미래 시점
        """
        print(f"\n{'='*60}")
        print(f"{stock_name} 분류 모델 전처리")
        print(f"{'='*60}")
        print(f"설정: 상승/하락 기준 ±{threshold*100}%, {future_steps}스텝 후 예측")
        
        # 1. 데이터 로드
        print("\n1. 데이터 로드...")
        df = pd.read_csv(csv_file)
        df['datetime'] = pd.to_datetime(df['datetime'])
        print(f"  원본: {len(df):,}개")
        
        # 2. 타겟 레이블 생성
        print("\n2. 타겟 레이블 생성...")
        df = self.create_target_labels(df, threshold, future_steps)
        print(f"  레이블 생성 후: {len(df):,}개")
        
        # 3. 특성과 타겟 분리
        print("\n3. 특성과 타겟 분리...")
        exclude_cols = ['datetime', 'stock_code', 'stock_name', 'target']
        feature_columns = [col for col in df.columns if col not in exclude_cols]
        
        # 타겟 인코딩
        df_features, y = self.encode_labels(df)
        
        # 4. 데이터 분리 (시계열이므로 순서대로)
        print("\n4. 데이터 분리 (70/15/15)...")
        n = len(df_features)
        train_end = int(n * 0.7)
        val_end = int(n * 0.85)
        
        train_df = df_features.iloc[:train_end].copy()
        val_df = df_features.iloc[train_end:val_end].copy()
        test_df = df_features.iloc[val_end:].copy()
        
        y_train = y[:train_end]
        y_val = y[train_end:val_end]
        y_test = y[val_end:]
        
        print(f"  학습: {len(train_df):,}개")
        print(f"  검증: {len(val_df):,}개")
        print(f"  테스트: {len(test_df):,}개")
        
        # 5. 정규화 (train으로만 fit)
        print("\n5. 특성 정규화...")
        numeric_columns = train_df.select_dtypes(include=[np.number]).columns.tolist()
        exclude = ['datetime', 'stock_code', 'stock_name']
        columns_to_scale = [col for col in numeric_columns if col not in exclude]
        
        scaler = MinMaxScaler(feature_range=(0, 1))
        scaler.fit(train_df[columns_to_scale])
        
        train_df[columns_to_scale] = scaler.transform(train_df[columns_to_scale])
        val_df[columns_to_scale] = scaler.transform(val_df[columns_to_scale])
        test_df[columns_to_scale] = scaler.transform(test_df[columns_to_scale])
        
        print(f"  정규화: {len(columns_to_scale)}개 특성")
        
        # 6. 저장
        print("\n6. 데이터 저장...")
        output_dir = Path("data/classification")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # DataFrame 저장 (레이블 포함)
        train_df['target'] = y_train
        val_df['target'] = y_val
        test_df['target'] = y_test
        
        train_df.to_csv(output_dir / f"{stock_name}_train_class.csv", index=False, encoding='utf-8-sig')
        val_df.to_csv(output_dir / f"{stock_name}_val_class.csv", index=False, encoding='utf-8-sig')
        test_df.to_csv(output_dir / f"{stock_name}_test_class.csv", index=False, encoding='utf-8-sig')
        
        # 스케일러와 레이블 인코더 저장
        with open(output_dir / f"{stock_name}_scaler_class.pkl", 'wb') as f:
            pickle.dump(scaler, f)
        
        with open(output_dir / f"{stock_name}_label_encoder.pkl", 'wb') as f:
            pickle.dump(self.label_encoder, f)
        
        print(f"  저장 완료: {output_dir}")
        
        print(f"\n{'='*60}")
        print(f"{stock_name} 전처리 완료!")
        print(f"{'='*60}")
        
        return train_df, val_df, test_df


def main():
    """메인 실행"""
    print("""
    ============================================================
        분류 모델용 데이터 전처리
        (상승/하락/유지 예측)
    ============================================================
    """)
    
    # 설정
    threshold = 0.001  # 0.1% 기준 (5분봉에 적합)
    future_steps = 1  # 1스텝(5분) 후 예측
    
    print(f"\n설정:")
    print(f"  상승 기준: +{threshold*100}% 이상")
    print(f"  하락 기준: -{threshold*100}% 이하")
    print(f"  유지: 그 외")
    print(f"  예측 시점: {future_steps}스텝(5분) 후")
    
    # 종목
    stocks = [
        {"file": "data/processed/005930_삼성전자_5min.csv", "name": "삼성전자"},
        {"file": "data/processed/035420_네이버_5min.csv", "name": "네이버"},
        {"file": "data/processed/005380_현대차_5min.csv", "name": "현대차"}
    ]
    
    preprocessor = ClassificationPreprocessor()
    
    for stock in stocks:
        try:
            preprocessor.preprocess_for_classification(
                csv_file=stock["file"],
                stock_name=stock["name"],
                threshold=threshold,
                future_steps=future_steps
            )
        except Exception as e:
            print(f"\n❌ {stock['name']} 오류: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n\n{'='*60}")
    print("✅ 전처리 완료!")
    print(f"{'='*60}")
    print("\n다음 단계: 분류 모델 학습")
    print("  python train_classification.py")


if __name__ == "__main__":
    main()

