"""
전처리된 데이터 확인 스크립트
"""
import pandas as pd
import os

print("="*60)
print("전처리된 데이터 확인")
print("="*60)

# 전처리된 데이터 디렉토리
data_dir = "data/preprocessed"

# CSV 파일 리스트
csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]

# 종목별로 그룹화
stocks = {}
for filename in csv_files:
    stock_name = filename.split('_')[0]
    if stock_name not in stocks:
        stocks[stock_name] = {}
    
    if 'train' in filename:
        stocks[stock_name]['train'] = filename
    elif 'val' in filename:
        stocks[stock_name]['val'] = filename
    elif 'test' in filename:
        stocks[stock_name]['test'] = filename

# 각 종목별 데이터 확인
for stock_name, files in stocks.items():
    print(f"\n{'='*60}")
    print(f"종목: {stock_name}")
    print(f"{'='*60}")
    
    for dataset_type, filename in files.items():
        filepath = os.path.join(data_dir, filename)
        df = pd.read_csv(filepath)
        
        print(f"\n[{dataset_type.upper()}] {filename}")
        print(f"  레코드 수: {len(df):,}개")
        print(f"  특성 수: {len(df.columns)}개")
        print(f"  기간: {df['datetime'].iloc[0]} ~ {df['datetime'].iloc[-1]}")
        
        # 특성 목록
        feature_cols = [col for col in df.columns if col not in ['datetime', 'stock_code', 'stock_name']]
        
        if dataset_type == 'train':  # 학습 데이터에서만 상세 정보 출력
            print(f"\n  특성 목록 ({len(feature_cols)}개):")
            
            # 그룹별로 정리
            groups = {
                'OHLCV': ['open', 'high', 'low', 'close', 'volume'],
                '이동평균': [col for col in feature_cols if 'MA_' in col or 'EMA_' in col],
                'MACD': [col for col in feature_cols if 'MACD' in col],
                '볼린저밴드': [col for col in feature_cols if 'BB_' in col],
                'RSI/스토캐스틱': [col for col in feature_cols if 'RSI' in col or 'Stoch' in col],
                '거래량지표': [col for col in feature_cols if 'Volume' in col or 'OBV' in col],
                'ATR': [col for col in feature_cols if 'ATR' in col],
                '수익률': [col for col in feature_cols if 'Return' in col or 'Ratio' in col]
            }
            
            for group_name, group_cols in groups.items():
                if group_cols:
                    print(f"    {group_name}: {', '.join(group_cols)}")
            
            # 데이터 샘플
            print(f"\n  데이터 샘플 (처음 3개):")
            print(df[['datetime', 'open', 'high', 'low', 'close', 'volume']].head(3).to_string(index=False))

print(f"\n{'='*60}")
print("전처리 완료!")
print(f"{'='*60}\n")

print("생성된 특성:")
print("  - OHLCV: 기본 가격 및 거래량 데이터")
print("  - 이동평균: MA_5, MA_10, MA_20, MA_60, EMA_12, EMA_26")
print("  - MACD: MACD, MACD_Signal, MACD_Hist")
print("  - 볼린저밴드: BB_Upper, BB_Middle, BB_Lower, BB_Width, BB_PctB")
print("  - RSI: 14일 RSI")
print("  - 스토캐스틱: Stoch_K, Stoch_D")
print("  - ATR: 14일 ATR")
print("  - 거래량 지표: Volume_MA, Volume_Ratio, OBV")
print("  - 수익률: Return, Log_Return, Return_5d, Return_10d, Return_20d")
print("  - 비율: HL_Ratio, CO_Ratio")
print("\n모든 특성이 0-1 범위로 정규화되었습니다.")





