# ml/ensemble.py

import numpy as np

def weighted_average(
    behaviour_prob,
    academic_prob,
    behaviour_weight,
    academic_weight
):
    behaviour_prob = np.asarray(behaviour_prob)
    academic_prob = np.asarray(academic_prob)

    return (
        behaviour_weight * behaviour_prob +
        academic_weight * academic_prob
    )


def apply_threshold(
    probabilities,
    threshold
):
    probabilities = np.asarray(probabilities)

    return (probabilities >= threshold).astype(int)


def build_prediction_result(
    metadata,
    behaviour_prob,
    academic_prob,
    final_prob,
    final_label,
    model_version
):
    """
    Combine metadata and prediction outputs into
    the prediction_result table.
    """

    prediction_result = metadata.copy()

    prediction_result["behaviour_probability"] = np.round(
        behaviour_prob,
        2
    ).astype(float)
    prediction_result["academic_probability"] = np.round(
        academic_prob,
        2
    ).astype(float)
    prediction_result["final_risk_probability"] = np.round(
        final_prob,
        2
    ).astype(float)
    prediction_result["final_risk_label"] = final_label
    prediction_result["ensemble_model_version"] = model_version

    return prediction_result