"""Content page — Content creation studio with type selector and review."""

import json

import streamlit as st

from components.copy_button import copyable_text, copyable_output
import api_client

st.title(":material/edit: Content Studio")

tab_create, tab_review = st.tabs(["Create", "Review"])

# --- Load content types ---
try:
    ct_response = api_client.get_content_types()
    # Handle both list and dict response formats
    if isinstance(ct_response, list):
        content_types = {ct.get("slug", ct.get("name", "unknown")): ct for ct in ct_response}
    elif isinstance(ct_response, dict):
        content_types = ct_response
    else:
        content_types = {}
except Exception as e:
    st.error(f"Failed to load content types: {e}")
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
        )
        selected_key = type_keys[selected_idx]
        selected_type = content_types[selected_key]

        # Show type details
        ui_config = selected_type.get("ui_config", {})
        color = ui_config.get("color", "#7C3AED")
        st.markdown(
            f'<div style="background-color:{color}22;border-left:4px solid {color};'
            f'padding:8px 12px;border-radius:4px;margin-bottom:1rem;">'
            f'<strong>{selected_type.get("name", selected_key)}</strong><br>'
            f'<small>{selected_type.get("description", "")}</small><br>'
            f'<small>Max words: {selected_type.get("max_words", "N/A")} | '
            f'Mode: {selected_type.get("default_mode", "N/A")}</small>'
            f"</div>",
            unsafe_allow_html=True,
        )

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

                except Exception as e:
                    st.error(f"Creation failed: {e}")


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
                                       format_func=lambda i: type_options[i])
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
                verdict_colors = {
                    "READY TO SEND": "#22C55E",
                    "NEEDS REVISION": "#F59E0B",
                    "MAJOR REWORK": "#EF4444",
                }
                v_color = verdict_colors.get(verdict, "#6B7280")
                st.markdown(
                    f'<div style="background-color:{v_color}22;border:2px solid {v_color};'
                    f'padding:12px;border-radius:8px;text-align:center;margin-bottom:1rem;">'
                    f'<h3 style="color:{v_color};margin:0;">{verdict}</h3></div>',
                    unsafe_allow_html=True,
                )

                # Overall score
                overall = result.get("overall_score", 0)
                st.metric("Overall Score", f"{overall:.1f} / 10")

                # Summary
                summary = result.get("summary", "")
                if summary:
                    st.markdown(summary)

                # Per-dimension scores
                scores = result.get("scores", [])
                if scores:
                    st.markdown("#### Dimension Scores")
                    for dim_score in scores:
                        dim_name = dim_score.get("dimension", "")
                        score = dim_score.get("score", 0)
                        status = dim_score.get("status", "")

                        status_colors = {
                            "pass": "#22C55E",
                            "warning": "#F59E0B",
                            "issue": "#EF4444",
                        }
                        s_color = status_colors.get(status, "#6B7280")

                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**{dim_name}**")
                            st.progress(min(score / 10.0, 1.0))
                        with col2:
                            st.markdown(
                                f'<span style="color:{s_color};font-weight:600;">'
                                f"{score}/10</span>",
                                unsafe_allow_html=True,
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

            except Exception as e:
                st.error(f"Review failed: {e}")
