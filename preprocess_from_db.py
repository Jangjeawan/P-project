"""
PostgreSQL에서 데이터를 읽어와 전처리 후 다시 저장
"""
import pandas as pd
import sys
from database import DatabaseManager, StockPrice, StockPriceProcessed
from technical_indicators import TechnicalIndicators
from sqlalchemy import and_
from datetime import datetime


class DBPreprocessor:
    """데이터베이스 기반 전처리"""
    
    def __init__(self):
        self.db = DatabaseManager()
        
    def load_from_db(self, stock_code: str) -> pd.DataFrame:
        """
        PostgreSQL에서 데이터 로드
        
        Args:
            stock_code: 종목코드
            
        Returns:
            DataFrame
        """
        session = self.db.get_session()
        
        try:
            # 데이터 조회
            query = session.query(StockPrice).filter(
                StockPrice.stock_code == stock_code
            ).order_by(StockPrice.datetime)
            
            # DataFrame 변환
            data = []
            for record in query:
                data.append({
                    'datetime': record.datetime,
                    'open': record.open,
                    'high': record.high,
                    'low': record.low,
                    'close': record.close,
                    'volume': record.volume,
                    'stock_code': record.stock_code,
                    'stock_name': record.stock_name
                })
            
            df = pd.DataFrame(data)
            
            if not df.empty:
                print(f"  로드 완료: {len(df):,}개 레코드")
            
            return df
            
        finally:
            session.close()
    
    def preprocess_and_save(self, stock_code: str, stock_name: str):
        """
        전처리 및 DB 저장
        
        Args:
            stock_code: 종목코드
            stock_name: 종목명
        """
        print(f"\n{'='*60}")
        print(f"{stock_name} 전처리 시작")
        print(f"{'='*60}")
        
        # 1. DB에서 데이터 로드
        print("\n1. 데이터 로드 중...")
        df = self.load_from_db(stock_code)
        
        if df.empty:
            print(f"❌ {stock_name} 데이터 없음")
            return False
        
        # 2. 기술적 지표 추가
        print("\n2. 기술적 지표 계산 중...")
        print("  이동평균, MACD, RSI, 볼린저밴드, 스토캐스틱, ATR, 거래량 지표...")
        df = TechnicalIndicators.add_all_indicators(df)
        
        # 3. NaN 제거
        initial_len = len(df)
        df = df.dropna().reset_index(drop=True)
        removed = initial_len - len(df)
        print(f"\n3. 결측치 제거: {removed}개 행 삭제")
        print(f"  최종 데이터: {len(df):,}개")
        
        # 4. DB에 저장
        print("\n4. PostgreSQL에 저장 중...")
        success = self._save_to_db(df, stock_code, stock_name)
        
        if success:
            print(f"✅ {stock_name} 전처리 완료!")
            return True
        else:
            print(f"❌ {stock_name} 저장 실패")
            return False
    
    def _save_to_db(self, df: pd.DataFrame, stock_code: str, stock_name: str) -> bool:
        """전처리된 데이터를 DB에 저장"""
        session = self.db.get_session()
        
        try:
            # 기존 데이터 확인
            existing_count = session.query(StockPriceProcessed).filter(
                StockPriceProcessed.stock_code == stock_code
            ).count()
            
            if existing_count > 0:
                print(f"  기존 데이터 {existing_count:,}개 발견 - 삭제 후 재삽입")
                session.query(StockPriceProcessed).filter(
                    StockPriceProcessed.stock_code == stock_code
                ).delete()
                session.commit()
            
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
            
            print(f"\n  ✅ 저장 완료: {inserted:,}개")
            return True
            
        except Exception as e:
            session.rollback()
            print(f"\n  ❌ 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            session.close()


def main():
    """메인 실행 함수"""
    print("""
    ============================================================
        PostgreSQL 데이터 전처리 및 저장
    ============================================================
    """)
    
    # DB 연결
    db = DatabaseManager()
    if not db.connect():
        print("❌ 데이터베이스 연결 실패")
        return 1
    
    # 전처리할 종목
    stocks = [
        {"code": "005930", "name": "삼성전자"},
        {"code": "035420", "name": "네이버"},
        {"code": "005380", "name": "현대차"}
    ]
    
    # 전처리 실행
    preprocessor = DBPreprocessor()
    results = {}
    
    for stock in stocks:
        stock_code = stock['code']
        stock_name = stock['name']
        
        try:
            success = preprocessor.preprocess_and_save(stock_code, stock_name)
            results[stock_name] = success
        except Exception as e:
            print(f"\n❌ {stock_name} 오류: {e}")
            results[stock_name] = False
    
    # 결과 요약
    print(f"\n\n{'='*60}")
    print("전처리 완료 요약")
    print(f"{'='*60}\n")
    
    for stock_name, success in results.items():
        status = "✅ 성공" if success else "❌ 실패"
        print(f"{status}: {stock_name}")
    
    # 최종 데이터 확인
    print(f"\n\n{'='*60}")
    print("데이터베이스 최종 현황")
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
            
            print(f"  {stock_name}: 원본 {raw:,}개 → 전처리 {processed:,}개")
            
    finally:
        session.close()
    
    db.close()
    
    print(f"\n{'='*60}")
    print("✅ 모든 작업 완료!")
    print(f"{'='*60}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())



