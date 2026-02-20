"""Settings — system configuration and provider status."""

import logging

import streamlit as st
from api_client import get_settings_config, get_settings_providers, get_health

logger = logging.getLogger(__name__)

st.title("Settings")

tab_providers, tab_config, tab_status = st.tabs(["Providers", "Configuration", "System Status"])

with tab_providers:
    st.subheader("Active Providers")

    try:
        providers = get_settings_providers()
    except Exception:
        logger.exception("Failed to load providers")
        st.error("Failed to load providers. Please try again.")
        providers = {}

    if providers:
        # Model provider
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### LLM Provider")
            provider = providers.get("model_provider", "unknown")
            model = providers.get("model_name", "default")
            st.metric("Provider", provider)
            if model:
                st.caption(f"Model: `{model}`")

        with col2:
            st.markdown("#### Memory Provider")
            mem_provider = providers.get("memory_provider", "unknown")
            st.metric("Provider", mem_provider)
            graphiti = providers.get("graphiti_enabled", False)
            if graphiti:
                st.caption(f"Graphiti: enabled ({providers.get('graph_provider', 'none')})")
            else:
                st.caption("Graphiti: disabled")

        st.divider()

        # Embedding info
        st.markdown("#### Embeddings")
        emb_model = providers.get("embedding_model", "unknown")
        voyage = providers.get("voyage_available", False)
        st.markdown(f"Model: `{emb_model}`")
        st.markdown(f"Voyage AI: {'Available' if voyage else 'Not configured'}")

        st.divider()

        # Service instances
        st.markdown("#### Active Services")
        services = providers.get("services", {})
        if services:
            for svc_name, class_name in services.items():
                if class_name:
                    st.markdown(f"- **{svc_name.replace('_', ' ').title()}**: `{class_name}`")
                else:
                    st.markdown(f"- **{svc_name.replace('_', ' ').title()}**: *Not configured*")

with tab_config:
    st.subheader("System Configuration")
    st.caption("API keys are redacted for security.")

    try:
        config = get_settings_config()
    except Exception:
        logger.exception("Failed to load config")
        st.error("Failed to load configuration. Please try again.")
        config = {}

    if config:
        # Group config by category
        groups = {
            "LLM": ["model_provider", "model_name", "model_fallback_chain", "primary_model", "fallback_model"],
            "Memory": ["memory_provider", "graph_provider", "graphiti_enabled"],
            "Embeddings": ["embedding_model", "embedding_dimensions", "embedding_batch_size"],
            "Search": ["memory_search_limit", "graph_search_limit", "pattern_context_limit", "experience_limit"],
            "Timeouts": ["api_timeout_seconds", "service_timeout_seconds", "mcp_review_timeout_multiplier"],
            "Brain": ["brain_user_id", "brain_data_path"],
            "Server": ["mcp_transport", "mcp_host", "mcp_port", "api_port", "frontend_url"],
            "Quality": ["quality_gate_score", "confidence_downgrade_threshold", "stale_pattern_days"],
            "Agent": ["agent_max_retries", "agent_request_limit", "pipeline_request_limit"],
        }

        for group_name, fields in groups.items():
            with st.expander(group_name, expanded=group_name in ("LLM", "Memory")):
                for field in fields:
                    value = config.get(field)
                    if value is not None:
                        display = "***" if value == "***" else str(value)
                        st.markdown(f"**{field}**: `{display}`")

        # Show remaining fields not in groups
        grouped_fields = set()
        for fields in groups.values():
            grouped_fields.update(fields)

        remaining = {k: v for k, v in config.items() if k not in grouped_fields and v is not None}
        if remaining:
            with st.expander("Other"):
                for field, value in sorted(remaining.items()):
                    display = "***" if value == "***" else str(value)
                    st.markdown(f"**{field}**: `{display}`")

with tab_status:
    st.subheader("System Status")

    try:
        health = get_health()
    except Exception:
        logger.exception("Failed to load health data")
        st.error("Failed to load health data. Please try again.")
        health = {}

    if health:
        # Core metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Memories", health.get("memory_count", 0))
        with col2:
            st.metric("Patterns", health.get("total_patterns", 0))
        with col3:
            st.metric("Status", health.get("status", "unknown"))

        # Errors
        errors = health.get("errors", [])
        if errors:
            st.warning(f"{len(errors)} error(s) detected:")
            for err in errors:
                st.markdown(f"- {err}")

        # Graph status
        graphiti_status = health.get("graphiti_status", "disabled")
        graphiti_backend = health.get("graphiti_backend", "none")
        st.divider()
        st.markdown(f"**Graph**: {graphiti_status} (backend: `{graphiti_backend}`)")
