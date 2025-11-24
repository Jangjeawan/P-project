"""
주식 데이터 수집 및 저장 모듈
"""
import pandas as pd
import numpy as np
from datetime import datetime
import os
import yaml
from pathlib import Path
from typing import List, Dict
from kis_api import KISAPIClient


class StockDataCollector:
    """주식 데이터 수집 및 전처리"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Args:
            config_path: 설정 파일 경로
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # 데이터 저장 경로 생성
        self.raw_data_path = Path(self.config['data_path']['raw_data'])
        self.processed_data_path = Path(self.config['data_path']['processed_data'])
        self.raw_data_path.mkdir(parents=True, exist_ok=True)
        self.processed_data_path.mkdir(parents=True, exist_ok=True)
        
        # KIS API 클라이언트 초기화
        real_mode = os.getenv("KIS_REAL_MODE", "False").lower() == "true"
        self.api_client = KISAPIClient(real_mode=real_mode)
    
    def collect_stock_data(self, stock_code: str, stock_name: str) -> pd.DataFrame:
        """
        특정 종목의 데이터 수집
        
        Args:
            stock_code: 종목코드
            stock_name: 종목명
            
        Returns:
            수집된 데이터 DataFrame
        """
        print(f"\n{'='*60}")
        print(f"종목: {stock_name} ({stock_code})")
        print(f"{'='*60}")
        
        days_back = self.config['data_collection']['period_days']
        
        # 데이터 수집 (일봉)
        raw_data = self.api_client.get_historical_daily_data(
            stock_code, days_back
        )
        
        if not raw_data:
            print(f"[WARNING] {stock_name} 데이터 수집 실패")
            return pd.DataFrame()
        
        # DataFrame 변환
        df = self._convert_to_dataframe(raw_data, stock_code, stock_name)
        
        # 원본 데이터 저장
        self._save_raw_data(df, stock_code, stock_name)
        
        return df
    
    def _convert_to_dataframe(
        self,
        raw_data: List[Dict],
        stock_code: str,
        stock_name: str
    ) -> pd.DataFrame:
        """
        API 응답을 DataFrame으로 변환 (일봉 데이터)
        
        Args:
            raw_data: API 응답 데이터
            stock_code: 종목코드
            stock_name: 종목명
            
        Returns:
            변환된 DataFrame
        """
        data_list = []
        
        for item in raw_data:
            try:
                date_str = item.get('stck_bsop_date', '')
                data_list.append({
                    'date': date_str,
                    'datetime': pd.to_datetime(date_str, format='%Y%m%d'),
                    'open': float(item.get('stck_oprc', 0)),
                    'high': float(item.get('stck_hgpr', 0)),
                    'low': float(item.get('stck_lwpr', 0)),
                    'close': float(item.get('stck_clpr', 0)),
                    'volume': int(item.get('acml_vol', 0)),
                    'stock_code': stock_code,
                    'stock_name': stock_name
                })
            except (ValueError, KeyError) as e:
                print(f"[WARNING] 데이터 변환 오류: {e}")
                continue
        
        if not data_list:
            return pd.DataFrame()
        
        df = pd.DataFrame(data_list)
        
        # 시간순 정렬 (오래된 날짜부터)
        df = df.sort_values('datetime').reset_index(drop=True)
        
        return df
    
    def generate_intraday_from_daily(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        일봉 데이터에서 5분봉 시뮬레이션 데이터 생성
        (실제 5분봉 데이터가 아닌, 일봉 기반 시뮬레이션)
        
        Args:
            df: 일봉 데이터
            
        Returns:
            5분봉 시뮬레이션 데이터
        """
        if df.empty:
            return df
        
        all_5min_data = []
        
        for _, row in df.iterrows():
            # 각 거래일에 대해 09:00 ~ 15:30 사이 5분봉 생성
            # 총 78개의 5분봉 (390분 / 5분)
            date = row['datetime']
            
            # 시뮬레이션: 일봉 데이터를 기반으로 5분봉 생성
            # 실제로는 랜덤하지만 OHLC 관계 유지
            open_price = row['open']
            high_price = row['high']
            low_price = row['low']
            close_price = row['close']
            total_volume = row['volume']
            
            # 78개의 5분봉 타임스탬프 생성
            time_slots = pd.date_range(
                start=f"{date.strftime('%Y-%m-%d')} 09:00:00",
                end=f"{date.strftime('%Y-%m-%d')} 15:25:00",
                freq='5T'
            )
            
            # 간단한 시뮬레이션: 각 5분봉마다 가격 분배
            for i, ts in enumerate(time_slots):
                # 시뮬레이션 로직 (실제 데이터는 아님)
                ratio = i / len(time_slots)
                
                # 시가에서 종가로 선형 변화 + 랜덤성
                estimated_close = open_price + (close_price - open_price) * ratio
                estimated_open = open_price + (close_price - open_price) * (ratio - 0.05 if ratio > 0.05 else 0)
                
                all_5min_data.append({
                    'datetime': ts,
                    'open': estimated_open,
                    'high': max(estimated_open, estimated_close) * 1.002,
                    'low': min(estimated_open, estimated_close) * 0.998,
                    'close': estimated_close,
                    'volume': total_volume // len(time_slots),
                    'stock_code': row['stock_code'],
                    'stock_name': row['stock_name']
                })
        
        result_df = pd.DataFrame(all_5min_data)
        return result_df
    
    def _save_raw_data(self, df: pd.DataFrame, stock_code: str, stock_name: str):
        """원본 데이터 저장"""
        if df.empty:
            return
        
        filename = f"{stock_code}_{stock_name}_daily_raw.csv"
        filepath = self.raw_data_path / filename
        
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"[OK] 원본 일봉 데이터 저장: {filepath}")
    
    def save_processed_data(self, df: pd.DataFrame, stock_code: str, stock_name: str):
        """처리된 데이터 저장"""
        if df.empty:
            return
        
        filename = f"{stock_code}_{stock_name}_5min.csv"
        filepath = self.processed_data_path / filename
        
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"[OK] 5분봉 데이터 저장: {filepath}")
    
    def collect_all_stocks(self):
        """설정 파일의 모든 종목 데이터 수집"""
        stocks = self.config['stocks']
        
        print(f"\n{'='*60}")
        print(f"총 {len(stocks)}개 종목 데이터 수집 시작")
        print(f"기간: 최근 {self.config['data_collection']['period_days']}일")
        print(f"{'='*60}\n")
        
        results = {}
        
        for stock in stocks:
            stock_code = stock['code']
            stock_name = stock['name']
            
            try:
                # 일봉 데이터 수집
                df_daily = self.collect_stock_data(stock_code, stock_name)
                
                if not df_daily.empty:
                    # 5분봉 시뮬레이션 데이터 생성
                    df_5min = self.generate_intraday_from_daily(df_daily)
                    
                    # 저장
                    self.save_processed_data(df_5min, stock_code, stock_name)
                    
                    results[stock_name] = {
                        'success': True,
                        'records_daily': len(df_daily),
                        'records_5min': len(df_5min)
                    }
                    
                    print(f"\n[STATS] {stock_name} 통계:")
                    print(f"  - 일봉: {len(df_daily):,}개")
                    print(f"  - 5분봉 (시뮬레이션): {len(df_5min):,}개")
                    print(f"  - 기간: {df_daily['datetime'].min().date()} ~ {df_daily['datetime'].max().date()}")
                else:
                    results[stock_name] = {'success': False}
                    
            except Exception as e:
                print(f"\n[ERROR] {stock_name} 수집 실패: {e}")
                results[stock_name] = {'success': False, 'error': str(e)}
        
        # 최종 결과 출력
        self._print_summary(results)
        
        return results
    
    def _print_summary(self, results: Dict):
        """수집 결과 요약 출력"""
        print(f"\n{'='*60}")
        print("데이터 수집 완료")
        print(f"{'='*60}\n")
        
        success_count = sum(1 for r in results.values() if r.get('success'))
        total_count = len(results)
        
        print(f"성공: {success_count}/{total_count}")
        print()
        
        for stock_name, result in results.items():
            if result.get('success'):
                print(f"[OK] {stock_name}: {result.get('records_5min', 0):,}개 (5분봉)")
            else:
                error_msg = result.get('error', '알 수 없는 오류')
                print(f"[FAIL] {stock_name}: {error_msg}")
        
        print(f"\n{'='*60}")

