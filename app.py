from __future__ import annotations

import json
from datetime import date
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from src.auth import build_session_user
from src.config import APP_TITLE
from src.database import initialize_database
from src.repository import SafetyRepository


repository = SafetyRepository()


def init_app() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon=":office_building:", layout="wide")
    initialize_database(seed=True)
    if "user" not in st.session_state:
        st.session_state.user = None


def login_view() -> None:
    st.title(APP_TITLE)
    st.caption("Prototype decision-support system for safety ranking of residential multi-storey buildings.")
    st.info("Demo accounts: admin / admin123, inspector1 / inspect123, developer1 / develop123")

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign In", use_container_width=True)

    if submitted:
        user = repository.authenticate_user(username.strip(), password)
        if user:
            st.session_state.user = build_session_user(user)
            st.success("Login successful.")
            st.rerun()
        st.error("Invalid username or password.")


def logout_button() -> None:
    if st.sidebar.button("Sign Out", use_container_width=True):
        st.session_state.user = None
        st.rerun()


def sidebar_navigation() -> str:
    user = st.session_state.user
    st.sidebar.title("Navigation")
    st.sidebar.write(f"Signed in as **{user['full_name']}**")
    st.sidebar.write(f"Role: `{user['role']}`")
    page = st.sidebar.radio(
        "Go to",
        ["Dashboard", "Register / Edit Building", "Building Detail", "Users"],
    )
    logout_button()
    return page


def dashboard_view() -> None:
    st.title("Safety Dashboard")
    frame = repository.get_dashboard_dataframe()
    if frame.empty:
        st.warning("No buildings have been captured yet.")
        return

    numeric_scores = pd.to_numeric(frame["overall_score"], errors="coerce").fillna(0)
    total_buildings = len(frame)
    average_score = round(float(numeric_scores.mean()), 2)
    low_risk_count = int((frame["risk_category"] == "Low Risk").sum())

    col1, col2, col3 = st.columns(3)
    col1.metric("Registered Buildings", total_buildings)
    col2.metric("Average Safety Score", average_score)
    col3.metric("Low Risk Buildings", low_risk_count)

    ranking_columns = [
        "building_name",
        "location",
        "number_of_floors",
        "overall_score",
        "risk_category",
        "structural_score",
        "fire_score",
        "compliance_score",
    ]
    ranking_frame = frame[ranking_columns].copy()
    ranking_frame.index = ranking_frame.index + 1
    st.subheader("Building Ranking")
    st.dataframe(ranking_frame, use_container_width=True)

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        risk_chart = px.histogram(
            frame,
            x="risk_category",
            color="risk_category",
            title="Risk Category Distribution",
        )
        st.plotly_chart(risk_chart, use_container_width=True)
    with chart_col2:
        score_chart = px.bar(
            frame.sort_values(by="overall_score", ascending=False),
            x="building_name",
            y="overall_score",
            color="risk_category",
            title="Overall Score by Building",
        )
        st.plotly_chart(score_chart, use_container_width=True)

    csv_bytes = ranking_frame.to_csv(index=True).encode("utf-8")
    st.download_button(
        "Download Ranking CSV",
        csv_bytes,
        file_name="building_safety_ranking.csv",
        mime="text/csv",
    )


def user_role_can_manage() -> bool:
    return st.session_state.user["role"] in {"admin", "inspector", "developer"}


