"""Memory Browser page — Search, filter, and browse brain memory."""

import json

import streamlit as st

from config import MEMORY_TABLES
from api_client import search_memory, semantic_search, vector_search, delete_item
from components.copy_button import copyable_text

st.title(":material/search: Memory Browser")
st.caption("Search and browse your brain's memory stores")

# --- Search mode selector ---
search_mode = st.radio(
    "Search Mode",
    ["Browse Tables", "Semantic Search", "Vector Search"],
    horizontal=True,
)

st.divider()

if search_mode == "Browse Tables":
    # --- Table selector ---
    table_keys = list(MEMORY_TABLES.keys())
    table_labels = [f"{MEMORY_TABLES[k]['icon']} {MEMORY_TABLES[k]['name']}" for k in table_keys]

    selected_table_idx = st.selectbox(
        "Table",
        range(len(table_keys)),
        format_func=lambda i: table_labels[i],
    )
    table_key = table_keys[selected_table_idx]
    table_config = MEMORY_TABLES[table_key]

    # --- Filters ---
    filter_params = {}
    if table_config["filters"]:
        cols = st.columns(len(table_config["filters"]))
        for i, (filter_name, filter_config) in enumerate(table_config["filters"].items()):
            with cols[i]:
                if filter_config.get("type") == "select_fixed":
                    options = filter_config["options"]
                    val = st.selectbox(
                        filter_config["label"],
                        options=options,
                        key=f"filter_{table_key}_{filter_name}",
                    )
                    if val:
                        filter_params[filter_name] = val
                else:
                    val = st.text_input(
                        filter_config["label"],
                        key=f"filter_{table_key}_{filter_name}",
                    )
                    if val:
                        filter_params[filter_name] = val

    # --- Fetch and display results ---
    if st.button("Search", type="primary", key="browse_search"):
        with st.spinner("Searching..."):
            try:
                data = search_memory(table_config["endpoint"], filter_params)
                # Extract the results list (key varies: patterns, examples, knowledge, experiences)
                results = data.get(table_key, data.get("items", []))
                if not results:
                    # Try other common keys
                    for k, v in data.items():
                        if isinstance(v, list):
                            results = v
                            break

                count = data.get("count", len(results))
                st.info(f"Found {count} results")

                for i, item in enumerate(results):
                    # Build title from available fields
                    title = item.get("name") or item.get("title") or item.get("category", f"Item {i+1}")
                    with st.expander(f"{title}", expanded=False):
                        # Display configured fields
                        for field in table_config["display_fields"]:
                            value = item.get(field)
                            if value is not None:
                                label = field.replace("_", " ").title()
                                if isinstance(value, str) and len(value) > 200:
                                    st.markdown(f"**{label}**:")
                                    copyable_text(value)
                                elif isinstance(value, list):
                                    st.markdown(f"**{label}**: {', '.join(str(v) for v in value)}")
                                else:
                                    st.markdown(f"**{label}**: {value}")

                        # Delete button
                        item_id = item.get("id")
                        if item_id:
                            # Map table key to API delete table name
                            delete_table = table_key.rstrip("s")  # patterns -> pattern, etc.
                            if st.button(
                                "Delete",
                                key=f"delete_{table_key}_{item_id}_{i}",
                                type="secondary",
                            ):
                                try:
                                    delete_item(delete_table, item_id)
                                    st.success("Deleted!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Delete failed: {e}")

            except Exception as e:
                st.error(f"Search failed: {e}")

elif search_mode == "Semantic Search":
    st.markdown("Search Mem0 semantic memory using the Recall agent.")
    query = st.text_input("Search query", key="semantic_query")

    if st.button("Search", type="primary", key="semantic_search_btn"):
        if not query:
            st.warning("Enter a search query")
        else:
            with st.spinner("Searching semantic memory..."):
                try:
                    data = semantic_search(query)
                    if data.get("summary"):
                        st.markdown(f"**Summary**: {data['summary']}")
                    matches = data.get("matches", [])
                    st.info(f"Found {len(matches)} matches")
                    for i, m in enumerate(matches):
                        relevance = m.get("relevance", "MEDIUM")
                        with st.expander(f"Match {i+1} — {relevance} relevance"):
                            copyable_text(m.get("content", ""))
                            if m.get("source"):
                                st.caption(f"Source: {m['source']}")
                    patterns = data.get("patterns", [])
                    if patterns:
                        st.markdown("**Related Patterns**: " + ", ".join(patterns))
                except Exception as e:
                    st.error(f"Semantic search failed: {e}")

elif search_mode == "Vector Search":
    st.markdown("Search using pgvector similarity on Supabase tables.")
    query = st.text_input("Search query", key="vector_query")

    col1, col2 = st.columns(2)
    with col1:
        table = st.selectbox(
            "Table",
            ["memory_content", "pattern_registry", "content_examples", "knowledge_repo"],
            key="vector_table",
        )
    with col2:
        limit = st.slider("Max results", 1, 50, 10, key="vector_limit")

    if st.button("Search", type="primary", key="vector_search_btn"):
        if not query:
            st.warning("Enter a search query")
        else:
            with st.spinner("Running vector search..."):
                try:
                    data = vector_search(query, table=table, limit=limit)
                    results = data.get("results", [])
                    st.info(f"Found {len(results)} results")
                    for i, item in enumerate(results):
                        title = item.get("title") or item.get("name") or f"Result {i+1}"
                        similarity = item.get("similarity", "")
                        sim_str = f" (similarity: {similarity:.4f})" if isinstance(similarity, (int, float)) else ""
                        with st.expander(f"{title}{sim_str}"):
                            content = item.get("content") or item.get("pattern_text") or ""
                            if content:
                                copyable_text(content)
                            # Show remaining fields
                            skip = {"content", "pattern_text", "title", "name", "similarity", "embedding"}
                            extras = {k: v for k, v in item.items() if k not in skip and v is not None}
                            if extras:
                                st.json(extras)
                except Exception as e:
                    st.error(f"Vector search failed: {e}")
