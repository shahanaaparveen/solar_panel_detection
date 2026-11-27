"""Severity rules independent of model confidence."""
HIGH_RISK = {"hotspot", "thermal anomaly", "anomaly", "diode", "bypass diode failure",
             "loose electrical connection", "reverse bias cell", "open circuit",
             "cracked glass", "physical damage", "broken frame", "delamination"}
LOW_RISK = {"dust accumulation", "bird dropping", "bird droppings", "leaves", "vegetation shading"}
MEDIUM_RISK = {"cell mismatch", "mud", "snow"}


def assess_finding(class_name, model_confidence, spatial_confidence=None, evidence_quality="unknown"):
    label = class_name.strip().lower()
    if label in HIGH_RISK:
        priority, recommendation = "High", "Arrange a qualified inspection and verify the affected module before repair."
    elif label in LOW_RISK:
        priority, recommendation = "Low", "Review the evidence and clean or clear the affected module if confirmed."
    elif label in MEDIUM_RISK:
        priority, recommendation = "Medium", "Review the evidence and schedule cleaning or maintenance as appropriate."
    else:
        priority, recommendation = "Medium", "Review the finding and confirm the condition during site inspection."
    review = model_confidence < 0.5 or spatial_confidence is None or spatial_confidence < 0.5 or evidence_quality != "good"
    return {"severity": None, "severity_status": "UNVALIDATED",
            "inspection_priority": priority, "priority_rule": "class_rule_v1_uncalibrated",
            "priority_explanation": "Class-based triage only; physical defect severity has not been calibrated on inspection data.",
            "finding_status": "SUSPECTED", "review_required": review,
            "recommendation": recommendation, "confidence_calibration": "uncalibrated"}
