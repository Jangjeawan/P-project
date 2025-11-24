"""
수집된 데이터 확인 스크립트
"""
import pandas as pd
import os

print("="*60)
print("수집된 데이터 확인")
print("="*60)

# 5분봉 데이터 확인
data_dir = "data/processed"
files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]

for filename in files:
    filepath = os.path.join(data_dir, filename)
    df = pd.read_csv(filepath)
    
    print(f"\n파일: {filename}")
    print(f"총 레코드: {len(df):,}개")
    print(f"\n데이터 샘플 (처음 5개):")
    print(df.head())
    print(f"\n기본 통계:")
    print(df[['open', 'high', 'low', 'close', 'volume']].describe())
    print("\n" + "-"*60)

print("\n데이터 수집 완료! 이제 AI 모델 학습을 진행할 수 있습니다.")


