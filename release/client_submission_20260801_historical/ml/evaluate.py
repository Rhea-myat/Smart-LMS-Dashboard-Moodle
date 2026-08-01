from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from ml.ensemble import apply_threshold, weighted_average


def summarize_metrics(y_true, pred, prob) -> dict:
    return {
        "accuracy": accuracy_score(y_true, pred),
        "precision": precision_score(y_true, pred),
        "recall": recall_score(y_true, pred),
        "f1_score": f1_score(y_true, pred),
        "roc_auc": roc_auc_score(y_true, prob),
        "confusion_matrix": confusion_matrix(y_true, pred).tolist(),
        "classification_report": classification_report(y_true, pred)
    }


def evaluate_behaviour_model(model, scaler, X_test, y_test) -> dict:
    X_test_scaled = scaler.transform(X_test)
    pred = model.predict(X_test_scaled)
    prob = model.predict_proba(X_test_scaled)[:, 1]

    return {
        "pred": pred,
        "prob": prob,
        "metrics": summarize_metrics(y_test, pred, prob)
    }


def evaluate_academic_model(model, X_test, y_test) -> dict:
    pred = model.predict(X_test)
    prob = model.predict_proba(X_test)[:, 1]

    return {
        "pred": pred,
        "prob": prob,
        "metrics": summarize_metrics(y_test, pred, prob)
    }


def evaluate_ensemble(y_true, behaviour_prob, academic_prob, behaviour_weight=0.5, academic_weight=0.5, threshold=0.5) -> dict:
    final_prob = weighted_average(
        behaviour_prob,
        academic_prob,
        behaviour_weight,
        academic_weight
    )
    final_pred = apply_threshold(final_prob, threshold)

    return {
        "pred": final_pred,
        "prob": final_prob,
        "metrics": summarize_metrics(y_true, final_pred, final_prob)
    }