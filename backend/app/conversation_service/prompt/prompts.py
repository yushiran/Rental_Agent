import opik
from loguru import logger
import os
from jinja2 import Environment, FileSystemLoader
from typing import Optional


class Prompt:
    """
    Unified Prompt class that combines template management and Opik versioning.
    Supports both inline prompts and Jinja2 template files.
    """
    
    # Class-level template environment (shared across all instances)
    _template_env = None
    _prompt_dir = "app/conversation_service/prompt/scripts"
    
    @classmethod
    def _get_template_env(cls):
        """Get or create the shared Jinja2 environment."""
        if cls._template_env is None:
            cls._template_env = Environment(
                loader=FileSystemLoader(cls._prompt_dir), 
                autoescape=False
            )
        return cls._template_env
    
    @classmethod
    def set_prompt_dir(cls, prompt_dir: str):
        """Set the global prompt directory and reset the template environment."""
        cls._prompt_dir = prompt_dir
        cls._template_env = None  # Force recreation with new directory
    
    def __init__(self, name: str, prompt: str = None, template_path: str = None) -> None:
        self.name = name
        self.template_path = template_path
        
        # If template_path is provided, use template-based approach
        if template_path:
            self._use_template = True
            self.__prompt = None  # Will be loaded on demand
        else:
            self._use_template = False
            try:
                self.__prompt = opik.Prompt(name=name, prompt=prompt)
            except Exception:
                logger.warning(
                    f"Can't use Opik to version the prompt '{name}' (probably due to missing or invalid credentials). "
                    "Falling back to local prompt. The prompt is not versioned, but it's still usable."
                )
                self.__prompt = prompt

    def get_prompt(self, **kwargs) -> str:
        """Get the prompt text, optionally rendered with template variables."""
        if self._use_template:
            template = self._get_template_env().get_template(self.template_path)
            return template.render(**kwargs)
        else:
            if isinstance(self.__prompt, opik.Prompt):
                return self.__prompt.prompt
            else:
                return self.__prompt

    @property
    def prompt(self) -> str:
        """Get the raw prompt text (for backward compatibility)."""
        if self._use_template:
            # For template-based prompts, return template path info
            return f"Template: {self.template_path}"
        else:
            if isinstance(self.__prompt, opik.Prompt):
                return self.__prompt.prompt
            else:
                return self.__prompt

    def __str__(self) -> str:
        return self.prompt

    def __repr__(self) -> str:
        mode = "template" if self._use_template else "inline"
        path_info = self.template_path if self._use_template else "inline"
        return f"Prompt(name='{self.name}', mode='{mode}', path='{path_info}')"
    
# ===== RENTAL AGENT PROMPTS =====

# --- Landlord Agent ---
LANDLORD_AGENT_PROMPT = Prompt(
    name="landlord_agent_prompt",
    template_path="landlord/landlord_prompt.jinja",
)

# --- Tenant Agent ---
TENANT_AGENT_PROMPT = Prompt(
    name="tenant_agent_prompt",
    template_path="tenant/tenant_prompt.jinja",
)

# --- Property Matching ---
PROPERTY_MATCHING_PROMPT = Prompt(
    name="property_matching_prompt",
    template_path="tools/property_matching_prompt.jinja",
)

# --- Summary ---
RENTAL_SUMMARY_PROMPT = Prompt(
    name="rental_summary_prompt",
    template_path="tools/rental_summary_prompt.jinja",
)

PROPERTY_CONTEXT_SUMMARY_PROMPT = Prompt(
    name="property_context_summary_prompt",
    template_path="tools/property_context_summary_prompt.jinja",
)

# --- Property Viewing Feedback ---
VIEWING_FEEDBACK_ANALYSIS_PROMPT = Prompt(
    name="viewing_feedback_analysis_prompt",
    template_path="tools/viewing_feedback_analysis_prompt.jinja",
)

MARKET_ANALYSIS_PROMPT = Prompt(
    name="market_analysis_prompt",
    template_path="tools/market_analysis_prompt.jinja",
)

META_CONTROLLER_SHOULD_CONTINUE_PROMPT = Prompt(
    name="meta_controller_should_continue_prompt",
    template_path="tools/should_continue.jinja",
)
