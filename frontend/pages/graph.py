"""Knowledge Graph Explorer — interactive visualization of brain relationships."""

import logging

import streamlit as st
from api_client import graph_search, graph_health, graph_episodes

logger = logging.getLogger(__name__)
from components.copy_button import copyable_text
from components.graph_utils import relationships_to_graph

st.title("Knowledge Graph")

# Check graph availability
try:
    health = graph_health()
except Exception:
    logger.exception("Failed to check graph status")
    st.error("Failed to check graph status. Please try again.")
    health = {"status": "unavailable"}

status = health.get("status", "unavailable")
backend = health.get("backend", "none")

if status == "disabled" or backend == "none":
    st.warning("Knowledge graph is not enabled. Set `GRAPHITI_ENABLED=true` in your `.env` file.")
    st.info("The graph explorer requires a running FalkorDB or Neo4j instance.")
    st.stop()

# Status indicator
status_colors = {"healthy": "green", "degraded": "orange", "unavailable": "red"}
st.markdown(
    f"**Status**: :{status_colors.get(status, 'red')}_circle: {status} | "
    f"**Backend**: `{backend}`"
)

if health.get("error"):
    logger.warning("Graph health error: %s", health["error"])
    st.warning("Graph service reported an error. Check logs for details.")

st.divider()

# Tabs
tab_search, tab_episodes = st.tabs(["Search", "Episodes"])

with tab_search:
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("Search relationships", placeholder="What concepts are you looking for?")
    with col2:
        limit = st.slider("Max results", min_value=5, max_value=100, value=25)

    if query:
        with st.spinner("Searching knowledge graph..."):
            try:
                result = graph_search(query, limit=limit)
                relationships = result.get("results", [])
                count = result.get("count", 0)

                st.subheader(f"Found {count} relationships")

                if relationships:
                    # Render interactive graph
                    graph_data = relationships_to_graph(relationships)

                    try:
                        from st_link_analysis import st_link_analysis, NodeStyle, EdgeStyle

                        node_styles = [
                            NodeStyle("entity", "#7C3AED", "label", "circle"),
                        ]
                        edge_styles = [
                            EdgeStyle("*", labeled=True, directed=True),
                        ]

                        selected = st_link_analysis(
                            graph_data,
                            "cose",  # force-directed layout
                            node_styles,
                            edge_styles,
                            key="graph_search",
                        )

                        # Show selected element details
                        if selected and selected.get("selected"):
                            st.subheader("Selected")
                            st.json(selected["selected"])

                    except ImportError:
                        st.warning("Install `st-link-analysis` for interactive graph: `pip install st-link-analysis`")
                        # Fallback: text list
                        for rel in relationships:
                            st.markdown(
                                f"- **{rel.get('source', '?')}** "
                                f"--[{rel.get('relationship', '?')}]--> "
                                f"**{rel.get('target', '?')}**"
                            )

                    # Relationship table
                    with st.expander("Relationship Table"):
                        import pandas as pd
                        df = pd.DataFrame(relationships)
                        st.dataframe(df, use_container_width=True)

                    # Raw JSON
                    with st.expander("Raw JSON"):
                        import json
                        copyable_text(json.dumps(result, indent=2, default=str))

                else:
                    st.info("No relationships found. Try a different query.")

            except Exception:
                logger.exception("Graph search failed")
                st.error("Graph search failed. Please try again.")

with tab_episodes:
    st.subheader("Graph Episodes")
    st.caption("Episodes are content ingested into the knowledge graph.")

    group_id = st.text_input("Filter by group ID (optional)", key="ep_group")

    if st.button("Load Episodes", type="primary"):
        with st.spinner("Loading episodes..."):
            try:
                result = graph_episodes(group_id=group_id or None)
                episodes = result.get("episodes", [])
                count = result.get("count", 0)

                st.subheader(f"{count} episodes")

                if episodes:
                    for i, ep in enumerate(episodes):
                        content = ep.get("content", "No content")
                        ep_id = ep.get("id", f"Episode {i+1}")
                        source = ep.get("source", "unknown")
                        created = ep.get("created_at", "")

                        title = content[:80] + ("..." if len(content) > 80 else "")
                        with st.expander(f"{title}", expanded=i < 3):
                            st.markdown(content)
                            copyable_text(content)

                            meta_cols = st.columns(3)
                            with meta_cols[0]:
                                st.caption(f"**ID**: `{ep_id[:12]}...`")
                            with meta_cols[1]:
                                st.caption(f"**Source**: {source}")
                            with meta_cols[2]:
                                if created:
                                    st.caption(f"**Created**: {str(created)[:10]}")
                else:
                    st.info("No episodes found. Ingest some content first.")

            except Exception:
                logger.exception("Failed to load episodes")
                st.error("Failed to load episodes. Please try again.")
