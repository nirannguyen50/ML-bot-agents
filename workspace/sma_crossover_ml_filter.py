"""
# SMA Crossover ML Filter - Data Scientist
# Version: 1.0
# Features engineered from task #2 for EURUSD

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
from sklearn.preprocessing import StandardScaler
import joblib
import warnings
warnings.filterwarnings('ignore')

class SMACrossoverMLFilter:
    def __init__(self, features_file='data/features/eurusd_features.csv'):
        self.features_df = pd.read_csv(features_file, parse_dates=['Date'])
        self.model = None
        self.scaler = StandardScaler()
        self.feature_importance = None
        
    def prepare_features_target(self):
        """Prepare features and target variable for ML model"""
        df = self.features_df.copy()
        
        # 1. Define SMA Crossover Signal
        df['sma_signal'] = np.where(df['SMA_50'] > df['SMA_200'], 1, -1)
        df['prev_sma_signal'] = df['sma_signal'].shift(1)
        df['crossover'] = np.where(df['sma_signal'] != df['prev_sma_signal'], 1, 0)
        
        # 2. Define Target: Profitable Trade (1) vs Unprofitable (0)
        # Use future 5-day return after crossover
        df['future_return'] = df['Close'].pct_change(5).shift(-5)
        df['target'] = np.where(df['future_return'] > 0.001, 1, 0)  # 0.1% threshold
        
        # 3. Feature Selection from engineered features
        feature_cols = [
            'SMA_50', 'SMA_200', 'EMA_20', 'RSI_14', 'MACD', 'MACD_signal',
            'BB_upper', 'BB_lower', 'BB_width', 'ATR_14', 'Volatility_20',
            'Momentum_10', 'Volume_ratio', 'Price_position'
        ]
        
        # Filter only rows with crossovers for training
        df_crossover = df[df['crossover'] == 1].copy()
        df_crossover = df_crossover.dropna(subset=feature_cols + ['target'])
        
        X = df_crossover[feature_cols]
        y = df_crossover['target']
        
        return X, y, df_crossover
    
    def train_model(self, test_size=0.2):
        """Train Random Forest model with time-series cross-validation"""
        X, y, _ = self.prepare_features_target()
        
        # Time-based split for financial data
        split_idx = int(len(X) * (1 - test_size))
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train Random Forest
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            class_weight='balanced'
        )
        
        self.model.fit(X_train_scaled, y_train)
        
        # Predictions
        y_pred = self.model.predict(X_test_scaled)
        
        # Feature importance
        self.feature_importance = pd.DataFrame({
            'feature': X.columns,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        # Metrics
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred),
            'recall': recall_score(y_test, y_pred),
            'f1': f1_score(y_test, y_pred),
            'train_size': len(X_train),
            'test_size': len(X_test),
            'positive_rate': y_test.mean()
        }
        
        return metrics, classification_report(y_test, y_pred)
    
    def predict_signal(self, current_features):
        """Predict if current crossover signal is profitable"""
        if self.model is None:
            raise ValueError("Model not trained. Call train_model first.")
        
        # Prepare input
        feature_cols = [
            'SMA_50', 'SMA_200', 'EMA_20', 'RSI_14', 'MACD', 'MACD_signal',
            'BB_upper', 'BB_lower', 'BB_width', 'ATR_14', 'Volatility_20',
            'Momentum_10', 'Volume_ratio', 'Price_position'
        ]
        
        current_df = pd.DataFrame([current_features])
        X_scaled = self.scaler.transform(current_df[feature_cols])
        
        prediction = self.model.predict(X_scaled)[0]
        probability = self.model.predict_proba(X_scaled)[0][1]
        
        return {
            'prediction': int(prediction),
            'probability': float(probability),
            'signal': 'PROFITABLE' if prediction == 1 else 'UNPROFITABLE'
        }
    
    def save_model(self, path='workspace/sma_crossover_model.pkl'):
        """Save trained model and scaler"""
        joblib.dump({
            'model': self.model,
            'scaler': self.scaler,
            'feature_importance': self.feature_importance
        }, path)
        print(f"Model saved to {path}")
    
    def load_model(self, path='workspace/sma_crossover_model.pkl'):
        """Load trained model"""
        saved_data = joblib.load(path)
        self.model = saved_data['model']
        self.scaler = saved_data['scaler']
        self.feature_importance = saved_data['feature_importance']

def main():
    """Main execution function"""
    print("=== SMA Crossover ML Filter - Training ===")
    
    # Initialize and train
    ml_filter = SMACrossoverMLFilter()
    
    # Train model
    metrics, report = ml_filter.train_model(test_size=0.2)
    
    print(f"\nTraining Results:")
    print(f"Train samples: {metrics['train_size']}")
    print(f"Test samples: {metrics['test_size']}")
    print(f"Accuracy: {metrics['accuracy']:.4f}")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall: {metrics['recall']:.4f}")
    print(f"F1 Score: {metrics['f1']:.4f}")
    print(f"Positive rate in test: {metrics['positive_rate']:.4f}")
    
    print(f"\nClassification Report:")
    print(report)
    
    print(f"\nTop 5 Feature Importances:")
    print(ml_filter.feature_importance.head(5).to_string(index=False))
    
    # Save model
    ml_filter.save_model()
    
    # Example prediction
    print(f"\n=== Example Prediction ===")
    sample_features = {
        'SMA_50': 1.0850, 'SMA_200': 1.0800, 'EMA_20': 1.0860,
        'RSI_14': 55.0, 'MACD': 0.001, 'MACD_signal': 0.0005,
        'BB_upper': 1.0900, 'BB_lower': 1.0750, 'BB_width': 0.015,
        'ATR_14': 0.005, 'Volatility_20': 0.008, 'Momentum_10': 0.002,
        'Volume_ratio': 1.2, 'Price_position': 0.6
    }
    
    prediction = ml_filter.predict_signal(sample_features)
    print(f"Sample prediction: {prediction}")
    
    return ml_filter

if __name__ == "__main__":
    ml_filter = main()