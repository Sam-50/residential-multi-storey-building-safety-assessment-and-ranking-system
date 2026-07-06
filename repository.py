from __future__ import annotations

import json
from typing import Any

import pandas as pd

from src.auth import verify_password
from src.database import db_session, save_score
from src.scoring import calculate_scores


class SafetyRepository:
    def authenticate_user(self, username: str, password: str) -> dict[str, Any] | None:
        with db_session() as connection:
            user = connection.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        if not user or not verify_password(password, user["password_hash"]):
            return None
        return user

    def get_users(self) -> list[dict[str, Any]]:
        with db_session() as connection:
            return connection.execute(
                "SELECT id, username, full_name, role, created_at FROM users ORDER BY full_name"
            ).fetchall()

    def get_buildings(self) -> list[dict[str, Any]]:
        with db_session() as connection:
            return connection.execute(
                """
                SELECT
                    b.*,
                    s.structural_score,
                    s.fire_score,
                    s.compliance_score,
                    s.overall_score,
                    s.risk_category,
                    s.computed_at
                FROM buildings b
                LEFT JOIN scores s ON s.building_id = b.id
                ORDER BY COALESCE(s.overall_score, 0) DESC, b.building_name ASC
                """
            ).fetchall()

    def get_building_bundle(self, building_id: int) -> dict[str, Any] | None:
        with db_session() as connection:
            building = connection.execute("SELECT * FROM buildings WHERE id = ?", (building_id,)).fetchone()
            if not building:
                return None
            structural = connection.execute(
                "SELECT * FROM structural_assessments WHERE building_id = ?",
                (building_id,),
            ).fetchone()
            fire = connection.execute(
                "SELECT * FROM fire_assessments WHERE building_id = ?",
                (building_id,),
            ).fetchone()
            compliance = connection.execute(
                "SELECT * FROM compliance_records WHERE building_id = ?",
                (building_id,),
            ).fetchone()
            score = connection.execute("SELECT * FROM scores WHERE building_id = ?", (building_id,)).fetchone()
        return {
            "building": building,
            "structural": structural,
            "fire": fire,
            "compliance": compliance,
            "score": score,
        }

    def upsert_building_bundle(
        self,
        building_data: dict[str, Any],
        structural_data: dict[str, Any],
        fire_data: dict[str, Any],
        compliance_data: dict[str, Any],
        building_id: int | None = None,
    ) -> int:
        with db_session() as connection:
            if building_id is None:
                cursor = connection.execute(
                    """
                    INSERT INTO buildings (
                        building_name, location, number_of_floors, year_of_construction,
                        intended_use, approved_design_details, created_by
                    )
                    VALUES (
                        :building_name, :location, :number_of_floors, :year_of_construction,
                        :intended_use, :approved_design_details, :created_by
                    )
                    """,
                    building_data,
                )
                building_id = cursor.lastrowid
            else:
                connection.execute(
                    """
                    UPDATE buildings
                    SET
                        building_name = :building_name,
                        location = :location,
                        number_of_floors = :number_of_floors,
                        year_of_construction = :year_of_construction,
                        intended_use = :intended_use,
                        approved_design_details = :approved_design_details,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                    """,
                    {**building_data, "id": building_id},
                )

            connection.execute(
                """
                INSERT INTO structural_assessments (
                    building_id, concrete_grade, reinforcement_steel_type,
                    column_dimensions_cm, floor_count_compliance, supervision_records,
                    structural_compliance_notes, assessed_by
                )
                VALUES (
                    :building_id, :concrete_grade, :reinforcement_steel_type,
                    :column_dimensions_cm, :floor_count_compliance, :supervision_records,
                    :structural_compliance_notes, :assessed_by
                )
                ON CONFLICT(building_id) DO UPDATE SET
                    concrete_grade = excluded.concrete_grade,
                    reinforcement_steel_type = excluded.reinforcement_steel_type,
                    column_dimensions_cm = excluded.column_dimensions_cm,
                    floor_count_compliance = excluded.floor_count_compliance,
                    supervision_records = excluded.supervision_records,
                    structural_compliance_notes = excluded.structural_compliance_notes,
                    assessed_by = excluded.assessed_by,
                    assessed_at = CURRENT_TIMESTAMP
                """,
                {**structural_data, "building_id": building_id},
            )
            connection.execute(
                """
                INSERT INTO fire_assessments (
                    building_id, number_of_staircases, staircase_width_m, fire_exits,
                    fire_extinguishers, smoke_detectors, fire_alarms, sprinklers,
                    emergency_lighting, evacuation_route_notes, assessed_by
                )
                VALUES (
                    :building_id, :number_of_staircases, :staircase_width_m, :fire_exits,
                    :fire_extinguishers, :smoke_detectors, :fire_alarms, :sprinklers,
                    :emergency_lighting, :evacuation_route_notes, :assessed_by
                )
                ON CONFLICT(building_id) DO UPDATE SET
                    number_of_staircases = excluded.number_of_staircases,
                    staircase_width_m = excluded.staircase_width_m,
                    fire_exits = excluded.fire_exits,
                    fire_extinguishers = excluded.fire_extinguishers,
                    smoke_detectors = excluded.smoke_detectors,
                    fire_alarms = excluded.fire_alarms,
                    sprinklers = excluded.sprinklers,
                    emergency_lighting = excluded.emergency_lighting,
                    evacuation_route_notes = excluded.evacuation_route_notes,
                    assessed_by = excluded.assessed_by,
                    assessed_at = CURRENT_TIMESTAMP
                """,
                {**fire_data, "building_id": building_id},
            )
            connection.execute(
                """
                INSERT INTO compliance_records (
                    building_id, inspector_name, inspector_registration_number,
                    developer_name, developer_registration_number, approval_status,
                    uploaded_document_metadata, verification_status, review_notes, assessed_by
                )
                VALUES (
                    :building_id, :inspector_name, :inspector_registration_number,
                    :developer_name, :developer_registration_number, :approval_status,
                    :uploaded_document_metadata, :verification_status, :review_notes, :assessed_by
                )
                ON CONFLICT(building_id) DO UPDATE SET
                    inspector_name = excluded.inspector_name,
                    inspector_registration_number = excluded.inspector_registration_number,
                    developer_name = excluded.developer_name,
                    developer_registration_number = excluded.developer_registration_number,
                    approval_status = excluded.approval_status,
                    uploaded_document_metadata = excluded.uploaded_document_metadata,
                    verification_status = excluded.verification_status,
                    review_notes = excluded.review_notes,
                    assessed_by = excluded.assessed_by,
                    assessed_at = CURRENT_TIMESTAMP
                """,
                {**compliance_data, "building_id": building_id},
            )

            building = connection.execute("SELECT * FROM buildings WHERE id = ?", (building_id,)).fetchone()
            structural = connection.execute(
                "SELECT * FROM structural_assessments WHERE building_id = ?",
                (building_id,),
            ).fetchone()
            fire = connection.execute(
                "SELECT * FROM fire_assessments WHERE building_id = ?",
                (building_id,),
            ).fetchone()
            compliance = connection.execute(
                "SELECT * FROM compliance_records WHERE building_id = ?",
                (building_id,),
            ).fetchone()

            score = calculate_scores(building, structural, fire, compliance)
            save_score(connection, building_id, score.to_record())
        return building_id

    def get_dashboard_dataframe(self) -> pd.DataFrame:
        records = self.get_buildings()
        frame = pd.DataFrame(records)
        if frame.empty:
            return frame
        return frame.fillna("")

    def get_score_breakdown(self, building_id: int) -> tuple[pd.DataFrame, dict[str, Any]]:
        bundle = self.get_building_bundle(building_id)
        if not bundle or not bundle["score"]:
            return pd.DataFrame(), {}
        explanation = json.loads(bundle["score"]["explanation_json"])
        frame = pd.DataFrame(
            [
                {"Category": "Structural", "Score": bundle["score"]["structural_score"]},
                {"Category": "Fire", "Score": bundle["score"]["fire_score"]},
                {"Category": "Compliance", "Score": bundle["score"]["compliance_score"]},
            ]
        )
        return frame, explanation
