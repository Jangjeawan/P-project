"""
한국투자증권 KIS API 클라이언트
"""
import requests
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv

load_dotenv()


class KISAPIClient:
    """한국투자증권 Open API 클라이언트"""
    
    def __init__(self, real_mode: bool = False):
        """
        Args:
            real_mode: True면 실전투자, False면 모의투자
        """
        self.app_key = os.getenv("KIS_APP_KEY")
        self.app_secret = os.getenv("KIS_APP_SECRET")
        
        if not self.app_key or not self.app_secret:
            raise ValueError("KIS_APP_KEY와 KIS_APP_SECRET을 .env 파일에 설정해주세요")
        
        self.real_mode = real_mode
        self.base_url = (
            "https://openapi.koreainvestment.com:9443" if real_mode
            else "https://openapivts.koreainvestment.com:29443"
        )
        
        self.access_token = None
        self.token_expired = None
        
    def _get_access_token(self) -> str:
        """접근 토큰 발급"""
        # 토큰이 유효하면 재사용
        if self.access_token and self.token_expired:
            if datetime.now() < self.token_expired:
                return self.access_token
        
        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        data = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        
        response = requests.post(url, headers=headers, data=json.dumps(data))
        
        if response.status_code != 200:
            raise Exception(f"토큰 발급 실패: {response.text}")
        
        result = response.json()
        self.access_token = result["access_token"]
        
        # 토큰 만료 시간 설정 (24시간 - 1시간 여유)
        self.token_expired = datetime.now() + timedelta(hours=23)
        
        return self.access_token
    
    def _get_headers(self, tr_id: str) -> Dict[str, str]:
        """API 요청 헤더 생성"""
        return {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self._get_access_token()}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id
        }
    
    def get_stock_price_minute(
        self,
        stock_code: str,
        date: str,
        time_from: str = "090000",
        time_to: str = "153000"
    ) -> List[Dict]:
        """
        주식 분봉 조회
        
        Args:
            stock_code: 종목코드 (6자리)
            date: 조회일자 (YYYYMMDD)
            time_from: 시작시간 (HHMMSS)
            time_to: 종료시간 (HHMMSS)
            
        Returns:
            분봉 데이터 리스트
        """
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"
        
        # 실전/모의 구분
        tr_id = "FHKST03010200" if self.real_mode else "FHKST03010200"
        
        params = {
            "FID_ETC_CLS_CODE": "",
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
            "FID_INPUT_HOUR_1": time_from,
            "FID_PW_DATA_INCU_YN": "Y",  # 과거 데이터 포함
        }
        
        headers = self._get_headers(tr_id)
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            raise Exception(f"API 요청 실패: {response.text}")
        
        result = response.json()
        
        if result.get("rt_cd") != "0":
            raise Exception(f"API 오류: {result.get('msg1')}")
        
        return result.get("output2", [])
    
    def get_stock_price_daily(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        adj_price: bool = True
    ) -> List[Dict]:
        """
        주식 일봉 조회
        
        Args:
            stock_code: 종목코드 (6자리)
            start_date: 시작일자 (YYYYMMDD)
            end_date: 종료일자 (YYYYMMDD)
            adj_price: 수정주가 여부
            
        Returns:
            일봉 데이터 리스트
        """
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
        
        tr_id = "FHKST03010100" if self.real_mode else "FHKST03010100"
        
        all_data = []
        
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
            "FID_INPUT_DATE_1": start_date,
            "FID_INPUT_DATE_2": end_date,
            "FID_PERIOD_DIV_CODE": "D",  # D:일, W:주, M:월
            "FID_ORG_ADJ_PRC": "0" if adj_price else "1",  # 0:수정주가, 1:원주가
        }
        
        headers = self._get_headers(tr_id)
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            raise Exception(f"API 요청 실패: {response.text}")
        
        result = response.json()
        
        if result.get("rt_cd") != "0":
            raise Exception(f"API 오류: {result.get('msg1')}")
        
        return result.get("output2", [])
    
    def get_historical_daily_data(
        self,
        stock_code: str,
        days_back: int = 365
    ) -> List[Dict]:
        """
        과거 일봉 데이터 수집
        
        Args:
            stock_code: 종목코드
            days_back: 과거 며칠치 데이터
            
        Returns:
            전체 일봉 데이터
        """
        print(f"\n{stock_code} 데이터 수집 시작...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        
        print(f"  기간: {start_str} ~ {end_str}")
        
        try:
            # 일봉 데이터 조회
            daily_data = self.get_stock_price_daily(
                stock_code, start_str, end_str
            )
            
            if daily_data:
                print(f"  완료: {len(daily_data)}개의 데이터 수집")
            else:
                print(f"  데이터 없음")
            
            # API 호출 제한
            time.sleep(0.1)
            
            return daily_data
            
        except Exception as e:
            print(f"  실패: {e}")
            return []

