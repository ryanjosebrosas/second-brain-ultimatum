"""Chat page — Interactive chat with agent selector."""

import logging
from typing import Any

import streamlit as st

from config import AGENTS, DEFAULT_CONTENT_TYPES, group_content_types_by_category
from api_client import call_agent, get_content_types
from components.agent_formatters import format_agent_response

logger = logging.getLogger(__name__)

# Pre-computed from static AGENTS config — no need to rebuild on every rerun.
_AGENT_KEYS: list[str] = list(AGENTS.keys())
_AGENT_LABELS: list[str] = [f"{AGENTS[k]['icon']} {AGENTS[k]['name']}" for k in _AGENT_KEYS]

# Maximum chat messages retained per agent to prevent session state bloat.
_MAX_HISTORY: int = 50

# Maximum input length in characters. Prevents runaway LLM costs.
_MAX_INPUT_LENGTH: int = 10_000


@st.cache_data(ttl=300)
def _get_content_type_options() -> list[str]:
    """Fetch content types with 5-minute cache. Falls back to defaults."""
    try:
        ct_data = get_content_types()
        options = [ct["slug"] for ct in ct_data.get("content_types", [])]
        return options if options else DEFAULT_CONTENT_TYPES
    except Exception:
        return DEFAULT_CONTENT_TYPES


@st.cache_data(ttl=300)
def _get_content_type_options_full() -> dict[str, dict]:
    """Get content types as {slug: {full config}} for grouped selector."""
    try:
        ct_data = get_content_types()
        if isinstance(ct_data, dict) and "content_types" in ct_data:
            return {ct["slug"]: ct for ct in ct_data["content_types"] if "slug" in ct}
        elif isinstance(ct_data, list):
            return {ct.get("slug", ct.get("name", "unknown")): ct for ct in ct_data}
    except Exception:
        pass
    return {}


# --- Page header ---
st.title(":material/chat: Chat")
st.caption("Talk to your Second Brain agents")

# --- Agent selector in sidebar ---
with st.sidebar:
    st.subheader("Agent")
    selected_idx: int = st.radio(
        "Select an agent",
        range(len(_AGENT_KEYS)),
        format_func=lambda i: _AGENT_LABELS[i],
        label_visibility="collapsed",
    ) or 0
    agent_key: str = _AGENT_KEYS[selected_idx]
    agent_config: dict[str, Any] = AGENTS[agent_key]
    st.caption(agent_config["description"])

# --- Initialize chat history per agent ---
history_key = f"chat_history_{agent_key}"
if history_key not in st.session_state:
    st.session_state[history_key] = []

# --- Extra fields (above chat input) ---
extra_values: dict[str, str] = {}
if agent_config["extra_fields"]:
    with st.expander("Options", expanded=False):
        for field_name, field_config in agent_config["extra_fields"].items():
            if field_config["type"] == "text":
                extra_values[field_name] = st.text_input(
                    field_config["label"],
                    value=field_config["default"],
                    key=f"extra_{agent_key}_{field_name}",
                )
            elif field_config["type"] == "select":
                # Grouped content type selector with cascade
                full_options = _get_content_type_options_full()
                if full_options:
                    grouped = group_content_types_by_category(full_options)
                    cat_col, type_col = st.columns(2)
                    with cat_col:
                        chat_category = st.selectbox(
                            "Category",
                            options=list(grouped.keys()),
                            index=0,
                            key=f"chat_{agent_key}_category",
                        )
                    with type_col:
                        if chat_category and chat_category in grouped:
                            type_items = grouped[chat_category]
                            slugs = [s for s, n in type_items]
                            names = [n for s, n in type_items]
                            type_idx = st.selectbox(
                                field_config["label"],
                                range(len(slugs)),
                                format_func=lambda i, n=names: n[i],
                                key=f"chat_{agent_key}_{field_name}",
                            ) or 0
                            extra_values[field_name] = slugs[type_idx]
                        else:
                            extra_values[field_name] = field_config.get("default", "linkedin")
                else:
                    # Fallback to flat list if full options unavailable
                    options = _get_content_type_options()
                    default_val = field_config["default"]
                    default_idx = options.index(default_val) if default_val and default_val in options else 0
                    extra_values[field_name] = st.selectbox(
                        field_config["label"],
                        options=options,
                        index=default_idx,
                        key=f"chat_{agent_key}_{field_name}",
                    )
            elif field_config["type"] == "select_fixed":
                options = field_config["options"]
                default_val = field_config["default"]
                default_idx = options.index(default_val) if default_val in options else 0
                extra_values[field_name] = st.selectbox(
                    field_config["label"],
                    options=options,
                    index=default_idx,
                    key=f"extra_{agent_key}_{field_name}",
                )

# --- Display chat history ---
for msg in st.session_state[history_key]:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            format_agent_response(agent_key, msg["content"])

# --- Chat input ---
user_input = st.chat_input(agent_config["input_label"])

if user_input:
    if len(user_input) > _MAX_INPUT_LENGTH:
        st.warning(f"Input too long ({len(user_input):,} chars). Maximum is {_MAX_INPUT_LENGTH:,}.")
        st.stop()

    # Add user message to history
    st.session_state[history_key].append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    # Build payload
    payload = {agent_config["input_field"]: user_input}
    for field_name, value in extra_values.items():
        if value:
            payload[field_name] = value

    # Call agent
    with st.chat_message("assistant"):
        with st.spinner(f"{agent_config['name']} is thinking..."):
            try:
                response = call_agent(agent_config["endpoint"], payload)
                format_agent_response(agent_key, response)
                st.session_state[history_key].append({"role": "assistant", "content": response})
                # Cap history to prevent session state bloat
                if len(st.session_state[history_key]) > _MAX_HISTORY:
                    st.session_state[history_key] = st.session_state[history_key][-_MAX_HISTORY:]
            except Exception as e:
                logger.error("Agent %s call failed: %s", agent_key, e)
                error_msg = "An error occurred. Please try again."
                st.error(error_msg)
                st.session_state[history_key].append({"role": "assistant", "content": error_msg})
                # Cap history
                if len(st.session_state[history_key]) > _MAX_HISTORY:
                    st.session_state[history_key] = st.session_state[history_key][-_MAX_HISTORY:]
