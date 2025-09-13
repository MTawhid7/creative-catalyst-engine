# catalyst/pipeline/processors/generation/base_generator.py

from abc import abstractmethod
from catalyst.context import RunContext

# --- START: DEFINITIVE TYPE HIERARCHY FIX ---
# Import the BaseProcessor to establish the correct inheritance.
from catalyst.pipeline.base_processor import BaseProcessor

# --- END: DEFINITIVE TYPE HIERARCHY FIX ---


class BaseImageGenerator(BaseProcessor):  # <-- THE CRITICAL CHANGE
    """
    Abstract Base Class for an image generation strategy.
    This now inherits from BaseProcessor to unify the pipeline interface.
    """

    # The __init__ is now inherited from BaseProcessor, so we don't need to repeat it.

    @abstractmethod
    async def process(self, context: RunContext) -> RunContext:  # <-- RENAME THE METHOD
        """
        The main method to generate and save images based on the context.
        The method is renamed from 'generate_images' to 'process' to conform
        to the BaseProcessor contract.
        """
        pass
