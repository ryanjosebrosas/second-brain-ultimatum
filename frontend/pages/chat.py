"""Chat page — Interactive chat with agent selector."""

import json

import streamlit as st

from config import AGENTS
from api_client import call_agent, get_content_types
from components.styles import inject_styles
from components.copy_button import copyable_text, copyable_output

inject_styles()


def _format_agent_response(agent: str, data):
    """Format an agent response for display."""
    if isinstance(data, str):
        st.markdown(data)
        return

    if not isinstance(data, dict):
        st.write(data)
        return

    # Agent-specific formatting
    if agent == "recall":
        if data.get("summary"):
            st.markdown(f"**Summary**: {data['summary']}")
        matches = data.get("matches", [])
        if matches:
            st.markdown(f"**{len(matches)} matches found**")
            for i, m in enumerate(matches):
                with st.expander(f"Match {i+1} — {m.get('relevance', 'MEDIUM')} relevance"):
                    copyable_text(m.get("content", ""))
                    if m.get("source"):
                        st.caption(f"Source: {m['source']}")
        patterns = data.get("patterns", [])
        if patterns:
            st.markdown("**Related Patterns**: " + ", ".join(patterns))
        relations = data.get("relations", [])
        if relations:
            st.markdown("**Relations**:")
            for r in relations:
                st.markdown(f"- {r.get('source', '?')} \u2192 *{r.get('relationship', '?')}* \u2192 {r.get('target', '?')}")

    elif agent == "ask":
        if data.get("answer"):
            copyable_text(data["answer"])
        if data.get("confidence"):
            st.caption(f"Confidence: {data['confidence']}")
        if data.get("context_used"):
            with st.expander("Context Used"):
                for ctx in data["context_used"]:
                    st.markdown(f"- {ctx}")
        if data.get("next_action"):
            st.info(f"Suggested next: `{data['next_action']}`")

    elif agent == "learn":
        if data.get("summary"):
            st.markdown(data["summary"])
        patterns = data.get("patterns_extracted", [])
        if patterns:
            st.markdown(f"**{len(patterns)} patterns extracted**")
            for p in patterns:
                name = p.get("name", "Unnamed")
                topic = p.get("topic", "")
                conf = p.get("confidence", "LOW")
                st.markdown(f"- **{name}** ({topic}) \u2014 {conf}")

    elif agent == "create":
        if data.get("content"):
            copyable_text(data["content"])
        if data.get("word_count"):
            st.caption(f"Word count: {data['word_count']}")

    elif agent == "review":
        overall = data.get("overall_score")
        if overall is not None:
            st.metric("Overall Score", f"{overall}/10")
        dimensions = data.get("dimensions", [])
        if dimensions:
            cols = st.columns(min(len(dimensions), 4))
            for i, dim in enumerate(dimensions):
                with cols[i % len(cols)]:
                    st.metric(dim.get("name", "?"), f"{dim.get('score', '?')}/10")
        if data.get("top_strengths"):
            st.markdown("**Strengths**: " + ", ".join(data["top_strengths"]))
        if data.get("improvements"):
            st.markdown("**Improvements**:")
            for imp in data["improvements"]:
                st.markdown(f"- {imp}")

    elif agent == "email":
        if data.get("subject"):
            st.markdown(f"**Subject**: {data['subject']}")
        if data.get("body"):
            copyable_text(data["body"])

    elif agent == "coaching":
        if data.get("message"):
            st.markdown(data["message"])
        if data.get("action_items"):
            st.markdown("**Action Items**:")
            for item in data["action_items"]:
                st.markdown(f"- {item}")

    elif agent == "prioritize":
        if data.get("summary"):
            st.markdown(data["summary"])
        tasks = data.get("prioritized_tasks", data.get("tasks", []))
        if tasks:
            for t in tasks:
                name = t.get("name", t.get("task", "?"))
                score = t.get("score", "?")
                st.markdown(f"- **{name}** \u2014 Score: {score}")

    elif agent == "pipeline":
        result = data.get("result", "")
        if result:
            copyable_text(str(result))

    else:
        # Generic fallback
        copyable_output(data)


# --- Page header ---
st.title(":material/chat: Chat")
st.caption("Talk to your Second Brain agents")

# --- Agent selector in sidebar ---
with st.sidebar:
    st.subheader("Agent")
    agent_keys = list(AGENTS.keys())
    agent_labels = [f"{AGENTS[k]['icon']} {AGENTS[k]['name']}" for k in agent_keys]
    selected_idx = st.radio(
        "Select an agent",
        range(len(agent_keys)),
        format_func=lambda i: agent_labels[i],
        label_visibility="collapsed",
    )
    agent_key = agent_keys[selected_idx]
    agent_config = AGENTS[agent_key]
    st.caption(agent_config["description"])

# --- Initialize chat history per agent ---
history_key = f"chat_history_{agent_key}"
if history_key not in st.session_state:
    st.session_state[history_key] = []

# --- Extra fields (above chat input) ---
extra_values = {}
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
                # Dynamic content type selector
                try:
                    ct_data = get_content_types()
                    options = [ct["slug"] for ct in ct_data.get("content_types", [])]
                except Exception:
                    options = ["linkedin", "email", "landing-page", "comment", "case-study",
                               "proposal", "one-pager", "presentation", "instagram", "essay"]
                default_val = field_config["default"]
                default_idx = options.index(default_val) if default_val and default_val in options else 0
                extra_values[field_name] = st.selectbox(
                    field_config["label"],
                    options=options,
                    index=default_idx,
                    key=f"extra_{agent_key}_{field_name}",
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
            _format_agent_response(agent_key, msg["content"])

# --- Chat input ---
user_input = st.chat_input(agent_config["input_label"])

if user_input:
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
                _format_agent_response(agent_key, response)
                st.session_state[history_key].append({"role": "assistant", "content": response})
            except Exception as e:
                error_msg = f"Error: {e}"
                st.error(error_msg)
                st.session_state[history_key].append({"role": "assistant", "content": error_msg})
