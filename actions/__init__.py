"""ComfyUI Bot Actions Module

This module contains all the action handlers for different ComfyUI operations.
"""

from .base_job import ComfyJob, Status
from .dream import dream, DrawJob, extract_loras, round_to_multiple
from .upscale import upscale, UpscaleJob

__all__ = [
    # Base classes
    'ComfyJob',
    'Status',
    
    # Dream operations
    'dream',
    'DrawJob',
    'extract_loras',
    'round_to_multiple',
    
    # Upscale operations
    'upscale',
    'UpscaleJob',
]
