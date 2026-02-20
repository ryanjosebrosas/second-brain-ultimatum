"""Template Bank — browse, edit, and create reusable content templates."""

import logging

import streamlit as st

import api_client

logger = logging.getLogger(__name__)

st.header("Template Bank")

# --- Data Loading ---


@st.cache_data(ttl=30)
def _load_templates(content_type: str | None = None, tag: str | None = None) -> list[dict]:
    try:
        result = api_client.get_templates(content_type=content_type, tag=tag)
        return result.get("templates", []) if isinstance(result, dict) else []
    except Exception:
        logger.exception("Failed to load templates")
        return []


@st.cache_data(ttl=300)
def _load_content_types() -> dict[str, dict]:
    try:
        ct_response = api_client.get_content_types()
        if isinstance(ct_response, dict) and "content_types" in ct_response:
            items = ct_response["content_types"]
        elif isinstance(ct_response, list):
            items = ct_response
        else:
            return {}
        return {ct.get("slug", ct.get("name", "?")): ct for ct in items}
    except Exception:
        logger.exception("Failed to load content types")
        return {}


content_types = _load_content_types()
ct_slugs = sorted(content_types.keys())

# --- Tabs ---
tab_browse, tab_edit, tab_deconstruct = st.tabs(
    ["Browse Library", "Edit / Create", "Deconstruct Content"]
)

# ========== TAB 1: Browse Library ==========
with tab_browse:
    # Filters
    col_type, col_tag, col_search = st.columns(3)
    with col_type:
        filter_type = st.selectbox(
            "Content Type",
            options=["All"] + ct_slugs,
            key="browse_filter_type",
        )
    with col_tag:
        filter_tag = st.text_input("Tag filter", key="browse_filter_tag")
    with col_search:
        search_text = st.text_input("Search name", key="browse_search")

    # Load filtered templates
    selected_type = filter_type if filter_type != "All" else None
    selected_tag = filter_tag.strip() or None
    templates = _load_templates(content_type=selected_type, tag=selected_tag)

    # Client-side name search
    if search_text:
        templates = [
            t for t in templates
            if search_text.lower() in t.get("name", "").lower()
        ]

    if not templates:
        st.info("No templates found. Create one in the Edit/Create tab or deconstruct existing content.")
    else:
        st.caption(f"{len(templates)} templates")
        for tmpl in templates:
            tmpl_id = tmpl.get("id", "")
            tmpl_name = tmpl.get("name", "Untitled")
            tmpl_type = tmpl.get("content_type", "?")
            tmpl_tags = ", ".join(tmpl.get("tags", [])) or "none"
            uses = tmpl.get("use_count", 0)

            with st.expander(f"{tmpl_name}  ({tmpl_type})  [uses: {uses}]"):
                st.markdown(f"**Structure:** {tmpl.get('structure_hint', 'N/A')}")
                st.markdown(f"**When to use:** {tmpl.get('when_to_use', 'N/A')}")
                if tmpl.get("when_not_to_use"):
                    st.markdown(f"**When NOT to use:** {tmpl['when_not_to_use']}")
                st.markdown(f"**Tags:** {tmpl_tags}")

                # Show template body
                with st.expander("Template Body", expanded=False):
                    st.code(tmpl.get("body", "(empty)"), language=None)

                if tmpl.get("customization_guide"):
                    with st.expander("Customization Guide", expanded=False):
                        st.markdown(tmpl["customization_guide"])

                # Action buttons
                col_edit, col_del = st.columns([1, 1])
                with col_edit:
                    if st.button("Edit", key=f"edit_{tmpl_id}"):
                        st.session_state["edit_template_id"] = tmpl_id
                        st.session_state["edit_template_data"] = tmpl
                        st.rerun()
                with col_del:
                    if st.button("Delete", key=f"del_{tmpl_id}", type="secondary"):
                        try:
                            api_client.delete_template(tmpl_id)
                            st.success(f"Deleted: {tmpl_name}")
                            _load_templates.clear()
                            st.rerun()
                        except Exception:
                            logger.exception("Failed to delete template")
                            st.error("Failed to delete template.")

