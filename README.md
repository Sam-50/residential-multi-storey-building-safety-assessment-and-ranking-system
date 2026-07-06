# Web-Based Decision Support System for Safety Ranking of Residential Multi-Storey Buildings

This project is a modular Python prototype for a final-year computer science project. It captures structural safety, fire safety, and compliance data for residential multi-storey buildings, computes transparent weighted safety scores, and visualizes the ranking through a Streamlit dashboard.

Important note: this is a decision-support system for comparative assessment. It is not a structural engineering certification or simulation tool.

## Proposed Folder Structure

```text
Playground/
|-- app.py
|-- requirements.txt
|-- README.md
|-- data/
|   `-- safety_ranking.db
|-- sql/
|   `-- schema.sql
`-- src/
    |-- __init__.py
    |-- auth.py
    |-- config.py
    |-- database.py
    |-- repository.py
    |-- sample_data.py
    `-- scoring.py
```

## Architecture Summary

- `app.py`: Streamlit interface, navigation, authentication flow, forms, dashboards, and downloads.
- `src/database.py`: SQLite initialization, schema loading, seed execution, and score persistence.
- `src/repository.py`: application data access layer for authentication, CRUD operations, and reporting queries.
- `src/scoring.py`: isolated scoring engine with normalization, weighting, risk banding, and explanation output.
- `src/sample_data.py`: demo users and sample building assessments.
- `sql/schema.sql`: explicit relational schema for the prototype database.

## Database Schema

The system uses these main tables:

- `users`: stores local authentication credentials and user roles.
- `buildings`: stores core building registration and profile information.
- `structural_assessments`: stores simplified structural safety indicators.
- `fire_assessments`: stores fire preparedness and evacuation indicators.
- `compliance_records`: stores inspector, approval, and verification details.
- `scores`: stores computed subscores, overall score, risk category, and transparent explanation JSON.

The full schema is available in [sql/schema.sql](/C:/Users/HP/Documents/Playground/sql/schema.sql).

## Scoring Model

The prototype uses a simple weighted model:

- Structural safety: 45%
- Fire safety: 35%
- Compliance and credentials: 20%

Risk categories:

- 80 to 100: Low Risk
- 60 to 79: Moderate Risk
- 40 to 59: High Risk
- Below 40: Critical Risk

The scoring engine is intentionally modular so the weightings and indicator mappings can be changed later in [src/scoring.py](/C:/Users/HP/Documents/Playground/src/scoring.py).

## Seed Data

The app automatically seeds demo data on first run:

- Users
  - `admin / admin123`
  - `inspector1 / inspect123`
  - `developer1 / develop123`
- Buildings
  - `Sunrise Residency`
  - `Greenview Flats`
  - `Hillside Court`

## Setup Instructions

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the application:

```bash
streamlit run app.py
```

4. Open the local Streamlit URL shown in the terminal, typically `http://localhost:8501`.

On first launch, the SQLite database will be created automatically in `data/safety_ranking.db`.

## Main Features Implemented

- Local authentication with roles: `admin`, `inspector`, `developer`
- Building registration and editing
- Structural, fire, and compliance data capture
- Persistent SQLite storage
- Automatic score recomputation whenever assessments are saved
- Dashboard with ranking table and risk distribution charts
- Individual building detail page with transparent scoring explanation
- Downloadable ranking CSV and JSON summary report
- Seeded sample dataset for demonstrations

## Design Decisions

- SQLite was chosen to keep setup simple and fully local for prototype evaluation.
- Streamlit was used because it supports rapid development of forms, dashboards, and demo-ready interfaces.
- The repository pattern keeps database queries out of the UI layer.
- The scoring engine is separated into its own module to make future calibration easy.
- Compliance-based indicators were used instead of simulation so the system remains practical and understandable for an undergraduate project.

## Assumptions

- This prototype stores uploaded document metadata as text entries rather than full file storage.
- Assessment tables keep one current record per building for simplicity.
- Passwords use SHA-256 hashing for a lightweight prototype, not enterprise-grade identity management.
- The system compares buildings using simplified indicators and should support inspection prioritization rather than legal approval.

## Future Improvements

- Add true document upload and file storage.
- Add audit trails and assessment history per building.
- Add password reset, user creation, and stricter authorization controls.
- Add geospatial mapping of buildings.
- Add configurable scoring weights through an admin settings page.
- Add PDF report generation.
- Add REST API endpoints and migrate to PostgreSQL for multi-user deployment.
- Add more detailed compliance rules aligned with local building and fire codes.
