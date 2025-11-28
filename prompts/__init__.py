# ============================================================================
# prompts/__init__.py
# ============================================================================

"""Prompt templates for LLM extraction"""

from .extraction_prompts import (
    get_main_extraction_prompt,
    get_validation_prompt,
    get_reconciliation_prompt,
    get_duplicate_detection_prompt,
    SYSTEM_PROMPT_EXTRACTION
)

__all__ = [
    'get_main_extraction_prompt',
    'get_validation_prompt',
    'get_reconciliation_prompt',
    'get_duplicate_detection_prompt',
    'SYSTEM_PROMPT_EXTRACTION'
]
