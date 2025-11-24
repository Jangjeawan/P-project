"""
데이터 전처리 메인 스크립트
"""
import sys
from data_preprocessor import DataPreprocessor


def main():
    """메인 실행 함수"""
    print("""
    ============================================================
            국내 주식 AI 트레이딩 - 데이터 전처리
    ============================================================
    """)
    
    # 전처리할 종목 리스트
    stocks = [
        {"filename": "005930_삼성전자_5min.csv", "name": "삼성전자"},
        {"filename": "035420_네이버_5min.csv", "name": "네이버"},
        {"filename": "005380_현대차_5min.csv", "name": "현대차"}
    ]
    
    # 전처리 설정
    config = {
        "normalize_method": "minmax",  # minmax 또는 standard
        "train_ratio": 0.7,            # 70%
        "val_ratio": 0.15,             # 15%
        "test_ratio": 0.15             # 15%
    }
    
    print(f"\n전처리 설정:")
    print(f"  정규화 방법: {config['normalize_method']}")
    print(f"  학습/검증/테스트 비율: {config['train_ratio']}/{config['val_ratio']}/{config['test_ratio']}")
    print()
    
    try:
        # 전처리기 초기화
        preprocessor = DataPreprocessor()
        
        # 각 종목 전처리
        results = {}
        
        for stock in stocks:
            try:
                train_df, val_df, test_df = preprocessor.preprocess_stock(
                    filename=stock["filename"],
                    stock_name=stock["name"],
                    normalize_method=config["normalize_method"],
                    train_ratio=config["train_ratio"],
                    val_ratio=config["val_ratio"],
                    test_ratio=config["test_ratio"]
                )
                
                results[stock["name"]] = {
                    "success": True,
                    "train_size": len(train_df),
                    "val_size": len(val_df),
                    "test_size": len(test_df),
                    "features": len(train_df.columns)
                }
                
            except Exception as e:
                print(f"\n[ERROR] {stock['name']} 전처리 실패: {e}")
                results[stock["name"]] = {"success": False, "error": str(e)}
        
        # 결과 요약
        print(f"\n\n{'='*60}")
        print("전처리 완료 요약")
        print(f"{'='*60}\n")
        
        for stock_name, result in results.items():
            if result.get("success"):
                print(f"[OK] {stock_name}")
                print(f"     특성: {result['features']}개")
                print(f"     학습: {result['train_size']:,}개")
                print(f"     검증: {result['val_size']:,}개")
                print(f"     테스트: {result['test_size']:,}개")
                print()
            else:
                print(f"[FAIL] {stock_name}: {result.get('error', '알 수 없는 오류')}\n")
        
        print(f"{'='*60}")
        
        # 성공 여부 확인
        if all(r.get("success") for r in results.values()):
            print("\n[SUCCESS] 모든 데이터 전처리가 완료되었습니다!")
            print("\n다음 단계: AI 모델 학습을 진행할 수 있습니다.")
            return 0
        else:
            print("\n[WARNING] 일부 데이터 전처리에 실패했습니다.")
            return 1
            
    except Exception as e:
        print(f"\n[ERROR] 예상치 못한 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())


