"""Second Brain — Interactive Frontend."""

import streamlit as st

st.set_page_config(
    page_title="Second Brain",
    page_icon=":brain:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Define pages
chat_page = st.Page("pages/chat.py", title="Chat", icon=":material/chat:", default=True)
memory_page = st.Page("pages/memory.py", title="Memory", icon=":material/search:")
dashboard_page = st.Page("pages/dashboard.py", title="Dashboard", icon=":material/dashboard:")
content_page = st.Page("pages/content.py", title="Content", icon=":material/edit:")
projects_page = st.Page("pages/projects.py", title="Projects", icon=":material/folder:")
graph_page = st.Page("pages/graph.py", title="Graph", icon=":material/hub:")
settings_page = st.Page("pages/settings.py", title="Settings", icon=":material/settings:")

# Navigation
pg = st.navigation({
    "Main": [chat_page, memory_page],
    "Tools": [content_page, projects_page],
    "Insights": [dashboard_page, graph_page],
    "System": [settings_page],
})

# Sidebar branding + connection status
with st.sidebar:
    st.markdown("### :brain: Second Brain")
    st.caption("Your AI-powered knowledge system")
    try:
        import httpx
        from config import FASTAPI_URL
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(f"{FASTAPI_URL}/api/health/metrics")
            if resp.status_code == 200:
                st.success("API Connected", icon=":material/check_circle:")
            else:
                st.warning(f"API Error ({resp.status_code})", icon=":material/warning:")
    except Exception:
        st.error("API Offline", icon=":material/error:")
        st.caption("Start the API server first")
    st.divider()

pg.run()
