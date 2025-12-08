"""
주식 데이터 수집 메인 스크립트
"""
import sys
import io
from data_collector import StockDataCollector

# Windows 콘솔 인코딩 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def main():
    """메인 실행 함수"""
    print("""
    ============================================================
            국내 주식 AI 트레이딩 - 데이터 수집 시스템
    ============================================================
    """)
    
    try:
        # 데이터 수집기 초기화
        collector = StockDataCollector()
        
        # 전체 종목 데이터 수집
        results = collector.collect_all_stocks()
        
        # 성공 여부 확인
        if all(r.get('success') for r in results.values()):
            print("\n[SUCCESS] 모든 데이터 수집이 성공적으로 완료되었습니다!")
            return 0
        else:
            print("\n[WARNING] 일부 데이터 수집에 실패했습니다.")
            return 1
            
    except FileNotFoundError as e:
        print(f"\n[ERROR] 설정 파일을 찾을 수 없습니다: {e}")
        print("config.yaml 파일이 있는지 확인해주세요.")
        return 1
        
    except ValueError as e:
        print(f"\n[ERROR] API 인증 정보가 없습니다: {e}")
        print("\n다음 단계를 따라주세요:")
        print("1. https://apiportal.koreainvestment.com 에서 API 키 발급")
        print("2. .env.example 파일을 .env로 복사")
        print("3. .env 파일에 API 키 정보 입력")
        return 1
        
    except Exception as e:
        print(f"\n[ERROR] 예상치 못한 오류가 발생했습니다: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

