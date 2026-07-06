PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'inspector', 'developer')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS buildings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    building_name TEXT NOT NULL,
    location TEXT NOT NULL,
    number_of_floors INTEGER NOT NULL CHECK(number_of_floors > 0),
    year_of_construction INTEGER NOT NULL,
    intended_use TEXT NOT NULL,
    approved_design_details TEXT NOT NULL,
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS structural_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    building_id INTEGER NOT NULL UNIQUE,
    concrete_grade TEXT NOT NULL,
    reinforcement_steel_type TEXT NOT NULL,
    column_dimensions_cm REAL NOT NULL CHECK(column_dimensions_cm > 0),
    floor_count_compliance INTEGER NOT NULL CHECK(floor_count_compliance IN (0, 1)),
    supervision_records INTEGER NOT NULL CHECK(supervision_records IN (0, 1)),
    structural_compliance_notes TEXT NOT NULL,
    assessed_by INTEGER,
    assessed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(building_id) REFERENCES buildings(id) ON DELETE CASCADE,
    FOREIGN KEY(assessed_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS fire_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    building_id INTEGER NOT NULL UNIQUE,
    number_of_staircases INTEGER NOT NULL CHECK(number_of_staircases >= 0),
    staircase_width_m REAL NOT NULL CHECK(staircase_width_m >= 0),
    fire_exits INTEGER NOT NULL CHECK(fire_exits >= 0),
    fire_extinguishers INTEGER NOT NULL CHECK(fire_extinguishers >= 0),
    smoke_detectors INTEGER NOT NULL CHECK(smoke_detectors >= 0),
    fire_alarms INTEGER NOT NULL CHECK(fire_alarms IN (0, 1)),
    sprinklers INTEGER NOT NULL CHECK(sprinklers IN (0, 1)),
    emergency_lighting INTEGER NOT NULL CHECK(emergency_lighting IN (0, 1)),
    evacuation_route_notes TEXT NOT NULL,
    assessed_by INTEGER,
    assessed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(building_id) REFERENCES buildings(id) ON DELETE CASCADE,
    FOREIGN KEY(assessed_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS compliance_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    building_id INTEGER NOT NULL UNIQUE,
    inspector_name TEXT NOT NULL,
    inspector_registration_number TEXT NOT NULL,
    developer_name TEXT NOT NULL,
    developer_registration_number TEXT NOT NULL,
    approval_status TEXT NOT NULL CHECK(approval_status IN ('Approved', 'Conditional', 'Pending', 'Rejected')),
    uploaded_document_metadata TEXT NOT NULL,
    verification_status TEXT NOT NULL CHECK(verification_status IN ('Verified', 'Partially Verified', 'Unverified')),
    review_notes TEXT NOT NULL,
    assessed_by INTEGER,
    assessed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(building_id) REFERENCES buildings(id) ON DELETE CASCADE,
    FOREIGN KEY(assessed_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    building_id INTEGER NOT NULL UNIQUE,
    structural_score REAL NOT NULL,
    fire_score REAL NOT NULL,
    compliance_score REAL NOT NULL,
    overall_score REAL NOT NULL,
    risk_category TEXT NOT NULL,
    explanation_json TEXT NOT NULL,
    computed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(building_id) REFERENCES buildings(id) ON DELETE CASCADE
);
