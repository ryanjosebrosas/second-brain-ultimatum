"""Content page — Content creation studio with type selector, review, and ingestion."""

import logging
from typing import Any

import streamlit as st

from components.copy_button import copyable_text
from config import group_content_types_by_category, KNOWLEDGE_CATEGORIES
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

_VOICE_PROFILES = ["Default", "uttam", "robert", "luke"]

st.title(":material/edit: Content Studio")

tab_create, tab_review, tab_ingest = st.tabs(["Create", "Review", "Ingest"])


@st.cache_data(ttl=300)
def _get_cached_content_types() -> dict[str, Any]:
    """Fetch content types with 5-minute cache to avoid API calls on every rerun."""
    ct_response = api_client.get_content_types()
    if isinstance(ct_response, dict) and "content_types" in ct_response:
        return {ct.get("slug", ct.get("name", "unknown")): ct for ct in ct_response["content_types"]}
    elif isinstance(ct_response, list):
        return {ct.get("slug", ct.get("name", "unknown")): ct for ct in ct_response}
    return {}


@st.cache_data(ttl=60)
def _get_cached_templates(content_type: str) -> dict[str, Any]:
    """Fetch templates for a content type with 1-minute cache."""
    return api_client.get_templates(content_type=content_type)


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
        st.markdown("#### Select Content Type")

        # Grouped cascade selector
        grouped = group_content_types_by_category(content_types)
        col_cat, col_type = st.columns(2)
        with col_cat:
            category_options = list(grouped.keys())
            selected_category = st.selectbox(
                "Category",
                options=category_options,
                index=0,
                key="create_category",
            )
        with col_type:
            if selected_category and selected_category in grouped:
                type_options = grouped[selected_category]
                type_slugs = [slug for slug, name in type_options]
                type_names = [name for slug, name in type_options]
                selected_type_idx = st.selectbox(
                    "Content Type",
                    range(len(type_slugs)),
                    format_func=lambda i: type_names[i],
                    key="create_type",
                ) or 0
                selected_key = type_slugs[selected_type_idx]
                selected_type = content_types[selected_key]
            else:
                selected_key = list(content_types.keys())[0] if content_types else "linkedin"
                selected_type = content_types.get(selected_key, {})

        # Voice profile selector
        selected_voice = st.selectbox(
            "Voice Profile",
            options=_VOICE_PROFILES,
            index=0,
            key="create_voice_profile",
            help="Select whose writing voice and style to use for this content.",
        )
        voice_user_id = "" if selected_voice == "Default" else selected_voice

        # Show type details
        type_name = selected_type.get("name", selected_key)
        type_desc = selected_type.get("description", "")
        max_words = selected_type.get("max_words", "N/A")
        mode = selected_type.get("default_mode", "N/A")
        st.info(f"**{type_name}**\n\n{type_desc}\n\nMax words: {max_words} | Mode: {mode}")

        # --- Template selector ---
        selected_template_body = ""
        try:
            tmpl_response = _get_cached_templates(selected_key)
            tmpl_list = tmpl_response.get("templates", []) if isinstance(tmpl_response, dict) else []
        except Exception:
            tmpl_list = []

        st.markdown("#### Template (optional)")
        if tmpl_list:
            tmpl_names = ["None — write from scratch"] + [
                t.get("name", "Untitled") for t in tmpl_list
            ]
            tmpl_choice = st.selectbox(
                "Template",
                options=range(len(tmpl_names)),
                format_func=lambda i: tmpl_names[i],
                key="create_template",
            )
            if tmpl_choice and tmpl_choice > 0:
                chosen_template = tmpl_list[tmpl_choice - 1]
                selected_template_body = chosen_template.get("body", "")
                if selected_template_body:
                    st.code(selected_template_body, language=None)
        else:
            st.caption("No templates available for this content type.")

        # Input form
        prompt = st.text_area(
            "What do you want to create?",
            height=150,
            placeholder=f"Describe the {selected_type.get('name', '')} you want to create...",
        )

        if st.button("Create", type="primary", disabled=not prompt):
            with st.spinner("Creating content..."):
                try:
                    payload = {
                        "prompt": prompt,
                        "content_type": selected_key,
                    }
                    if voice_user_id:
                        payload["user_id"] = voice_user_id
                    if selected_template_body:
                        payload["structure_hint"] = selected_template_body
                    result = api_client.call_agent("/create", payload)

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

    # Grouped content type selector with Auto-detect
    review_type = None
    if content_types:
        review_options: list[tuple[str, str]] = [("auto", "Auto-detect")]
        for cat_label, items in group_content_types_by_category(content_types).items():
            review_options.extend(items)
        review_slugs = [s for s, n in review_options]
        review_names = [n for s, n in review_options]
        review_idx = st.selectbox(
            "Content Type (optional)",
            range(len(review_slugs)),
            format_func=lambda i: review_names[i],
            key="review_type",
        ) or 0
        if review_slugs[review_idx] != "auto":
            review_type = review_slugs[review_idx]

    # Voice profile for voice alignment scoring
    review_voice = st.selectbox(
        "Voice Profile",
        options=_VOICE_PROFILES,
        index=0,
        key="review_voice_profile",
        help="Select whose voice to score alignment against.",
    )
    review_voice_id = "" if review_voice == "Default" else review_voice

    if st.button("Review", type="primary", disabled=not review_content):
        with st.spinner("Reviewing content..."):
            try:
                payload = {"content": review_content}
                if review_type:
                    payload["content_type"] = review_type
                if review_voice_id:
                    payload["user_id"] = review_voice_id

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


