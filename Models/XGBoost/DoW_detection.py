import time
from pathlib import Path

import pandas as pd
import xgboost as xgb
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import train_test_split


DATA_PATH = Path(__file__).resolve().parent.parent / "dataset.csv"


def prepare_data(path: str):
    df = pd.read_csv(path)

    if "bot" not in df.columns:
        raise ValueError("Khong tim thay cot 'bot' trong dataset.")

    # 1. Lấy Nhãn
    raw_y = df["bot"]
    y = raw_y

    if raw_y.dtype == "bool":
        y = raw_y.astype(int)
    elif pd.api.types.is_numeric_dtype(raw_y):
        y = pd.to_numeric(raw_y, errors="coerce")
    else:
        normalized = raw_y.astype(str).str.strip().str.lower()
        y = normalized.map(
            {
                "true": 1,
                "false": 0,
                "1": 1,
                "0": 0,
                "yes": 1,
                "no": 0,
            }
        )

    if y.isna().any():
        invalid_values = raw_y[y.isna()].dropna().unique().tolist()[:10]
        raise ValueError(f"Nhan bot khong hop le, vi du: {invalid_values}")

    y = y.astype(int)

    # 2. KHAI TỬ KẺ PHẢN BỘI
    # Bắt buộc drop Id và timestamp. 
    # Tạm thời drop luôn FunctionId để ép model phải học từ CPU/RAM/RTT
    cols_to_drop = ["bot", "Id", "timestamp", "IP", "maxcpu", "avgcpu", "p95maxcpu", "vmcategory", "vmcorecountbucket", "vmmemorybucket"] 
    X = df.drop(columns=cols_to_drop, errors='ignore').copy()

    # 3. MÃ HÓA CÁC CỘT CHỮ (Label Encoding)
    # Giữ lại thông tin của vmcategory, functionTrigger thay vì biến thành 0
    for col in X.select_dtypes(include=["object"]).columns:
        X[col] = X[col].astype("category").cat.codes

    # 4. Dọn rác các cột còn lại và Ép về float32 cho GPU
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors='coerce').fillna(0)
    
    X = X.astype('float32')

    return train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )


def build_xgb_model(use_gpu: bool = True):
    base_params = {
        "n_estimators": 300,
        "max_depth": 6,
        "learning_rate": 0.05,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
        "eval_metric": "logloss",
        "random_state": 42,
    }

    if not use_gpu:
        return xgb.XGBClassifier(**base_params, tree_method="hist", device="cpu")

    try:
        # XGBoost >= 2.0
        return xgb.XGBClassifier(**base_params, tree_method="hist", device="cuda")
    except TypeError:
        # XGBoost cu: gpu_hist/gpu_predictor
        return xgb.XGBClassifier(
            **base_params,
            tree_method="gpu_hist",
            predictor="gpu_predictor",
        )


def main():
    print("Dang load va chia du lieu...")
    X_train, X_test, y_train, y_test = prepare_data(DATA_PATH)

    model = build_xgb_model(use_gpu=True)
    device_used = "GPU (CUDA)"

    try:
        start_time = time.time()
        model.fit(X_train, y_train)
        import matplotlib.pyplot as plt
        xgb.plot_importance(model, max_num_features=10)
        plt.show()
    except xgb.core.XGBoostError:
        print("Khong dung duoc CUDA, tu dong fallback sang CPU...")
        model = build_xgb_model(use_gpu=False)
        device_used = "CPU"
        start_time = time.time()
        model.fit(X_train, y_train)

    train_time = time.time() - start_time

    start_inf = time.time()
    y_pred = model.predict(X_test)
    inf_time = (time.time() - start_inf) / len(X_test)

    f1 = f1_score(y_test, y_pred)

    results = pd.DataFrame(
        [
            {
                "Model": "XGBoost",
                "Device": device_used,
                "F1-Score": f1,
                "Train Time (s)": train_time,
                "Inference Time (ms)": inf_time * 1000,
            }
        ]
    )

    print(results)
    print("\nClassification report:\n")
    print(classification_report(y_test, y_pred, digits=4))


if __name__ == "__main__":
    main()