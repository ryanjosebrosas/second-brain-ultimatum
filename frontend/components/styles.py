"""Frontend styles module.

All theming is handled via .streamlit/config.toml.
Do NOT use st.markdown with unsafe_allow_html=True for CSS injection.
"""


def inject_styles() -> None:
    """No-op. Styles are handled by .streamlit/config.toml.

    Kept as a no-op to avoid ImportError in any files that still import it.
    Will be fully removed once all imports are cleaned up.
    """
    pass
