import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, accuracy_score
import joblib
import os

def load_data(filepath='data/prepared_bets.csv'):
    if not os.path.exists(filepath):
        print(f"Error: {filepath} does not exist.")
        exit(1)
    return pd.read_csv(filepath)

def preprocess_data(df):
    import numpy as np  # Ensure numpy is imported
    
    # Feature Engineering
    df['price_log'] = df['price'].apply(lambda x: np.log(x) if x > 0 else 0)
    df['is_home'] = df['bet_type'].apply(lambda x: 1 if x == 'h2h' else 0)
    
    # Check for 'winning' column
    if 'winning' not in df.columns:
        print("Error: 'winning' column not found in DataFrame.")
        exit(1)
    
    features = ['price_log', 'point', 'travel_distance', 'is_home']
    X = df[features]
    y = df['winning']
    
    return X, y

def train_model(X, y):
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:,1]
    
    roc_auc = roc_auc_score(y_test, y_proba)
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"Model ROC-AUC: {roc_auc:.4f}")
    print(f"Model Accuracy: {accuracy:.4f}")
    
    return model

def save_model(model, filepath='models/nba_bet_model.pkl'):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    joblib.dump(model, filepath)
    print(f"Model saved to {filepath}")

if __name__ == "__main__":
    # Load data
    df = load_data()
    print("Data loaded successfully.")

    # Preprocess data
    X, y = preprocess_data(df)
    print("Data preprocessing completed.")

    # Train model
    model = train_model(X, y)
    print("Model training completed.")

    # Save model
    save_model(model)
    print("Model training and saving process completed successfully.")