def validate_building_form(building_data: dict[str, Any], compliance_data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    current_year = date.today().year
    if not building_data["building_name"].strip():
        errors.append("Building name is required.")
    if not building_data["location"].strip():
        errors.append("Location is required.")
    if not (1 <= int(building_data["number_of_floors"]) <= 100):
        errors.append("Number of floors must be between 1 and 100.")
    if not (1950 <= int(building_data["year_of_construction"]) <= current_year):
        errors.append(f"Year of construction must be between 1950 and {current_year}.")
    if not compliance_data["inspector_name"].strip():
        errors.append("Inspector name is required.")
    return errors


def register_edit_view() -> None:
    st.title("Register or Edit Building")
    if not user_role_can_manage():
        st.error("Your role does not have permission to manage building records.")
        return

    buildings = repository.get_buildings()
    building_options = {"Create New": None}
    for building in buildings:
        building_options[f"{building['building_name']} ({building['location']})"] = building["id"]
    selected_label = st.selectbox("Select record to edit", list(building_options.keys()))
    selected_id = building_options[selected_label]
    bundle = repository.get_building_bundle(selected_id) if selected_id else None

    defaults = bundle or {
        "building": {
            "building_name": "",
            "location": "",
            "number_of_floors": 1,
            "year_of_construction": 2020,
            "intended_use": "Residential Apartments",
            "approved_design_details": "",
        },
        "structural": {
            "concrete_grade": "C25",
            "reinforcement_steel_type": "TMT",
            "column_dimensions_cm": 25.0,
            "floor_count_compliance": 1,
            "supervision_records": 1,
            "structural_compliance_notes": "",
        },
        "fire": {
            "number_of_staircases": 1,
            "staircase_width_m": 1.0,
            "fire_exits": 1,
            "fire_extinguishers": 2,
            "smoke_detectors": 4,
            "fire_alarms": 1,
            "sprinklers": 0,
            "emergency_lighting": 1,
            "evacuation_route_notes": "",
        },
        "compliance": {
            "inspector_name": st.session_state.user["full_name"],
            "inspector_registration_number": "",
            "developer_name": "",
            "developer_registration_number": "",
            "approval_status": "Pending",
            "uploaded_document_metadata": "",
            "verification_status": "Unverified",
            "review_notes": "",
        },
    }

    concrete_options = ["C15", "C20", "C25", "C30", "C35"]
    steel_options = ["Mild", "Y12", "Y16", "High Tensile", "TMT"]
    approval_options = ["Approved", "Conditional", "Pending", "Rejected"]
    verification_options = ["Verified", "Partially Verified", "Unverified"]

    with st.form("building_form", clear_on_submit=False):
        st.subheader("Building Profile")
        col1, col2 = st.columns(2)
        with col1:
            building_name = st.text_input("Building name", value=defaults["building"]["building_name"])
            location = st.text_input("Location", value=defaults["building"]["location"])
            number_of_floors = st.number_input(
                "Number of floors",
                min_value=1,
                max_value=100,
                value=int(defaults["building"]["number_of_floors"]),
            )
        with col2:
            year_of_construction = st.number_input(
                "Year of construction",
                min_value=1950,
                max_value=date.today().year,
                value=int(defaults["building"]["year_of_construction"]),
            )
            intended_use = st.text_input("Intended use", value=defaults["building"]["intended_use"])
            approved_design_details = st.text_area(
                "Approved design details",
                value=defaults["building"]["approved_design_details"],
                height=100,
            )

        st.subheader("Structural Safety")
        col1, col2 = st.columns(2)
        with col1:
            concrete_grade = st.selectbox(
                "Concrete grade",
                concrete_options,
                index=concrete_options.index(defaults["structural"]["concrete_grade"]),
            )
            reinforcement_steel_type = st.selectbox(
                "Reinforcement steel type",
                steel_options,
                index=steel_options.index(defaults["structural"]["reinforcement_steel_type"]),
            )
            column_dimensions_cm = st.number_input(
                "Average column dimension (cm)",
                min_value=10.0,
                max_value=100.0,
                value=float(defaults["structural"]["column_dimensions_cm"]),
                step=0.5,
            )
        with col2:
            floor_count_compliance = st.checkbox(
                "Floor count compliant with approved design",
                value=bool(defaults["structural"]["floor_count_compliance"]),
            )
            supervision_records = st.checkbox(
                "Supervision records available",
                value=bool(defaults["structural"]["supervision_records"]),
            )
            structural_compliance_notes = st.text_area(
                "Structural compliance notes",
                value=defaults["structural"]["structural_compliance_notes"],
                height=100,
            )

        st.subheader("Fire Safety")
        col1, col2, col3 = st.columns(3)
        with col1:
            number_of_staircases = st.number_input(
                "Number of staircases",
                min_value=0,
                value=int(defaults["fire"]["number_of_staircases"]),
            )
            staircase_width_m = st.number_input(
                "Staircase width (m)",
                min_value=0.0,
                max_value=5.0,
                value=float(defaults["fire"]["staircase_width_m"]),
                step=0.1,
            )
            fire_exits = st.number_input("Fire exits", min_value=0, value=int(defaults["fire"]["fire_exits"]))
        with col2:
            fire_extinguishers = st.number_input(
                "Fire extinguishers",
                min_value=0,
                value=int(defaults["fire"]["fire_extinguishers"]),
            )
            smoke_detectors = st.number_input(
                "Smoke detectors",
                min_value=0,
                value=int(defaults["fire"]["smoke_detectors"]),
            )
            fire_alarms = st.checkbox("Fire alarms installed", value=bool(defaults["fire"]["fire_alarms"]))
        with col3:
            sprinklers = st.checkbox("Sprinklers installed", value=bool(defaults["fire"]["sprinklers"]))
            emergency_lighting = st.checkbox(
                "Emergency lighting available",
                value=bool(defaults["fire"]["emergency_lighting"]),
            )
            evacuation_route_notes = st.text_area(
                "Evacuation route notes",
                value=defaults["fire"]["evacuation_route_notes"],
                height=100,
            )

        st.subheader("Compliance and Credentials")
        col1, col2 = st.columns(2)
        with col1:
            inspector_name = st.text_input("Inspector name", value=defaults["compliance"]["inspector_name"])
            inspector_registration_number = st.text_input(
                "Inspector registration number",
                value=defaults["compliance"]["inspector_registration_number"],
            )
            developer_name = st.text_input("Developer name", value=defaults["compliance"]["developer_name"])
            developer_registration_number = st.text_input(
                "Developer registration number",
                value=defaults["compliance"]["developer_registration_number"],
            )
        with col2:
            approval_status = st.selectbox(
                "Approval status",
                approval_options,
                index=approval_options.index(defaults["compliance"]["approval_status"]),
            )
            verification_status = st.selectbox(
                "Verification status",
                verification_options,
                index=verification_options.index(defaults["compliance"]["verification_status"]),
            )
            uploaded_document_metadata = st.text_area(
                "Uploaded document metadata",
                value=defaults["compliance"]["uploaded_document_metadata"],
                help="Enter document names separated by commas.",
                height=100,
            )
            review_notes = st.text_area("Review notes", value=defaults["compliance"]["review_notes"], height=100)

        submitted = st.form_submit_button("Save Assessment", use_container_width=True)

    if submitted:
        building_data = {
            "building_name": building_name,
            "location": location,
            "number_of_floors": int(number_of_floors),
            "year_of_construction": int(year_of_construction),
            "intended_use": intended_use,
            "approved_design_details": approved_design_details,
            "created_by": st.session_state.user["id"],
        }
        structural_data = {
            "concrete_grade": concrete_grade,
            "reinforcement_steel_type": reinforcement_steel_type,
            "column_dimensions_cm": float(column_dimensions_cm),
            "floor_count_compliance": int(floor_count_compliance),
            "supervision_records": int(supervision_records),
            "structural_compliance_notes": structural_compliance_notes,
            "assessed_by": st.session_state.user["id"],
        }
        fire_data = {
            "number_of_staircases": int(number_of_staircases),
            "staircase_width_m": float(staircase_width_m),
            "fire_exits": int(fire_exits),
            "fire_extinguishers": int(fire_extinguishers),
            "smoke_detectors": int(smoke_detectors),
            "fire_alarms": int(fire_alarms),
            "sprinklers": int(sprinklers),
            "emergency_lighting": int(emergency_lighting),
            "evacuation_route_notes": evacuation_route_notes,
            "assessed_by": st.session_state.user["id"],
        }
        compliance_data = {
            "inspector_name": inspector_name,
            "inspector_registration_number": inspector_registration_number,
            "developer_name": developer_name,
            "developer_registration_number": developer_registration_number,
            "approval_status": approval_status,
            "uploaded_document_metadata": uploaded_document_metadata,
            "verification_status": verification_status,
            "review_notes": review_notes,
            "assessed_by": st.session_state.user["id"],
        }

        errors = validate_building_form(building_data, compliance_data)
        if errors:
            for error in errors:
                st.error(error)
            return

        saved_id = repository.upsert_building_bundle(
            building_data,
            structural_data,
            fire_data,
            compliance_data,
            building_id=selected_id,
        )
        st.success(f"Building record saved successfully. Building ID: {saved_id}")
        st.rerun()


def building_detail_view() -> None:
    st.title("Building Detail")
    buildings = repository.get_buildings()
    if not buildings:
        st.warning("No building records found.")
        return

    selected_id = st.selectbox(
        "Select building",
        options=[building["id"] for building in buildings],
        format_func=lambda building_id: next(
            f"{item['building_name']} ({item['location']})" for item in buildings if item["id"] == building_id
        ),
    )
    bundle = repository.get_building_bundle(selected_id)
    if not bundle:
        st.error("Unable to load building details.")
        return

    building = bundle["building"]
    structural = bundle["structural"]
    fire = bundle["fire"]
    compliance = bundle["compliance"]
    score = bundle["score"]

    st.subheader(building["building_name"])
    col1, col2, col3 = st.columns(3)
    col1.metric("Overall Score", score["overall_score"])
    col2.metric("Risk Category", score["risk_category"])
    col3.metric("Computed At", score["computed_at"])

    profile_frame = pd.DataFrame(
        {
            "Field": [
                "Location",
                "Number of floors",
                "Year of construction",
                "Intended use",
                "Approved design details",
            ],
            "Value": [
                building["location"],
                building["number_of_floors"],
                building["year_of_construction"],
                building["intended_use"],
                building["approved_design_details"],
            ],
        }
    )
    st.dataframe(profile_frame, use_container_width=True, hide_index=True)

    breakdown_frame, explanation = repository.get_score_breakdown(selected_id)
    st.subheader("Score Breakdown")
    breakdown_chart = px.bar(breakdown_frame, x="Category", y="Score", color="Category", range_y=[0, 100])
    st.plotly_chart(breakdown_chart, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Structural Assessment**")
        st.json(structural)
    with col2:
        st.markdown("**Fire Assessment**")
        st.json(fire)
    with col3:
        st.markdown("**Compliance Record**")
        st.json(compliance)

    st.subheader("Transparent Scoring Explanation")
    st.caption("The prototype uses a simplified compliance-based model for decision support, not engineering certification.")
    st.write(explanation["formula"])
    st.write("Weights:", explanation["weights"])

    component_tabs = st.tabs(["Structural", "Fire", "Compliance"])
    component_tabs[0].dataframe(
        pd.DataFrame(explanation["structural_components"].items(), columns=["Indicator", "Normalized Score"]),
        use_container_width=True,
        hide_index=True,
    )
    component_tabs[1].dataframe(
        pd.DataFrame(explanation["fire_components"].items(), columns=["Indicator", "Normalized Score"]),
        use_container_width=True,
        hide_index=True,
    )
    component_tabs[2].dataframe(
        pd.DataFrame(explanation["compliance_components"].items(), columns=["Indicator", "Normalized Score"]),
        use_container_width=True,
        hide_index=True,
    )

    summary_report = {
        "building": building,
        "score": score,
        "structural": structural,
        "fire": fire,
        "compliance": compliance,
        "explanation": explanation,
    }
    st.download_button(
        "Download Summary Report (JSON)",
        data=json.dumps(summary_report, indent=2).encode("utf-8"),
        file_name=f"building_{building['id']}_summary_report.json",
        mime="application/json",
    )


def users_view() -> None:
    st.title("User Management Overview")
    if st.session_state.user["role"] != "admin":
        st.info("Only administrators can view the full user directory.")
        return

    users = repository.get_users()
    st.dataframe(pd.DataFrame(users), use_container_width=True, hide_index=True)


def main() -> None:
    init_app()
    if not st.session_state.user:
        login_view()
        return

    page = sidebar_navigation()
    if page == "Dashboard":
        dashboard_view()
    elif page == "Register / Edit Building":
        register_edit_view()
    elif page == "Building Detail":
        building_detail_view()
    elif page == "Users":
        users_view()


if __name__ == "__main__":
    main()
