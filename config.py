from __future__ import annotations

from pathlib import Path

APP_TITLE = "Residential Building Safety Ranking DSS"
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "safety_ranking.db"
SCHEMA_PATH = BASE_DIR / "sql" / "schema.sql"

DEFAULT_WEIGHTS = {
    "structural": 0.45,
    "fire": 0.35,
    "compliance": 0.20,
}

RISK_BANDS = (
    (80, "Low Risk"),
    (60, "Moderate Risk"),
    (40, "High Risk"),
    (0, "Critical Risk"),
)
