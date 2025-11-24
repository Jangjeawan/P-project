"""
모델 평가 및 시각화
"""
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Tuple, Dict
import pandas as pd
from pathlib import Path


class ModelEvaluator:
    """모델 평가 및 결과 시각화"""
    
    def __init__(self, output_dir: str = "results"):
        """
        Args:
            output_dir: 결과 저장 디렉토리
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 한글 폰트 설정 (Windows)
        plt.rcParams['font.family'] = 'Malgun Gothic'
        plt.rcParams['axes.unicode_minus'] = False
    
    def plot_training_history(
        self,
        history,
        model_name: str,
        save: bool = True
    ):
        """학습 과정 시각화"""
        fig, axes = plt.subplots(1, 2, figsize=(15, 5))
        
        # Loss
        axes[0].plot(history.history['loss'], label='Train Loss', linewidth=2)
        axes[0].plot(history.history['val_loss'], label='Val Loss', linewidth=2)
        axes[0].set_title(f'{model_name} - Training Loss', fontsize=14, fontweight='bold')
        axes[0].set_xlabel('Epoch', fontsize=12)
        axes[0].set_ylabel('Loss (MSE)', fontsize=12)
        axes[0].legend(fontsize=10)
        axes[0].grid(True, alpha=0.3)
        
        # MAE
        axes[1].plot(history.history['mae'], label='Train MAE', linewidth=2)
        axes[1].plot(history.history['val_mae'], label='Val MAE', linewidth=2)
        axes[1].set_title(f'{model_name} - Mean Absolute Error', fontsize=14, fontweight='bold')
        axes[1].set_xlabel('Epoch', fontsize=12)
        axes[1].set_ylabel('MAE', fontsize=12)
        axes[1].legend(fontsize=10)
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save:
            filepath = self.output_dir / f'{model_name}_training_history.png'
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            print(f"  학습 그래프 저장: {filepath}")
        
        plt.show()
    
    def plot_predictions(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        model_name: str,
        dataset_name: str = 'Test',
        save: bool = True,
        n_samples: int = 500
    ):
        """예측 결과 시각화"""
        # 샘플 수 제한
        y_true = y_true[:n_samples]
        y_pred = y_pred[:n_samples].flatten()
        
        fig, axes = plt.subplots(2, 1, figsize=(15, 10))
        
        # 시계열 그래프
        x = np.arange(len(y_true))
        axes[0].plot(x, y_true, label='Actual', linewidth=2, alpha=0.7)
        axes[0].plot(x, y_pred, label='Predicted', linewidth=2, alpha=0.7)
        axes[0].set_title(f'{model_name} - {dataset_name} Predictions', 
                         fontsize=14, fontweight='bold')
        axes[0].set_xlabel('Time Steps', fontsize=12)
        axes[0].set_ylabel('Normalized Close Price', fontsize=12)
        axes[0].legend(fontsize=10)
        axes[0].grid(True, alpha=0.3)
        
        # 산점도
        axes[1].scatter(y_true, y_pred, alpha=0.5, s=20)
        axes[1].plot([y_true.min(), y_true.max()], 
                    [y_true.min(), y_true.max()], 
                    'r--', linewidth=2, label='Perfect Prediction')
        axes[1].set_title(f'{model_name} - Actual vs Predicted', 
                         fontsize=14, fontweight='bold')
        axes[1].set_xlabel('Actual', fontsize=12)
        axes[1].set_ylabel('Predicted', fontsize=12)
        axes[1].legend(fontsize=10)
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save:
            filepath = self.output_dir / f'{model_name}_{dataset_name}_predictions.png'
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            print(f"  예측 그래프 저장: {filepath}")
        
        plt.show()
    
    def plot_error_distribution(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        model_name: str,
        dataset_name: str = 'Test',
        save: bool = True
    ):
        """오차 분포 시각화"""
        errors = y_true - y_pred.flatten()
        
        fig, axes = plt.subplots(1, 2, figsize=(15, 5))
        
        # 히스토그램
        axes[0].hist(errors, bins=50, edgecolor='black', alpha=0.7)
        axes[0].axvline(x=0, color='r', linestyle='--', linewidth=2)
        axes[0].set_title(f'{model_name} - Error Distribution', 
                         fontsize=14, fontweight='bold')
        axes[0].set_xlabel('Prediction Error', fontsize=12)
        axes[0].set_ylabel('Frequency', fontsize=12)
        axes[0].grid(True, alpha=0.3)
        
        # Q-Q plot
        from scipy import stats
        stats.probplot(errors, dist="norm", plot=axes[1])
        axes[1].set_title(f'{model_name} - Q-Q Plot', 
                         fontsize=14, fontweight='bold')
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save:
            filepath = self.output_dir / f'{model_name}_{dataset_name}_error_distribution.png'
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            print(f"  오차 분포 그래프 저장: {filepath}")
        
        plt.show()
    
    def print_evaluation_results(
        self,
        results: Dict[str, float],
        model_name: str,
        dataset_name: str = 'Test'
    ):
        """평가 결과 출력"""
        print(f"\n{'='*60}")
        print(f"{model_name} - {dataset_name} 평가 결과")
        print(f"{'='*60}")
        print(f"[정규화된 값]")
        print(f"  Loss (MSE):        {results['loss']:.6f}")
        print(f"  MAE:               {results['mae']:.6f}")
        print(f"  RMSE:              {results['rmse']:.6f}")
        print(f"  R² Score:          {results['r2_score']:.6f}")
        print(f"  MAPE:              {results['mape']:.2f}%")
        
        # ✅ 실제 스케일 메트릭 출력
        if 'mae_real' in results:
            print(f"\n[실제 값 (역정규화)]")
            print(f"  MAE (실제):        {results['mae_real']:.2f} 원")
            print(f"  RMSE (실제):       {results['rmse_real']:.2f} 원")
            print(f"  R² Score:          {results['r2_real']:.6f}")
            print(f"  MAPE:              {results['mape_real']:.2f}%")
        
        print(f"{'='*60}")
    
    def save_results_to_csv(
        self,
        results: Dict[str, float],
        model_name: str,
        dataset_name: str = 'Test'
    ):
        """결과를 CSV로 저장"""
        df = pd.DataFrame([results])
        df.insert(0, 'model', model_name)
        df.insert(1, 'dataset', dataset_name)
        
        filepath = self.output_dir / 'evaluation_results.csv'
        
        # 파일이 존재하면 추가, 없으면 새로 생성
        if filepath.exists():
            df.to_csv(filepath, mode='a', header=False, index=False)
        else:
            df.to_csv(filepath, index=False)
        
        print(f"  결과 저장: {filepath}")


