from catalyst import settings
from .base_generator import BaseImageGenerator
from .dalle3_generator import DalleImageGeneration
from .gpt_image1_generator import GptImage1Generation
from .nanobanana_generator import NanoBananaGeneration  # <-- ADD THIS IMPORT


def get_image_generator() -> BaseImageGenerator:
    """
    Factory function to select and return the configured image generator.
    Reads the model name from the settings.
    """
    model_name = settings.IMAGE_GENERATION_MODEL.lower()

    if model_name == "dall-e-3":
        return DalleImageGeneration()
    elif model_name == "gpt-image-1":
        return GptImage1Generation()
    elif model_name == "nano-banana":  # <-- ADD THIS BLOCK
        return NanoBananaGeneration()
    else:
        from catalyst.utilities.logger import get_logger

        logger = get_logger(__name__)
        logger.warning(
            f"Invalid IMAGE_GENERATION_MODEL '{model_name}'. Defaulting to 'dall-e-3'."
        )
        return DalleImageGeneration()
