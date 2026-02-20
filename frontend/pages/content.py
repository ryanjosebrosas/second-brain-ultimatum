"""Content page — Content creation studio with type selector and review."""

import html
import logging
from typing import Any

import streamlit as st

from components.copy_button import copyable_text, copyable_output
import api_client

logger = logging.getLogger(__name__)

_VERDICT_ICONS: dict[str, str] = {
    "READY TO SEND": ":material/check_circle:",
    "NEEDS REVISION": ":material/warning:",
    "MAJOR REWORK": ":material/error:",
}

_STATUS_ICONS: dict[str, str] = {
    "pass": ":material/check_circle:",
    "warning": ":material/warning:",
    "issue": ":material/error:",
}

st.title(":material/edit: Content Studio")

tab_create, tab_review = st.tabs(["Create", "Review"])


@st.cache_data(ttl=300)
def _get_cached_content_types() -> dict[str, Any]:
    """Fetch content types with 5-minute cache to avoid API calls on every rerun."""
    ct_response = api_client.get_content_types()
    if isinstance(ct_response, list):
        return {ct.get("slug", ct.get("name", "unknown")): ct for ct in ct_response}
    elif isinstance(ct_response, dict):
        return ct_response
    return {}


# --- Load content types ---
try:
    content_types: dict[str, Any] = _get_cached_content_types()
except Exception:
    logger.exception("Failed to load content types")
    st.error("Failed to load content types. Please try again.")
    content_types = {}


# --- Create Tab ---
with tab_create:
    if not content_types:
        st.warning("No content types available. Check API connection.")
    else:
        # Content type selector with colored badges
        st.markdown("#### Select Content Type")
        type_keys = list(content_types.keys())
        type_labels = []
        for key in type_keys:
            ct = content_types[key]
            name = ct.get("name", key)
            ui = ct.get("ui_config", {})
            category = ui.get("category", "")
            label = f"{name} ({category})" if category else name
            type_labels.append(label)

        selected_idx = st.selectbox(
            "Content Type",
            range(len(type_keys)),
            format_func=lambda i: type_labels[i],
            label_visibility="collapsed",
        ) or 0
        selected_key = type_keys[selected_idx]
        selected_type = content_types[selected_key]

        # Show type details
        type_name = selected_type.get("name", selected_key)
        type_desc = selected_type.get("description", "")
        max_words = selected_type.get("max_words", "N/A")
        mode = selected_type.get("default_mode", "N/A")
        st.info(f"**{type_name}**\n\n{type_desc}\n\nMax words: {max_words} | Mode: {mode}")

        # Structure hint
        hint = selected_type.get("structure_hint", "")
        if hint:
            with st.expander("Structure Guide"):
                st.markdown(hint)

        # Input form
        prompt = st.text_area(
            "What do you want to create?",
            height=150,
            placeholder=f"Describe the {selected_type.get('name', '')} you want to create...",
        )

        if st.button("Create", type="primary", disabled=not prompt):
            with st.spinner("Creating content..."):
                try:
                    result = api_client.call_agent("/create", {
                        "prompt": prompt,
                        "content_type": selected_key,
                    })

                    # Store draft for review tab
                    st.session_state["last_draft"] = result

                    st.success("Content created!")

                    # Display draft
                    st.markdown("#### Draft")
                    draft = result.get("draft", "")
                    copyable_text(draft)

                    # Metadata
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Words", result.get("word_count", len(draft.split())))
                    with col2:
                        st.metric("Type", result.get("content_type", selected_key))
                    with col3:
                        st.metric("Mode", result.get("mode", ""))

                    # Voice elements
                    voice = result.get("voice_elements", [])
                    if voice:
                        st.markdown("**Voice Elements Applied:**")
                        st.markdown(", ".join(voice))

                    # Patterns
                    patterns = result.get("patterns_applied", [])
                    if patterns:
                        st.markdown("**Patterns Applied:**")
                        st.markdown(", ".join(patterns))

                    # Examples referenced
                    examples = result.get("examples_referenced", [])
                    if examples:
                        st.markdown("**Examples Referenced:**")
                        st.markdown(", ".join(examples))

                    # Notes
                    notes = result.get("notes", "")
                    if notes:
                        st.markdown("**Editorial Notes:**")
                        st.info(notes)

                except Exception:
                    logger.exception("Content creation failed")
                    st.error("Content creation failed. Please try again.")