# --- Ingest Tab ---
with tab_ingest:
    st.subheader("Ingest Content")
    st.caption("Add examples, knowledge, and files to your brain.")

    sub_examples, sub_knowledge, sub_files, sub_text = st.tabs(
        ["Examples", "Knowledge", "Files", "Text / Learn"]
    )

    # --- Examples sub-tab ---
    with sub_examples:
        st.markdown("**Add a content example** — pre-filled templates you can edit.")

        # Grouped content type selector
        ex_grouped = group_content_types_by_category(content_types)
        ex_col_cat, ex_col_type = st.columns(2)
        with ex_col_cat:
            ex_categories = list(ex_grouped.keys())
            ex_category = st.selectbox(
                "Category",
                options=ex_categories,
                index=0,
                key="ingest_ex_category",
            ) if ex_categories else None
        with ex_col_type:
            if ex_category and ex_category in ex_grouped:
                ex_type_options = ex_grouped[ex_category]
                ex_slugs = [s for s, n in ex_type_options]
                ex_names = [n for s, n in ex_type_options]
                ex_type_idx = st.selectbox(
                    "Content Type",
                    range(len(ex_slugs)),
                    format_func=lambda i: ex_names[i],
                    key="ingest_ex_type",
                ) or 0
                ex_selected_slug = ex_slugs[ex_type_idx]
                ex_selected_ct = content_types.get(ex_selected_slug, {})
            else:
                ex_selected_slug = ""
                ex_selected_ct = {}

        ex_title = st.text_input("Title", placeholder="e.g., Q4 Product Launch Post", key="ingest_ex_title")

        # Pre-fill template from structure_hint + writing_instructions
        template_parts = []
        hint = ex_selected_ct.get("structure_hint", "")
        if hint:
            template_parts.append(f"# Structure\n{hint}\n")
        instructions = ex_selected_ct.get("writing_instructions", "")
        if instructions:
            template_parts.append(f"# Guidelines\n{instructions}\n")
        template_text = "\n".join(template_parts) if template_parts else ""

        ex_content = st.text_area(
            "Content",
            value=template_text,
            height=300,
            key=f"ingest_ex_content_{ex_selected_slug}",
            help="Edit the template above with your actual content.",
        )

        ex_notes = st.text_input("Notes (optional)", key="ingest_ex_notes")

        if st.button("Save Example", type="primary", key="btn_save_example",
                      disabled=not (ex_selected_slug and ex_title and ex_content)):
            result = api_client.ingest_example(
                content_type=ex_selected_slug,
                title=ex_title,
                content=ex_content,
                notes=ex_notes or None,
            )
            if "error" not in result:
                st.success(f"Example saved: {ex_title} (ID: {result.get('id', 'unknown')})")
            else:
                st.error(f"Failed to save example: {result.get('error', 'Unknown error')}")

    # --- Knowledge sub-tab ---
    with sub_knowledge:
        st.markdown("**Add knowledge** — audience info, product details, competitor intel, etc.")

        kn_category = st.selectbox(
            "Knowledge Category",
            options=KNOWLEDGE_CATEGORIES,
            index=0,
            key="ingest_kn_category",
        )
        kn_title = st.text_input("Title", placeholder="e.g., Ideal Customer Profile", key="ingest_kn_title")
        kn_content = st.text_area("Content", height=250, key="ingest_kn_content",
                                   placeholder="Write or paste your knowledge entry here...")
        kn_tags = st.text_input("Tags (comma-separated, optional)", key="ingest_kn_tags",
                                 placeholder="e.g., audience, B2B, enterprise")

        if st.button("Save Knowledge", type="primary", key="btn_save_knowledge",
                      disabled=not (kn_category and kn_title and kn_content)):
            result = api_client.ingest_knowledge(
                category=kn_category,
                title=kn_title,
                content=kn_content,
                tags=kn_tags or None,
            )
            if "error" not in result:
                st.success(f"Knowledge saved: {kn_title} (ID: {result.get('id', 'unknown')})")
            else:
                st.error(f"Failed to save knowledge: {result.get('error', 'Unknown error')}")

    # --- Files sub-tab ---
    with sub_files:
        st.markdown("**Upload files** — PDFs, images, or text documents.")

        file_category = st.selectbox(
            "Category",
            options=["document", "visual", "reference", "general"],
            index=0,
            key="ingest_file_category",
        )
        file_context = st.text_input(
            "Context (optional)",
            placeholder="Describe what this file contains...",
            key="ingest_file_context",
        )

        uploaded = st.file_uploader(
            "Choose a file",
            type=["pdf", "jpg", "jpeg", "png", "webp", "gif", "txt", "md"],
            key="ingest_file_uploader",
            help="Supported: PDF, images (JPG/PNG/WebP/GIF), text files (TXT/MD). Max 20 MB.",
        )

        if uploaded:
            # Preview
            if uploaded.type and uploaded.type.startswith("image/"):
                st.image(uploaded, caption=uploaded.name, width=400)
            else:
                st.info(f"File: **{uploaded.name}** ({uploaded.size // 1024} KB, {uploaded.type})")

            if st.button("Upload & Ingest", type="primary", key="btn_upload_file"):
                file_bytes = uploaded.read()
                with st.spinner(f"Ingesting {uploaded.name}..."):
                    result = api_client.upload_file(
                        file_bytes=file_bytes,
                        filename=uploaded.name,
                        content_type=uploaded.type or "application/octet-stream",
                        context=file_context,
                        category=file_category,
                    )
                if "error" not in result:
                    st.success(
                        f"{result.get('message', 'File ingested')} "
                        f"| Type: {result.get('type', 'unknown')} "
                        f"| Memory: {'Yes' if result.get('memory_stored') else 'No'}"
                    )
                    if result.get("embedding"):
                        st.caption(f"Embedding: {result['embedding']}")
                else:
                    st.error(f"Upload failed: {result.get('error', 'Unknown error')}")

    # --- Text / Learn sub-tab ---
    with sub_text:
        st.markdown("**Paste text content** — the Learn agent will extract patterns and insights.")

        learn_category = st.selectbox(
            "Category",
            options=["general", "content", "prospects", "clients", "personal"],
            index=0,
            key="ingest_learn_category",
        )
        learn_content = st.text_area(
            "Content to learn from",
            height=300,
            key="ingest_learn_content",
            placeholder="Paste your work session notes, meeting transcripts, or any content...",
        )

        if st.button("Learn", type="primary", key="btn_learn",
                      disabled=not learn_content):
            with st.spinner("Extracting patterns and insights..."):
                result = api_client.call_agent("/learn", {
                    "content": learn_content,
                    "category": learn_category,
                })
            if "error" not in result:
                st.success("Learning complete!")
                if result.get("patterns_extracted"):
                    st.markdown("**Patterns extracted:**")
                    for p in result["patterns_extracted"]:
                        name = p.get("name", "Unnamed") if isinstance(p, dict) else str(p)
                        st.markdown(f"- {name}")
                if result.get("insights"):
                    with st.expander("Insights"):
                        for insight in result["insights"]:
                            st.markdown(f"- {insight}")
                if result.get("storage_summary"):
                    st.caption(result["storage_summary"])
            else:
                st.error(f"Learning failed: {result.get('error', 'Unknown error')}")
