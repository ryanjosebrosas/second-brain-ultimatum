"""Custom CSS injection for the Second Brain frontend."""

import streamlit as st


def inject_styles():
    """Inject custom CSS for dark-themed polished UX."""
    st.markdown("""
    <style>
    /* Chat message styling */
    .stChatMessage {
        border-radius: 12px;
        padding: 0.75rem;
        margin-bottom: 0.5rem;
    }

    /* Metric cards */
    [data-testid="stMetric"] {
        background-color: #1A1A2E;
        border: 1px solid #2D2D44;
        border-radius: 12px;
        padding: 1rem;
    }
    [data-testid="stMetricValue"] {
        color: #7C3AED;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #0D0D1A;
    }

    /* Button styling */
    .stButton > button {
        border-radius: 8px;
        border: 1px solid #7C3AED;
        background-color: transparent;
        color: #E5E5E5;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background-color: #7C3AED;
        color: white;
    }

    /* Primary button */
    .stButton > button[kind="primary"] {
        background-color: #7C3AED;
        color: white;
    }

    /* Expander styling */
    .streamlit-expanderHeader {
        background-color: #1A1A2E;
        border-radius: 8px;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #1A1A2E;
    }

    /* Divider */
    hr {
        border-color: #2D2D44;
    }

    /* Code block styling for copy buttons */
    .stCodeBlock {
        border: 1px solid #2D2D44;
        border-radius: 8px;
    }

    /* Agent selector radio styling */
    .stRadio > div {
        gap: 0.25rem;
    }
    </style>
    """, unsafe_allow_html=True)