# --- Review Tab ---
with tab_review:
    st.markdown("#### Review Content")

    # Pre-fill from last draft if available
    default_content = ""
    if "last_draft" in st.session_state:
        last = st.session_state["last_draft"]
        default_content = last.get("draft", "")
        st.info("Pre-filled with your last created draft. Edit or paste new content below.")

    review_content = st.text_area(
        "Content to review",
        value=default_content,
        height=200,
        placeholder="Paste content to review...",
    )

    # Optional content type for review context
    review_type = None
    if content_types:
        type_options = ["Auto-detect"] + list(content_types.keys())
        review_type_idx = st.selectbox("Content Type (optional)", range(len(type_options)),
                                       format_func=lambda i: type_options[i]) or 0
        if review_type_idx > 0:
            review_type = type_options[review_type_idx]

    if st.button("Review", type="primary", disabled=not review_content):
        with st.spinner("Reviewing content..."):
            try:
                payload = {"content": review_content}
                if review_type:
                    payload["content_type"] = review_type

                result = api_client.call_agent("/review", payload)

                # Verdict banner
                verdict = result.get("verdict", "")
                verdict_icon = _VERDICT_ICONS.get(verdict, ":material/info:")
                if verdict == "READY TO SEND":
                    st.success(f"{verdict_icon} **{verdict}**")
                elif verdict == "NEEDS REVISION":
                    st.warning(f"{verdict_icon} **{verdict}**")
                elif verdict == "MAJOR REWORK":
                    st.error(f"{verdict_icon} **{verdict}**")
                else:
                    st.info(f"{verdict_icon} **{verdict}**")

                # Overall score
                overall = result.get("overall_score", 0)
                st.metric("Overall Score", f"{overall:.1f} / 10")

                # Summary
                summary = result.get("summary", "")
                if summary:
                    st.text(summary)

                # Per-dimension scores
                scores = result.get("scores", [])
                if scores:
                    st.markdown("#### Dimension Scores")
                    for dim_score in scores:
                        dim_name = dim_score.get("dimension", "")
                        score = dim_score.get("score", 0)
                        status = dim_score.get("status", "")

                        s_icon = _STATUS_ICONS.get(status, "")

                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"{s_icon} **{dim_name}**")
                            st.progress(min(score / 10.0, 1.0))
                        with col2:
                            st.metric(
                                label=dim_name,
                                value=f"{score}/10",
                                label_visibility="collapsed",
                            )

                        # Strengths / Suggestions / Issues
                        strengths = dim_score.get("strengths", [])
                        suggestions = dim_score.get("suggestions", [])
                        issues = dim_score.get("issues", [])

                        with st.expander(f"{dim_name} Details", expanded=status == "issue"):
                            if strengths:
                                for s in strengths:
                                    st.markdown(f":material/check_circle: {s}")
                            if suggestions:
                                for s in suggestions:
                                    st.markdown(f":material/lightbulb: {s}")
                            if issues:
                                for s in issues:
                                    st.markdown(f":material/error: {s}")

                # Top strengths / Critical issues / Next steps
                top_strengths = result.get("top_strengths", [])
                if top_strengths:
                    st.markdown("#### Top Strengths")
                    for s in top_strengths:
                        st.markdown(f":material/check_circle: {s}")

                critical = result.get("critical_issues", [])
                if critical:
                    st.markdown("#### Critical Issues")
                    for s in critical:
                        st.error(s)

                next_steps = result.get("next_steps", [])
                if next_steps:
                    st.markdown("#### Next Steps")
                    for s in next_steps:
                        st.markdown(f"- {s}")

            except Exception:
                logger.exception("Content review failed")
                st.error("Review failed. Please try again.")
