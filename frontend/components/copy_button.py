"""Copy-to-clipboard component wrapper.

Uses Streamlit's built-in st.code() copy button (available since 1.28+).
No third-party packages needed.
"""

import json

import streamlit as st


def copyable_text(text: str, language: str | None = None):
    """Display text with a built-in copy button via st.code().

    Args:
        text: The text content to display and make copyable
        language: Optional language for syntax highlighting
    """
    st.code(text, language=language)


def copyable_output(output: dict, key_fields: list[str] | None = None):
    """Display a structured agent output with copy buttons on key fields.

    Args:
        output: Agent response dict
        key_fields: Specific fields to make copyable. If None, copies the full output.
    """
    if key_fields:
        for field in key_fields:
            value = output.get(field)
            if value and isinstance(value, str):
                st.markdown(f"**{field.replace('_', ' ').title()}**")
                st.code(value)
    else:
        full_text = json.dumps(output, indent=2, default=str)
        st.code(full_text, language="json")
