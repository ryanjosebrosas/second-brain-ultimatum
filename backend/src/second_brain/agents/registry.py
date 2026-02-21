"""Agent routing registry for pipeline orchestration."""

from typing import Any


def get_agent_registry() -> dict[str, tuple[Any, str]]:
    """Get the agent registry mapping route names to agent instances.

    Lazy-loaded to avoid circular imports. Each agent module is imported
    only when the registry is first requested.

    Returns:
        Dict mapping AgentRoute string to (agent_instance, description) tuples.
    """
    from second_brain.agents.recall import recall_agent
    from second_brain.agents.ask import ask_agent
    from second_brain.agents.learn import learn_agent
    from second_brain.agents.create import create_agent
    from second_brain.agents.review import review_agent
    from second_brain.agents.chief_of_staff import chief_of_staff  # noqa: F401

    registry: dict[str, tuple[Any, str]] = {
        "recall": (recall_agent, "Semantic memory search"),
        "ask": (ask_agent, "Contextual Q&A with brain knowledge"),
        "learn": (learn_agent, "Pattern extraction and learning"),
        "create": (create_agent, "Content creation with voice and patterns"),
        "review": (review_agent, "Single-dimension content review"),
    }

    # Lazily add new agents as they become available
    try:
        from second_brain.agents.clarity import clarity_agent
        registry["clarity"] = (clarity_agent, "Content clarity analysis")
    except ImportError:
        pass
    try:
        from second_brain.agents.synthesizer import synthesizer_agent
        registry["synthesizer"] = (synthesizer_agent, "Feedback consolidation")
    except ImportError:
        pass
    try:
        from second_brain.agents.template_builder import template_builder_agent
        registry["template_builder"] = (template_builder_agent, "Template identification")
    except ImportError:
        pass
    try:
        from second_brain.agents.coach import coach_agent
        registry["coach"] = (coach_agent, "Daily accountability coaching")
    except ImportError:
        pass
    try:
        from second_brain.agents.pmo import pmo_agent
        registry["pmo"] = (pmo_agent, "Priority advisory")
    except ImportError:
        pass
    try:
        from second_brain.agents.email_agent import email_agent
        registry["email"] = (email_agent, "Email operations")
    except ImportError:
        pass
    try:
        from second_brain.agents.specialist import specialist_agent
        registry["specialist"] = (specialist_agent, "Claude Code expertise")
    except ImportError:
        pass
    try:
        from second_brain.agents.hook_writer import hook_writer_agent
        registry["hook_writer"] = (hook_writer_agent, "LinkedIn hook generation")
    except ImportError:
        pass

    return registry
