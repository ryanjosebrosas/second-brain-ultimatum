"""Dashboard page — Brain health metrics and growth tracking."""

import logging

import streamlit as st

from api_client import get_health, get_milestones, get_growth, get_quality, get_setup
from components.charts import (
    metric_card,
    progress_bar,
    brain_level_badge,
    setup_checklist,
    quality_trend_chart,
    dimension_breakdown,
    graph_status_card,
)

logger = logging.getLogger(__name__)


@st.cache_data(ttl=60)
def _cached_get_health() -> dict:
    return get_health()


@st.cache_data(ttl=60)
def _cached_get_milestones() -> dict:
    return get_milestones()


@st.cache_data(ttl=60)
def _cached_get_growth() -> dict:
    return get_growth()


@st.cache_data(ttl=60)
def _cached_get_quality() -> dict:
    return get_quality()


@st.cache_data(ttl=300)
def _cached_get_setup() -> dict:
    return get_setup()


st.title(":material/dashboard: Dashboard")

tab_overview, tab_growth, tab_quality, tab_setup = st.tabs(
    ["Overview", "Growth", "Quality", "Setup"]
)

# --- Overview Tab ---
with tab_overview:
    try:
        health = _cached_get_health()
    except Exception:
        logger.exception("Failed to load health metrics")
        st.error("Failed to load health metrics. Please try again.")
        health = {}

    if health:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            metric_card("Memories", health.get("memory_count", 0))
        with col2:
            metric_card("Patterns", health.get("total_patterns", 0))
        with col3:
            metric_card("Experiences", health.get("experience_count", 0))
        with col4:
            metric_card("Status", health.get("status", "BUILDING"))

        st.divider()

        col1, col2, col3 = st.columns(3)
        with col1:
            metric_card(
                "HIGH Confidence",
                health.get("high_confidence", 0),
                help_text="Patterns with HIGH confidence level",
            )
        with col2:
            metric_card(
                "MEDIUM Confidence",
                health.get("medium_confidence", 0),
                help_text="Patterns with MEDIUM confidence level",
            )
        with col3:
            metric_card(
                "LOW Confidence",
                health.get("low_confidence", 0),
                help_text="Patterns with LOW confidence level",
            )

        st.divider()

        # Topics breakdown
        topics = health.get("topics", {})
        if topics:
            st.markdown("#### Topics")
            topic_cols = st.columns(min(len(topics), 4))
            for i, (topic, count) in enumerate(topics.items()):
                with topic_cols[i % len(topic_cols)]:
                    metric_card(topic, count)

        st.divider()

        # Graph status
        graph_status_card(health)

        # Errors
        errors = health.get("errors", [])
        if errors:
            st.divider()
            st.markdown("#### Errors")
            for err in errors:
                st.warning(err)

    # Milestones section
    st.divider()
    st.markdown("#### Brain Level & Milestones")
    try:
        milestones = _cached_get_milestones()
    except Exception:
        logger.exception("Failed to load milestones")
        st.error("Failed to load milestones. Please try again.")
        milestones = {}

    if milestones:
        brain_level_badge(milestones.get("level", "EMPTY"))
        st.caption(milestones.get("level_description", ""))

        col1, col2, col3 = st.columns(3)
        with col1:
            metric_card("Patterns", milestones.get("patterns_total", 0))
        with col2:
            metric_card("HIGH Patterns", milestones.get("high_confidence_count", 0))
        with col3:
            metric_card("Avg Review", milestones.get("avg_review_score", 0))

        progress_bar(
            "Milestones",
            milestones.get("milestones_completed", 0),
            milestones.get("milestones_total", 0),
        )

        next_m = milestones.get("next_milestone")
        if next_m:
            st.info(f"Next milestone: {next_m}")

        milestone_list = milestones.get("milestones", [])
        if milestone_list:
            with st.expander("All Milestones", expanded=False):
                for m in milestone_list:
                    icon = ":material/check_circle:" if m.get("completed") else ":material/radio_button_unchecked:"
                    name = m.get("name", "")
                    desc = m.get("description", "")
                    st.markdown(f"{icon} **{name}**")
                    if desc:
                        st.caption(desc)


# --- Growth Tab ---
with tab_growth:
    try:
        growth = _cached_get_growth()
    except Exception:
        logger.exception("Failed to load growth data")
        st.error("Failed to load growth data. Please try again.")
        growth = {}

    if growth:
        col1, col2, col3 = st.columns(3)
        with col1:
            metric_card("Growth Events", growth.get("growth_events_total", 0))
        with col2:
            metric_card("Avg Review Score", growth.get("avg_review_score", 0))
        with col3:
            metric_card("Score Trend", growth.get("review_score_trend", "stable"))

        st.divider()
        st.markdown("#### Activity Breakdown (Last 30 Days)")

        col1, col2 = st.columns(2)
        with col1:
            metric_card("Patterns Created", growth.get("patterns_created_period", 0))
            metric_card("Patterns Reinforced", growth.get("patterns_reinforced_period", 0))
            metric_card("Confidence Upgrades", growth.get("confidence_upgrades_period", 0))
        with col2:
            metric_card("Experiences Recorded", growth.get("experiences_recorded_period", 0))
            metric_card("Reviews Completed", growth.get("reviews_completed_period", 0))

        # Stale patterns
        stale = growth.get("stale_patterns", [])
        if stale:
            st.divider()
            st.markdown("#### Stale Patterns")
            st.caption("Not reinforced in 30+ days and below HIGH confidence")
            for name in stale:
                st.text(f"  \u2022 {name}")


# --- Quality Tab ---
with tab_quality:
    try:
        quality = _cached_get_quality()
    except Exception:
        logger.exception("Failed to load quality data")
        st.error("Failed to load quality data. Please try again.")
        quality = {}

    if quality:
        col1, col2, col3 = st.columns(3)
        with col1:
            metric_card("Total Reviews", quality.get("total_reviews", 0))
        with col2:
            metric_card("Avg Score", f"{quality.get('avg_score', 0):.1f}")
        with col3:
            metric_card("Trend", quality.get("score_trend", "stable"))

        st.divider()
        st.markdown("#### Score Distribution by Dimension")
        dimension_breakdown(quality)

        st.divider()
        st.markdown("#### Quality Trend")
        quality_trend_chart(quality)

        # Content type breakdown
        by_type = quality.get("by_content_type", {})
        if by_type:
            st.divider()
            st.markdown("#### By Content Type")
            for ct, data in by_type.items():
                st.text(f"{ct}: {data}")

        # Recurring issues
        issues = quality.get("recurring_issues", [])
        if issues:
            st.divider()
            st.markdown("#### Recurring Issues")
            for issue in issues:
                st.warning(issue)

        col1, col2 = st.columns(2)
        with col1:
            metric_card("Excellence", quality.get("excellence_count", 0), help_text="Reviews scoring 8+")
        with col2:
            metric_card("Needs Work", quality.get("needs_work_count", 0), help_text="Reviews scoring below 5")


# --- Setup Tab ---
with tab_setup:
    try:
        setup = _cached_get_setup()
    except Exception:
        logger.exception("Failed to load setup status")
        st.error("Failed to load setup status. Please try again.")
        setup = {}

    if setup:
        setup_checklist(setup)

        missing = setup.get("missing_categories", [])
        if missing:
            st.divider()
            st.markdown("#### Missing Categories")
            for cat in missing:
                st.markdown(f"- {cat}")
