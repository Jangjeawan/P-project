"""
LSTM 모델 학습 메인 스크립트
"""
import sys
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # TensorFlow 경고 메시지 억제

import numpy as np
from sequence_generator import SequenceGenerator
from lstm_model import StockLSTMModel
from model_evaluator import ModelEvaluator


def train_stock_model(
    stock_name: str,
    sequence_length: int = 60,
    lstm_units: list = [128, 64, 32],
    dropout_rate: float = 0.2,
    learning_rate: float = 0.001,
    epochs: int = 100,
    batch_size: int = 32
):
    """종목별 LSTM 모델 학습"""
    
    print(f"\n{'='*60}")
    print(f"{stock_name} - LSTM 모델 학습")
    print(f"{'='*60}")
    
    # 1. 데이터 경로 설정
    data_dir = "data/preprocessed"
    train_file = f"{data_dir}/{stock_name}_train.csv"
    val_file = f"{data_dir}/{stock_name}_val.csv"
    test_file = f"{data_dir}/{stock_name}_test.csv"
    scaler_file = f"{data_dir}/{stock_name}_scaler.pkl"
    
    # ✅ 스케일러 로드
    import pickle
    with open(scaler_file, 'rb') as f:
        scaler = pickle.load(f)
    print(f"스케일러 로드 완료: {scaler_file}")
    
    # 2. 시퀀스 데이터 생성
    seq_gen = SequenceGenerator(
        sequence_length=sequence_length,
        prediction_horizon=1
    )
    
    (X_train, y_train), (X_val, y_val), (X_test, y_test), feature_names = \
        seq_gen.prepare_datasets(train_file, val_file, test_file)
    
    print(f"\n특성 수: {len(feature_names)}")
    print(f"주요 특성: {', '.join(feature_names[:10])}...")
    
    # 3. 모델 생성 및 학습
    input_shape = (X_train.shape[1], X_train.shape[2])
    
    model = StockLSTMModel(
        input_shape=input_shape,
        lstm_units=lstm_units,
        dropout_rate=dropout_rate,
        learning_rate=learning_rate
    )
    
    model.build_model()
    
    # 학습
    history = model.train(
        X_train, y_train,
        X_val, y_val,
        model_name=stock_name,
        epochs=epochs,
        batch_size=batch_size,
        verbose=1
    )
    
    # 4. 모델 저장
    model_path = f"models/{stock_name}_lstm.keras"
    model.save_model(model_path)
    
    # 5. 평가
    evaluator = ModelEvaluator(output_dir=f"results/{stock_name}")
    
    # 학습 과정 시각화
    print("\n학습 과정 시각화 중...")
    evaluator.plot_training_history(history, stock_name)
    
    # ✅ 검증 데이터 평가 (스케일러 포함)
    print("\n검증 데이터 평가 중...")
    val_results = model.evaluate(X_val, y_val, scaler=scaler, close_idx=3)
    evaluator.print_evaluation_results(val_results, stock_name, "Validation")
    
    # ✅ 테스트 데이터 평가 (스케일러 포함)
    print("\n테스트 데이터 평가 중...")
    test_results = model.evaluate(X_test, y_test, scaler=scaler, close_idx=3)
    evaluator.print_evaluation_results(test_results, stock_name, "Test")
    
    # 예측 시각화
    print("\n예측 결과 시각화 중...")
    y_pred = model.predict(X_test)
    evaluator.plot_predictions(y_test, y_pred, stock_name, "Test")
    evaluator.plot_error_distribution(y_test, y_pred, stock_name, "Test")
    
    # 결과 저장
    evaluator.save_results_to_csv(val_results, stock_name, "Validation")
    evaluator.save_results_to_csv(test_results, stock_name, "Test")
    
    print(f"\n{'='*60}")
    print(f"{stock_name} 모델 학습 완료!")
    print(f"{'='*60}\n")
    
    return model, test_results


def main():
    """메인 실행 함수"""
    print("""
    ============================================================
            국내 주식 AI 트레이딩 - LSTM 모델 학습
    ============================================================
    """)
    
    # 학습 설정
    config = {
        "sequence_length": 60,      # 60개 시퀀스 (5분봉 기준 5시간)
        "lstm_units": [128, 64, 32],
        "dropout_rate": 0.2,
        "learning_rate": 0.001,
        "epochs": 100,
        "batch_size": 32
    }
    
    print("학습 설정:")
    for key, value in config.items():
        print(f"  {key}: {value}")
    
    # 학습할 종목
    stocks = ["삼성전자", "네이버", "현대차"]
    
    results_summary = {}
    
    try:
        for stock_name in stocks:
            try:
                model, results = train_stock_model(
                    stock_name=stock_name,
                    **config
                )
                results_summary[stock_name] = {
                    "success": True,
                    "results": results
                }
                
            except Exception as e:
                print(f"\n[ERROR] {stock_name} 학습 실패: {e}")
                import traceback
                traceback.print_exc()
                results_summary[stock_name] = {
                    "success": False,
                    "error": str(e)
                }
        
        # 최종 결과 요약
        print(f"\n\n{'='*60}")
        print("학습 완료 요약")
        print(f"{'='*60}\n")
        
        for stock_name, result in results_summary.items():
            if result.get("success"):
                res = result["results"]
                print(f"[OK] {stock_name}")
                print(f"     RMSE: {res['rmse']:.6f}")
                print(f"     MAE:  {res['mae']:.6f}")
                print(f"     R²:   {res['r2_score']:.6f}")
                print(f"     MAPE: {res['mape']:.2f}%")
                print()
            else:
                print(f"[FAIL] {stock_name}: {result.get('error', '알 수 없는 오류')}\n")
        
        print(f"{'='*60}")
        print("\n모든 모델이 'models/' 디렉토리에 저장되었습니다.")
        print("결과 그래프는 'results/' 디렉토리에서 확인할 수 있습니다.")
        
        return 0
        
    except Exception as e:
        print(f"\n[ERROR] 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())


