"""Projects page — Project lifecycle management."""

import json

import streamlit as st

from components.copy_button import copyable_output
import api_client

st.title(":material/folder: Projects")

STAGE_COLORS = {
    "planning": "#3B82F6",
    "executing": "#F59E0B",
    "reviewing": "#A855F7",
    "learning": "#22C55E",
    "complete": "#10B981",
    "archived": "#6B7280",
}

# --- Sidebar: Create Project ---
with st.sidebar:
    st.markdown("#### New Project")
    new_name = st.text_input("Project Name", key="new_proj_name")
    new_category = st.selectbox(
        "Category",
        ["content", "marketing", "sales", "product", "personal", "other"],
        key="new_proj_cat",
    )
    new_desc = st.text_area("Description (optional)", key="new_proj_desc", height=80)

    if st.button("Create Project", type="primary", disabled=not new_name):
        try:
            result = api_client.create_project(
                name=new_name,
                category=new_category,
                description=new_desc if new_desc else None,
            )
            st.success(f"Created: {new_name}")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to create project: {e}")

# --- Filters ---
col_filter1, col_filter2 = st.columns(2)
with col_filter1:
    stage_filter = st.selectbox(
        "Filter by Stage",
        ["All"] + list(STAGE_COLORS.keys()),
        key="proj_stage_filter",
    )
with col_filter2:
    cat_filter = st.text_input("Filter by Category", key="proj_cat_filter")

# --- Load Projects ---
try:
    filter_stage = stage_filter if stage_filter != "All" else None
    filter_cat = cat_filter if cat_filter else None
    projects_response = api_client.list_projects(
        lifecycle_stage=filter_stage,
        category=filter_cat,
    )

    # Handle response format — could be list or dict with items key
    if isinstance(projects_response, list):
        projects = projects_response
    elif isinstance(projects_response, dict):
        projects = projects_response.get("items", projects_response.get("projects", []))
    else:
        projects = []
except Exception as e:
    st.error(f"Failed to load projects: {e}")
    projects = []

if not projects:
    st.info("No projects found. Create one using the sidebar.")
else:
    st.caption(f"{len(projects)} project(s)")

    for proj in projects:
        proj_id = proj.get("id", "")
        name = proj.get("name", "Untitled")
        stage = proj.get("lifecycle_stage", "planning")
        category = proj.get("category", "")
        description = proj.get("description", "")
        created = proj.get("created_at", proj.get("date_created", ""))

        # Stage badge
        color = STAGE_COLORS.get(stage, "#6B7280")
        badge = (
            f'<span style="background-color:{color}22;color:{color};'
            f'padding:2px 8px;border-radius:8px;font-size:0.85em;font-weight:600;">'
            f"{stage}</span>"
        )

        with st.expander(f"{name}  {category}", expanded=False):
            st.markdown(badge, unsafe_allow_html=True)

            if description:
                st.markdown(description)

            col1, col2 = st.columns(2)
            with col1:
                st.caption(f"Category: {category}")
            with col2:
                if created:
                    # Show just the date portion
                    date_str = str(created)[:10] if created else ""
                    st.caption(f"Created: {date_str}")

            # Show full project data in expandable JSON
            with st.expander("Raw Data", expanded=False):
                copyable_output(proj)

            # Delete button
            if st.button(
                "Delete",
                key=f"del_{proj_id}",
                type="secondary",
            ):
                try:
                    api_client.delete_project(proj_id)
                    st.success(f"Deleted: {name}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to delete: {e}")
