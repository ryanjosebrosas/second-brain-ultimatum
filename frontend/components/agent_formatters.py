"""Agent response formatters.

Each agent has a dedicated formatter function. The dispatch dict maps agent keys
to their formatters. Unknown agents fall through to a generic formatter.
"""

from typing import Any

import streamlit as st

from components.copy_button import copyable_text, copyable_output


def _format_recall(data: dict[str, Any]) -> None:
    """Format recall agent response with summary, matches, patterns, and relations."""
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
            st.markdown(
                f"- {r.get('source', '?')} \u2192 *{r.get('relationship', '?')}* "
                f"\u2192 {r.get('target', '?')}"
            )


def _format_ask(data: dict[str, Any]) -> None:
    """Format ask agent response."""
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


def _format_learn(data: dict[str, Any]) -> None:
    """Format learn agent response with extracted patterns."""
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


def _format_create(data: dict[str, Any]) -> None:
    """Format create agent response with generated content."""
    if data.get("content"):
        copyable_text(data["content"])
    if data.get("word_count"):
        st.caption(f"Word count: {data['word_count']}")


def _format_review(data: dict[str, Any]) -> None:
    """Format review agent response with dimension scores."""
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


def _format_email(data: dict[str, Any]) -> None:
    """Format email agent response."""
    if data.get("subject"):
        st.markdown(f"**Subject**: {data['subject']}")
    if data.get("body"):
        copyable_text(data["body"])


def _format_coaching(data: dict[str, Any]) -> None:
    """Format coaching agent response."""
    if data.get("message"):
        st.markdown(data["message"])
    if data.get("action_items"):
        st.markdown("**Action Items**:")
        for item in data["action_items"]:
            st.markdown(f"- {item}")


def _format_prioritize(data: dict[str, Any]) -> None:
    """Format PMO prioritize agent response."""
    if data.get("summary"):
        st.markdown(data["summary"])
    tasks = data.get("prioritized_tasks", data.get("tasks", []))
    if tasks:
        for t in tasks:
            name = t.get("name", t.get("task", "?"))
            score = t.get("score", "?")
            st.markdown(f"- **{name}** \u2014 Score: {score}")


def _format_pipeline(data: dict[str, Any]) -> None:
    """Format pipeline (multi-agent) response."""
    result = data.get("result", "")
    if result:
        copyable_text(str(result))
    else:
        copyable_output(data)


def _format_generic(data: dict[str, Any]) -> None:
    """Generic fallback formatter for agents without a dedicated formatter."""
    copyable_output(data)


# Dispatch dict: agent_key -> formatter function
AGENT_FORMATTERS: dict[str, Any] = {
    "recall": _format_recall,
    "ask": _format_ask,
    "learn": _format_learn,
    "create": _format_create,
    "review": _format_review,
    "email": _format_email,
    "coaching": _format_coaching,
    "prioritize": _format_prioritize,
    "pipeline": _format_pipeline,
    # clarity, synthesize, templates, specialist -> fall through to _format_generic
}


def format_agent_response(agent: str, data: str | dict[str, Any]) -> None:
    """Format and display an agent response.

    Args:
        agent: The agent key from config.AGENTS (e.g., "recall", "ask").
        data: The agent's response -- either a string or a dict.
    """
    if isinstance(data, str):
        st.markdown(data)
        return

    if not isinstance(data, dict):
        st.write(data)
        return

    formatter = AGENT_FORMATTERS.get(agent, _format_generic)
    formatter(data)
