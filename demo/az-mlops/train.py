import pandas as pd
import mlflow
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

def main():
    df = pd.read_csv("iris.csv")
    X = df.drop("target", axis=1)
    y = df["target"]

    clf = RandomForestClassifier()
    clf.fit(X, y)

    acc = accuracy_score(y, clf.predict(X))

    mlflow.log_metric("accuracy", acc)
    joblib.dump(clf, "model.joblib")
    mlflow.sklearn.log_model(clf, "rf_model")

if __name__ == "__main__":
    main()
