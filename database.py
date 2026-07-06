from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from src.config import DATA_DIR, DATABASE_PATH, SCHEMA_PATH
from src.sample_data import SEED_BUILDINGS, SEED_USERS
from src.scoring import calculate_scores


def dict_factory(cursor: sqlite3.Cursor, row: tuple[Any, ...]) -> dict[str, Any]:
    return {column[0]: row[index] for index, column in enumerate(cursor.description)}


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_connection(db_path: Path = DATABASE_PATH) -> sqlite3.Connection:
    ensure_data_dir()
    connection = sqlite3.connect(db_path)
    connection.row_factory = dict_factory
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def db_session() -> Iterator[sqlite3.Connection]:
    connection = get_connection()
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def initialize_database(seed: bool = True) -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with db_session() as connection:
        connection.executescript(schema_sql)
        user_count = connection.execute("SELECT COUNT(*) AS total FROM users").fetchone()["total"]
        if seed and user_count == 0:
            seed_database(connection)


def seed_database(connection: sqlite3.Connection) -> None:
    for user in SEED_USERS:
        connection.execute(
            """
            INSERT INTO users (username, full_name, password_hash, role)
            VALUES (:username, :full_name, :password_hash, :role)
            """,
            user,
        )

    for record in SEED_BUILDINGS:
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
            record["building"],
        )
        building_id = cursor.lastrowid

        structural = {**record["structural"], "building_id": building_id}
        fire = {**record["fire"], "building_id": building_id}
        compliance = {**record["compliance"], "building_id": building_id}

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
            """,
            structural,
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
            """,
            fire,
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
            """,
            compliance,
        )

        building = connection.execute("SELECT * FROM buildings WHERE id = ?", (building_id,)).fetchone()
        score = calculate_scores(building, structural, fire, compliance)
        save_score(connection, building_id, score.to_record())


def save_score(connection: sqlite3.Connection, building_id: int, score_record: dict[str, Any]) -> None:
    connection.execute(
        """
        INSERT INTO scores (
            building_id, structural_score, fire_score, compliance_score,
            overall_score, risk_category, explanation_json
        )
        VALUES (
            :building_id, :structural_score, :fire_score, :compliance_score,
            :overall_score, :risk_category, :explanation_json
        )
        ON CONFLICT(building_id) DO UPDATE SET
            structural_score = excluded.structural_score,
            fire_score = excluded.fire_score,
            compliance_score = excluded.compliance_score,
            overall_score = excluded.overall_score,
            risk_category = excluded.risk_category,
            explanation_json = excluded.explanation_json,
            computed_at = CURRENT_TIMESTAMP
        """,
        {**score_record, "building_id": building_id},
    )
