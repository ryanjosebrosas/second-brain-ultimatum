"""Chart helper functions for the health dashboard.

Wraps Streamlit widgets with consistent styling for metrics,
progress bars, badges, checklists, and charts.
"""

from typing import Any

import pandas as pd
import streamlit as st


def metric_card(
    label: str,
    value: int | float | str,
    delta: int | float | str | None = None,
    help_text: str | None = None,
) -> None:
    """Styled st.metric wrapper."""
    st.metric(label=label, value=value, delta=delta, help=help_text)


def progress_bar(label: str, current: int, total: int) -> None:
    """Labeled progress bar."""
    pct = current / total if total > 0 else 0
    st.markdown(f"**{label}**: {current} / {total}")
    st.progress(min(pct, 1.0))


def _render_badge(text: str) -> None:
    """Render a badge using Streamlit-native caption with bold text."""
    st.caption(f"**{text}**")


def brain_level_badge(level: str) -> None:
    """Badge for brain level."""
    _render_badge(level)


def setup_checklist(setup_data: dict[str, Any]) -> None:
    """Render setup steps as a checklist.

    setup_data keys: is_complete, steps (list of step dicts),
    completed_count, total_steps, missing_categories, total_memory_entries.
    """
    steps = setup_data.get("steps", [])
    completed = setup_data.get("completed_count", 0)
    total = setup_data.get("total_steps", len(steps))

    progress_bar("Setup Progress", completed, total)

    if setup_data.get("is_complete"):
        st.success("Setup complete!")
    else:
        st.info(f"{total - completed} steps remaining")

    for step in steps:
        icon = ":material/check_circle:" if step.get("completed") else ":material/radio_button_unchecked:"
        desc = step.get("description", step.get("name", ""))
        st.markdown(f"{icon} {desc}")

    mem_entries = setup_data.get("total_memory_entries", 0)
    if mem_entries:
        st.caption(f"Total memory entries: {mem_entries}")


def quality_trend_chart(quality_data: dict[str, Any]) -> None:
    """Line chart from /health/quality response."""
    dimensions = quality_data.get("by_dimension", [])
    if not dimensions:
        st.info("No quality data yet. Review some content to see trends.")
        return

    df = pd.DataFrame(dimensions)
    if "dimension" in df.columns and "avg_score" in df.columns:
        chart_df = df.set_index("dimension")[["avg_score"]]
        st.bar_chart(chart_df)

    total = quality_data.get("total_reviews", 0)
    avg = quality_data.get("avg_score", 0)
    trend = quality_data.get("score_trend", "stable")
    st.caption(f"{total} reviews | Avg: {avg:.1f} | Trend: {trend}")


def dimension_breakdown(quality_data: dict[str, Any]) -> None:
    """Per-dimension score breakdown with progress bars."""
    dimensions = quality_data.get("by_dimension", [])
    if not dimensions:
        st.info("No dimension data available.")
        return

    for row in dimensions:
        dim = row.get("dimension", "")
        score = row.get("avg_score", 0)
        count = row.get("review_count", 0)
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{dim}**")
            st.progress(min(score / 10.0, 1.0))
        with col2:
            st.metric(label="Score", value=f"{score:.1f}/10", label_visibility="collapsed")
            st.caption(f"{count} reviews")


def graph_status_card(health_data: dict[str, Any]) -> None:
    """Display graphiti_status, graphiti_backend, and graph_provider."""
    status = health_data.get("graphiti_status", "disabled")
    backend = health_data.get("graphiti_backend", "none")
    provider = health_data.get("graph_provider", "disabled")

    st.markdown("#### Knowledge Graph")
    _render_badge(status.upper())
    col1, col2 = st.columns(2)
    with col1:
        st.caption(f"Provider: {provider}")
    with col2:
        st.caption(f"Backend: {backend}")
