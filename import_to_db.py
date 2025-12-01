"""
CSV 데이터를 PostgreSQL에 삽입
"""
import pandas as pd
from pathlib import Path
from datetime import datetime
from database import DatabaseManager, StockPrice, StockPriceProcessed
from sqlalchemy import and_
import sys


class DataImporter:
    """CSV 데이터를 DB에 삽입"""
    
    def __init__(self):
        self.db = DatabaseManager()
        
    def import_raw_data(self, csv_file: str, stock_code: str, stock_name: str):
        """
        원본 5분봉 데이터 삽입
        
        Args:
            csv_file: CSV 파일 경로
            stock_code: 종목코드
            stock_name: 종목명
        """
        print(f"\n{'='*60}")
        print(f"{stock_name} 원본 데이터 삽입")
        print(f"{'='*60}")
        
        # CSV 읽기
        df = pd.read_csv(csv_file)
        df['datetime'] = pd.to_datetime(df['datetime'])
        
        print(f"총 {len(df):,}개 레코드 발견")
        
        # 세션 생성
        session = self.db.get_session()
        
        try:
            # 기존 데이터 확인
            existing_count = session.query(StockPrice).filter(
                StockPrice.stock_code == stock_code
            ).count()
            
            if existing_count > 0:
                print(f"⚠️  기존 데이터 {existing_count:,}개 발견")
                response = input("덮어쓰시겠습니까? (y/n): ")
                if response.lower() == 'y':
                    session.query(StockPrice).filter(
                        StockPrice.stock_code == stock_code
                    ).delete()
                    session.commit()
                    print(f"✅ 기존 데이터 삭제 완료")
                else:
                    print("❌ 삽입 취소")
                    return False
            
            # 배치 삽입
            batch_size = 1000
            inserted = 0
            
            for i in range(0, len(df), batch_size):
                batch = df.iloc[i:i+batch_size]
                
                records = []
                for _, row in batch.iterrows():
                    record = StockPrice(
                        stock_code=stock_code,
                        stock_name=stock_name,
                        datetime=row['datetime'],
                        open=float(row['open']),
                        high=float(row['high']),
                        low=float(row['low']),
                        close=float(row['close']),
                        volume=int(row['volume'])
                    )
                    records.append(record)
                
                session.bulk_save_objects(records)
                session.commit()
                
                inserted += len(records)
                print(f"  진행: {inserted:,}/{len(df):,} ({inserted/len(df)*100:.1f}%)", end='\r')
            
            print(f"\n✅ {stock_name} 삽입 완료: {inserted:,}개")
            return True
            
        except Exception as e:
            session.rollback()
            print(f"\n❌ 오류 발생: {e}")
            return False
        finally:
            session.close()
    
    def import_processed_data(self, csv_file: str, stock_code: str, stock_name: str):
        """
        전처리된 데이터 삽입 (기술적 지표 포함)
        
        Args:
            csv_file: CSV 파일 경로
            stock_code: 종목코드
            stock_name: 종목명
        """
        print(f"\n{'='*60}")
        print(f"{stock_name} 전처리 데이터 삽입")
        print(f"{'='*60}")
        
        # CSV 읽기
        df = pd.read_csv(csv_file)
        df['datetime'] = pd.to_datetime(df['datetime'])
        
        print(f"총 {len(df):,}개 레코드 발견")
        
        # 세션 생성
        session = self.db.get_session()
        
        try:
            # 기존 데이터 확인
            existing_count = session.query(StockPriceProcessed).filter(
                StockPriceProcessed.stock_code == stock_code
            ).count()
            
            if existing_count > 0:
                print(f"⚠️  기존 데이터 {existing_count:,}개 발견")
                response = input("덮어쓰시겠습니까? (y/n): ")
                if response.lower() == 'y':
                    session.query(StockPriceProcessed).filter(
                        StockPriceProcessed.stock_code == stock_code
                    ).delete()
                    session.commit()
                    print(f"✅ 기존 데이터 삭제 완료")
                else:
                    print("❌ 삽입 취소")
                    return False
            
            # 컬럼명 매핑
            column_map = {
                'MA_5': 'ma_5', 'MA_10': 'ma_10', 'MA_20': 'ma_20', 'MA_60': 'ma_60',
                'EMA_12': 'ema_12', 'EMA_26': 'ema_26',
                'MACD': 'macd', 'MACD_Signal': 'macd_signal', 'MACD_Hist': 'macd_hist',
                'BB_Upper': 'bb_upper', 'BB_Middle': 'bb_middle', 'BB_Lower': 'bb_lower',
                'BB_Width': 'bb_width', 'BB_PctB': 'bb_pctb',
                'RSI': 'rsi', 'Stoch_K': 'stoch_k', 'Stoch_D': 'stoch_d',
                'ATR': 'atr',
                'Volume_MA_5': 'volume_ma_5', 'Volume_MA_20': 'volume_ma_20',
                'Volume_Ratio': 'volume_ratio', 'OBV': 'obv',
                'Return': 'return_1d', 'Log_Return': 'log_return',
                'Return_5d': 'return_5d', 'Return_10d': 'return_10d', 'Return_20d': 'return_20d',
                'HL_Ratio': 'hl_ratio', 'CO_Ratio': 'co_ratio'
            }
            
            # 배치 삽입
            batch_size = 1000
            inserted = 0
            
            for i in range(0, len(df), batch_size):
                batch = df.iloc[i:i+batch_size]
                
                records = []
                for _, row in batch.iterrows():
                    record_data = {
                        'stock_code': stock_code,
                        'stock_name': stock_name,
                        'datetime': row['datetime'],
                        'open': float(row['open']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'close': float(row['close']),
                        'volume': int(row['volume'])
                    }
                    
                    # 기술적 지표 추가
                    for csv_col, db_col in column_map.items():
                        if csv_col in row.index:
                            value = row[csv_col]
                            record_data[db_col] = float(value) if pd.notna(value) else None
                    
                    record = StockPriceProcessed(**record_data)
                    records.append(record)
                
                session.bulk_save_objects(records)
                session.commit()
                
                inserted += len(records)
                print(f"  진행: {inserted:,}/{len(df):,} ({inserted/len(df)*100:.1f}%)", end='\r')
            
            print(f"\n✅ {stock_name} 삽입 완료: {inserted:,}개")
            return True
            
        except Exception as e:
            session.rollback()
            print(f"\n❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            session.close()


def main():
    """메인 실행 함수"""
    print("""
    ============================================================
            CSV 데이터를 PostgreSQL에 삽입
    ============================================================
    """)
    
    # DB 연결
    db = DatabaseManager()
    if not db.connect():
        print("\n❌ 데이터베이스 연결 실패")
        print("다음을 확인하세요:")
        print("1. PostgreSQL 서버가 실행 중인지")
        print("2. .env 파일에 올바른 DB 정보가 입력되어 있는지")
        print("3. 데이터베이스가 생성되어 있는지")
        return 1
    
    # 테이블 생성
    print("\n테이블 생성 중...")
    db.create_tables()
    
    # 데이터 임포터 초기화
    importer = DataImporter()
    
    # 삽입할 데이터 목록
    stocks = [
        {"code": "005930", "name": "삼성전자"},
        {"code": "035420", "name": "네이버"},
        {"code": "005380", "name": "현대차"}
    ]
    
    # 사용자 선택
    print("\n삽입할 데이터 유형을 선택하세요:")
    print("1. 원본 5분봉 데이터 (data/processed/*.csv)")
    print("2. 전처리된 데이터 (data/preprocessed/*_train.csv)")
    print("3. 둘 다")
    
    choice = input("\n선택 (1/2/3): ").strip()
    
    results = {}
    
    for stock in stocks:
        stock_code = stock['code']
        stock_name = stock['name']
        
        try:
            if choice in ['1', '3']:
                # 원본 데이터 삽입
                csv_file = f"data/processed/{stock_code}_{stock_name}_5min.csv"
                if Path(csv_file).exists():
                    success = importer.import_raw_data(csv_file, stock_code, stock_name)
                    results[f"{stock_name}_raw"] = success
                else:
                    print(f"⚠️  파일 없음: {csv_file}")
            
            if choice in ['2', '3']:
                # 전처리 데이터 삽입
                csv_file = f"data/preprocessed/{stock_name}_train.csv"
                if Path(csv_file).exists():
                    success = importer.import_processed_data(csv_file, stock_code, stock_name)
                    results[f"{stock_name}_processed"] = success
                else:
                    print(f"⚠️  파일 없음: {csv_file}")
                    
        except Exception as e:
            print(f"\n❌ {stock_name} 처리 중 오류: {e}")
            results[stock_name] = False
    
    # 결과 요약
    print(f"\n\n{'='*60}")
    print("삽입 완료 요약")
    print(f"{'='*60}\n")
    
    for name, success in results.items():
        status = "✅ 성공" if success else "❌ 실패"
        print(f"{status}: {name}")
    
    # 데이터 확인
    print(f"\n\n{'='*60}")
    print("데이터베이스 현황")
    print(f"{'='*60}\n")
    
    session = db.get_session()
    try:
        raw_count = session.query(StockPrice).count()
        processed_count = session.query(StockPriceProcessed).count()
        
        print(f"원본 데이터: {raw_count:,}개")
        print(f"전처리 데이터: {processed_count:,}개")
        
        print("\n종목별:")
        for stock in stocks:
            stock_code = stock['code']
            stock_name = stock['name']
            
            raw = session.query(StockPrice).filter(StockPrice.stock_code == stock_code).count()
            processed = session.query(StockPriceProcessed).filter(
                StockPriceProcessed.stock_code == stock_code
            ).count()
            
            print(f"  {stock_name}: 원본 {raw:,}개, 전처리 {processed:,}개")
            
    finally:
        session.close()
    
    db.close()
    
    print(f"\n{'='*60}")
    print("✅ 모든 작업 완료!")
    print(f"{'='*60}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())