# ========== TAB 2: Edit / Create ==========
with tab_edit:
    # Check if editing existing template
    editing = st.session_state.get("edit_template_data")
    if editing:
        st.subheader(f"Editing: {editing.get('name', 'Untitled')}")
        if st.button("Cancel edit", type="secondary"):
            st.session_state.pop("edit_template_id", None)
            st.session_state.pop("edit_template_data", None)
            st.rerun()
    else:
        st.subheader("Create New Template")

    with st.form("template_form"):
        name = st.text_input(
            "Template Name",
            value=editing.get("name", "") if editing else "",
        )
        col_ct, col_tags = st.columns(2)
        with col_ct:
            ct_index = ct_slugs.index(editing["content_type"]) if editing and editing.get("content_type") in ct_slugs else 0
            content_type = st.selectbox(
                "Content Type", options=ct_slugs,
                index=ct_index,
                key="edit_content_type",
            )
        with col_tags:
            existing_tags = ", ".join(editing.get("tags", [])) if editing else ""
            tags_raw = st.text_input("Tags (comma-separated)", value=existing_tags)

        description = st.text_area(
            "Description",
            value=editing.get("description", "") if editing else "",
            height=80,
        )
        body = st.text_area(
            "Template Body (use [PLACEHOLDER_NAME] for customizable parts)",
            value=editing.get("body", "") if editing else "",
            height=300,
        )
        structure_hint = st.text_input(
            "Structure Hint (e.g., Hook -> Body -> CTA)",
            value=editing.get("structure_hint", "") if editing else "",
        )
        when_to_use = st.text_area(
            "When to Use",
            value=editing.get("when_to_use", "") if editing else "",
            height=80,
        )
        when_not_to_use = st.text_area(
            "When NOT to Use",
            value=editing.get("when_not_to_use", "") if editing else "",
            height=80,
        )
        customization_guide = st.text_area(
            "Customization Guide",
            value=editing.get("customization_guide", "") if editing else "",
            height=80,
        )

        submitted = st.form_submit_button(
            "Update Template" if editing else "Create Template",
            type="primary",
            disabled=not name or not body,
        )

    if submitted:
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
        template_data = {
            "name": name,
            "content_type": content_type,
            "body": body,
            "description": description,
            "structure_hint": structure_hint,
            "when_to_use": when_to_use,
            "when_not_to_use": when_not_to_use,
            "customization_guide": customization_guide,
            "tags": tags,
        }
        try:
            if editing:
                api_client.update_template(
                    st.session_state["edit_template_id"], template_data,
                )
                st.success(f"Updated: {name}")
                st.session_state.pop("edit_template_id", None)
                st.session_state.pop("edit_template_data", None)
            else:
                api_client.create_template(template_data)
                st.success(f"Created: {name}")
            _load_templates.clear()
            st.rerun()
        except Exception:
            logger.exception("Failed to save template")
            st.error("Failed to save template. Please try again.")


# ========== TAB 3: Deconstruct Content ==========
with tab_deconstruct:
    st.subheader("Deconstruct Existing Content")
    st.caption(
        "Paste content below and the AI will extract a reusable template "
        "with [PLACEHOLDER] markers for customizable parts."
    )

    col_ct2, _ = st.columns([1, 2])
    with col_ct2:
        hint_type = st.selectbox(
            "Content Type Hint (optional)",
            options=["auto-detect"] + ct_slugs,
            key="deconstruct_type_hint",
        )

    source_content = st.text_area(
        "Paste your content here",
        height=250,
        key="deconstruct_input",
    )

    if st.button(
        "Deconstruct", type="primary",
        disabled=not source_content or len(source_content.strip()) < 50,
    ):
        with st.spinner("Deconstructing content into template..."):
            try:
                ct_hint = hint_type if hint_type != "auto-detect" else ""
                result = api_client.deconstruct_content(
                    source_content, content_type=ct_hint,
                )
                st.session_state["deconstruct_result"] = result
            except Exception:
                logger.exception("Deconstruction failed")
                st.error("Deconstruction failed. Please try again.")

    # Show result and allow save
    if "deconstruct_result" in st.session_state:
        result = st.session_state["deconstruct_result"]
        st.success(f"Template extracted: {result.get('name', 'Untitled')}")

        st.markdown(f"**Name:** {result.get('name', '')}")
        st.markdown(f"**Content Type:** {result.get('content_type', '')}")
        st.markdown(f"**Structure:** {result.get('structure_hint', '')}")
        st.markdown(f"**When to Use:** {result.get('when_to_use', '')}")
        st.markdown(f"**Tags:** {', '.join(result.get('tags', []))}")

        with st.expander("Template Body", expanded=True):
            st.code(result.get("body", ""), language=None)

        col_save, col_edit_btn, col_discard = st.columns(3)
        with col_save:
            if st.button("Save to Bank", type="primary", key="save_deconstructed"):
                try:
                    save_data = {
                        "name": result.get("name", ""),
                        "content_type": result.get("content_type", ""),
                        "body": result.get("body", ""),
                        "structure_hint": result.get("structure_hint", ""),
                        "when_to_use": result.get("when_to_use", ""),
                        "when_not_to_use": result.get("when_not_to_use", ""),
                        "customization_guide": result.get("customization_guide", ""),
                        "tags": result.get("tags", []),
                        "source_deliverable": source_content[:500],
                        "ai_generated": True,
                    }
                    api_client.create_template(save_data)
                    st.success("Saved to template bank!")
                    st.session_state.pop("deconstruct_result", None)
                    _load_templates.clear()
                    st.rerun()
                except Exception:
                    logger.exception("Failed to save deconstructed template")
                    st.error("Failed to save. Please try again.")
        with col_edit_btn:
            if st.button("Edit before saving", key="edit_deconstructed"):
                st.session_state["edit_template_data"] = {
                    **result,
                    "source_deliverable": source_content[:500],
                    "ai_generated": True,
                }
                st.session_state.pop("deconstruct_result", None)
                st.rerun()
        with col_discard:
            if st.button("Discard", type="secondary", key="discard_deconstructed"):
                st.session_state.pop("deconstruct_result", None)
                st.rerun()
