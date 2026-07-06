from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import numpy as np

from src.config import DEFAULT_WEIGHTS, RISK_BANDS


@dataclass(slots=True)
class ScoreResult:
    structural_score: float
    fire_score: float
    compliance_score: float
    overall_score: float
    risk_category: str
    explanation: dict[str, Any]

    def to_record(self) -> dict[str, Any]:
        return {
            "structural_score": self.structural_score,
            "fire_score": self.fire_score,
            "compliance_score": self.compliance_score,
            "overall_score": self.overall_score,
            "risk_category": self.risk_category,
            "explanation_json": json.dumps(self.explanation),
        }


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return float(np.clip(value, minimum, maximum))


def normalize_binary(value: bool | int) -> float:
    return 100.0 if bool(value) else 0.0


def normalize_scaled(value: float, minimum: float, target: float) -> float:
    if value <= minimum:
        return 0.0
    if value >= target:
        return 100.0
    return clamp(((value - minimum) / (target - minimum)) * 100.0)


def normalize_count(value: int, target: int) -> float:
    if target <= 0:
        return 100.0
    return clamp((value / target) * 100.0)


def grade_to_score(concrete_grade: str) -> float:
    mapping = {
        "C15": 45.0,
        "C20": 60.0,
        "C25": 75.0,
        "C30": 90.0,
        "C35": 100.0,
    }
    return mapping.get(concrete_grade.upper(), 50.0)


def steel_to_score(steel_type: str) -> float:
    mapping = {
        "MILD": 60.0,
        "Y12": 75.0,
        "Y16": 85.0,
        "HIGH TENSILE": 95.0,
        "TMT": 100.0,
    }
    return mapping.get(steel_type.upper(), 65.0)


def approval_to_score(status: str) -> float:
    mapping = {
        "Approved": 100.0,
        "Conditional": 70.0,
        "Pending": 45.0,
        "Rejected": 10.0,
    }
    return mapping.get(status, 40.0)


def verification_to_score(status: str) -> float:
    mapping = {
        "Verified": 100.0,
        "Partially Verified": 65.0,
        "Unverified": 20.0,
    }
    return mapping.get(status, 30.0)


def determine_risk_category(overall_score: float) -> str:
    for threshold, label in RISK_BANDS:
        if overall_score >= threshold:
            return label
    return "Critical Risk"


def compute_structural_score(building: dict[str, Any], structural: dict[str, Any]) -> tuple[float, dict[str, float]]:
    floor_target = max(1, int(building["number_of_floors"]))
    components = {
        "concrete_grade": grade_to_score(structural["concrete_grade"]),
        "reinforcement_steel_type": steel_to_score(structural["reinforcement_steel_type"]),
        "column_dimensions_cm": normalize_scaled(float(structural["column_dimensions_cm"]), 15.0, 40.0),
        "floor_count_compliance": normalize_binary(structural["floor_count_compliance"]),
        "supervision_records": normalize_binary(structural["supervision_records"]),
        "design_scale_adjustment": normalize_scaled(float(floor_target), 1.0, 12.0),
    }
    weights = {
        "concrete_grade": 0.20,
        "reinforcement_steel_type": 0.15,
        "column_dimensions_cm": 0.20,
        "floor_count_compliance": 0.20,
        "supervision_records": 0.15,
        "design_scale_adjustment": 0.10,
    }
    score = sum(components[key] * weights[key] for key in components)
    return clamp(score), components


def compute_fire_score(building: dict[str, Any], fire: dict[str, Any]) -> tuple[float, dict[str, float]]:
    floors = max(1, int(building["number_of_floors"]))
    staircase_target = 2 if floors >= 4 else 1
    extinguisher_target = max(2, floors * 2)
    detector_target = max(4, floors * 3)

    components = {
        "number_of_staircases": normalize_count(int(fire["number_of_staircases"]), staircase_target),
        "staircase_width_m": normalize_scaled(float(fire["staircase_width_m"]), 0.6, 1.5),
        "fire_exits": normalize_count(int(fire["fire_exits"]), staircase_target),
        "fire_extinguishers": normalize_count(int(fire["fire_extinguishers"]), extinguisher_target),
        "smoke_detectors": normalize_count(int(fire["smoke_detectors"]), detector_target),
        "fire_alarms": normalize_binary(fire["fire_alarms"]),
        "sprinklers": normalize_binary(fire["sprinklers"]),
        "emergency_lighting": normalize_binary(fire["emergency_lighting"]),
    }
    weights = {
        "number_of_staircases": 0.15,
        "staircase_width_m": 0.15,
        "fire_exits": 0.10,
        "fire_extinguishers": 0.15,
        "smoke_detectors": 0.10,
        "fire_alarms": 0.15,
        "sprinklers": 0.10,
        "emergency_lighting": 0.10,
    }
    score = sum(components[key] * weights[key] for key in components)
    return clamp(score), components


def compute_compliance_score(compliance: dict[str, Any]) -> tuple[float, dict[str, float]]:
    document_count = len([item.strip() for item in compliance["uploaded_document_metadata"].split(",") if item.strip()])
    components = {
        "approval_status": approval_to_score(compliance["approval_status"]),
        "verification_status": verification_to_score(compliance["verification_status"]),
        "inspector_registration_number": 100.0 if compliance["inspector_registration_number"].strip() else 0.0,
        "developer_registration_number": 100.0 if compliance["developer_registration_number"].strip() else 0.0,
        "document_metadata": normalize_count(document_count, 3),
    }
    weights = {
        "approval_status": 0.35,
        "verification_status": 0.30,
        "inspector_registration_number": 0.10,
        "developer_registration_number": 0.10,
        "document_metadata": 0.15,
    }
    score = sum(components[key] * weights[key] for key in components)
    return clamp(score), components


def calculate_scores(
    building: dict[str, Any],
    structural: dict[str, Any],
    fire: dict[str, Any],
    compliance: dict[str, Any],
) -> ScoreResult:
    structural_score, structural_components = compute_structural_score(building, structural)
    fire_score, fire_components = compute_fire_score(building, fire)
    compliance_score, compliance_components = compute_compliance_score(compliance)

    overall_score = clamp(
        (structural_score * DEFAULT_WEIGHTS["structural"])
        + (fire_score * DEFAULT_WEIGHTS["fire"])
        + (compliance_score * DEFAULT_WEIGHTS["compliance"])
    )
    risk_category = determine_risk_category(overall_score)

    explanation = {
        "weights": DEFAULT_WEIGHTS,
        "structural_components": structural_components,
        "fire_components": fire_components,
        "compliance_components": compliance_components,
        "formula": "overall = structural*0.45 + fire*0.35 + compliance*0.20",
    }

    return ScoreResult(
        structural_score=round(structural_score, 2),
        fire_score=round(fire_score, 2),
        compliance_score=round(compliance_score, 2),
        overall_score=round(overall_score, 2),
        risk_category=risk_category,
        explanation=explanation,
    )
