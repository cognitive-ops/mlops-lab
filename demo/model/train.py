"""
Train an Iris classifier and save artifacts for serving.

Usage:
    python train.py                          # defaults
    python train.py --n-estimators 200 --max-depth 5
    python train.py --no-mlflow              # skip experiment tracking
"""
import argparse
import json
import os
from pathlib import Path

import joblib
import numpy as np
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split

ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", "artifacts"))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--n-estimators", type=int, default=100)
    p.add_argument("--max-depth", type=int, default=None)
    p.add_argument("--test-size", type=float, default=0.2)
    p.add_argument("--random-state", type=int, default=42)
    p.add_argument("--no-mlflow", action="store_true", help="Skip MLflow logging")
    return p.parse_args()


def train(args: argparse.Namespace) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    # ── Data ───────────────────────────────────────────────────────────────────
    iris = load_iris()
    X, y = iris.data, iris.target
    class_names: list[str] = list(iris.target_names)
    feature_names: list[str] = list(iris.feature_names)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=args.test_size,
        random_state=args.random_state,
        stratify=y,
    )

    # ── Train ──────────────────────────────────────────────────────────────────
    params = {
        "n_estimators": args.n_estimators,
        "max_depth": args.max_depth,
        "random_state": args.random_state,
    }
    clf = RandomForestClassifier(**params)
    clf.fit(X_train, y_train)

    # ── Evaluate ───────────────────────────────────────────────────────────────
    y_pred = clf.predict(X_test)
    accuracy = float(accuracy_score(y_test, y_pred))
    f1 = float(f1_score(y_test, y_pred, average="weighted"))

    print(f"\nAccuracy      : {accuracy:.4f}")
    print(f"F1 (weighted) : {f1:.4f}")
    print(f"\nClassification Report:\n{classification_report(y_test, y_pred, target_names=class_names)}")

    # ── Save artifacts ─────────────────────────────────────────────────────────
    model_path = ARTIFACTS_DIR / "model.joblib"
    meta_path = ARTIFACTS_DIR / "metadata.json"

    joblib.dump(clf, model_path)

    metadata = {
        "feature_names": feature_names,
        "class_names": class_names,
        "n_features": int(X.shape[1]),
        "params": {**params, "test_size": args.test_size},
        "metrics": {"accuracy": accuracy, "f1_weighted": f1},
    }
    meta_path.write_text(json.dumps(metadata, indent=2))

    print(f"\n✓ Model saved    → {model_path}")
    print(f"✓ Metadata saved → {meta_path}")

    # ── MLflow (optional) ──────────────────────────────────────────────────────
    if args.no_mlflow:
        return

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    if not tracking_uri:
        print("\nMLFLOW_TRACKING_URI not set — skipping experiment tracking.")
        return

    try:
        import mlflow

        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(os.getenv("MLFLOW_EXPERIMENT", "iris-classifier"))

        with mlflow.start_run(run_name=os.getenv("RUN_NAME", "random-forest")):
            mlflow.log_params({**params, "test_size": args.test_size})
            mlflow.log_metrics({"accuracy": accuracy, "f1_weighted": f1})
            mlflow.sklearn.log_model(clf, "model")
            mlflow.log_artifact(str(meta_path))
            print(f"✓ MLflow run logged → {mlflow.get_tracking_uri()}")

    except Exception as exc:
        print(f"MLflow logging failed (non-fatal): {exc}")


if __name__ == "__main__":
    train(parse_args())
