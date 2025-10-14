# catalyst/pipeline/processors/generation/base_generator.py

from abc import abstractmethod
from typing import Optional
from catalyst.context import RunContext
from catalyst.pipeline.base_processor import BaseProcessor


class BaseImageGenerator(BaseProcessor):
    """
    Abstract Base Class for an image generation strategy.
    This now inherits from BaseProcessor to unify the pipeline interface.
    """

    @abstractmethod
    # --- START: HYBRID REGENERATION REFACTOR ---
    async def process(
        self,
        context: RunContext,
        seed_override: Optional[int] = None,
        temperature_override: Optional[float] = None,
    ) -> RunContext:
        # --- END: HYBRID REGENERATION REFACTOR ---
        """
        The main method to generate and save images based on the context.
        """
        pass
