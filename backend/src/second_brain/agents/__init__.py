"""Second Brain agents — Pydantic AI agent definitions."""

from second_brain.agents.recall import recall_agent
from second_brain.agents.ask import ask_agent
from second_brain.agents.learn import learn_agent
from second_brain.agents.create import create_agent
from second_brain.agents.review import review_agent, run_full_review
from second_brain.agents.chief_of_staff import chief_of_staff
from second_brain.agents.utils import get_agent_registry, run_pipeline
from second_brain.agents.clarity import clarity_agent
from second_brain.agents.synthesizer import synthesizer_agent
from second_brain.agents.template_builder import template_builder_agent
from second_brain.agents.coach import coach_agent
from second_brain.agents.pmo import pmo_agent
from second_brain.agents.email_agent import email_agent
from second_brain.agents.specialist import specialist_agent

__all__ = [
    "recall_agent",
    "ask_agent",
    "learn_agent",
    "create_agent",
    "review_agent",
    "run_full_review",
    "chief_of_staff",
    "get_agent_registry",
    "run_pipeline",
    "clarity_agent",
    "synthesizer_agent",
    "template_builder_agent",
    "coach_agent",
    "pmo_agent",
    "email_agent",
    "specialist_agent",
]
