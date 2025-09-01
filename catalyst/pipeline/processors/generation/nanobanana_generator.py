# catalyst/pipeline/processors/generation/nanobanana_generator.py

import asyncio
import json
import re
import io
from pathlib import Path

# Gemini API and Image Handling
from google import genai
from PIL import Image

from .base_generator import BaseImageGenerator
from catalyst.context import RunContext
from catalyst import settings


class NanoBananaGeneration(BaseImageGenerator):
    """
    An image generation strategy that uses the Google Gemini 2.5 Flash Image Preview API.
    This implementation is nicknamed "Nano Banana".
    """

    def __init__(self):
        super().__init__()
        from catalyst.utilities.logger import get_logger
        self.logger = get_logger(self.__class__.__name__)
        self.client = None # Start with client as None

        # --- EAGER INITIALIZATION ---
        # Try to create the client immediately. If it fails, self.client remains None.
        if not settings.GEMINI_API_KEY:
            self.logger.critical("❌ CRITICAL: GEMINI_API_KEY is not set. Nano Banana generator will be disabled.")
            return

        try:
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
            self.logger.info("✅ Google Gemini (Nano Banana) client configured successfully.")
        except Exception as e:
            self.logger.critical(f"❌ CRITICAL: Failed to configure Gemini client: {e}", exc_info=True)
            self.client = None # Ensure client is None on failure

    async def generate_images(self, context: RunContext) -> RunContext:
        """
        Creates and runs image generation tasks in parallel using the Gemini API.
        """
        # --- GUARD CLAUSE ---
        # This is the safety check that prevents the "NoneType" error.
        if not self.client:
            self.logger.error("❌ Halting generation: Gemini client was not initialized. Check API key.")
            return context

        self.logger.info("🍌 Activating Nano Banana (Gemini 2.5 Flash Image) generation strategy...")

        if not context.final_report.get("detailed_key_pieces"):
            self.logger.warning("⚠️ No key pieces found in the report. Skipping image generation.")
            return context

        prompts_data = self._load_prompts_from_file(context)
        if not prompts_data:
            self.logger.error("❌ Could not load prompts. Halting generation.")
            return context

        tasks = []
        for garment_name, prompts in prompts_data.items():
            final_garment_prompt = prompts.get("final_garment")
            if not final_garment_prompt:
                continue
            tasks.append(self._generate_and_save_image(final_garment_prompt, garment_name, context))

        if not tasks:
            self.logger.warning("No valid image generation tasks were created.")
            return context

        self.logger.info(f"🚀 Launching {len(tasks)} image generation tasks in parallel...")
        await asyncio.gather(*tasks)

        self.logger.info("✅ Nano Banana (Gemini) image generation complete.")
        return context

    async def _generate_and_save_image(self, prompt: str, garment_name: str, context: RunContext):
        """Generates a single image using the specified Gemini image model and saves it."""

        self.logger.info(f"Cleaning prompt for Gemini: '{garment_name}'...")
        cleaned_prompt = re.sub(r"\*\*.*?\*\*|^- ", "", prompt, flags=re.MULTILINE)
        cleaned_prompt = cleaned_prompt.replace("\n", " ")
        cleaned_prompt = " ".join(cleaned_prompt.split())

        self.logger.info(f"Generating image for: '{garment_name}'...")
        try:
            # The client.models.generate_content call is synchronous, so we wrap it
            # in asyncio.to_thread to avoid blocking the event loop.
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model="gemini-2.5-flash-image-preview", # <-- The specified model
                contents=cleaned_prompt
            )

            if response.candidates:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    image_part = next((part for part in candidate.content.parts if hasattr(part, 'inline_data')), None)

                    if image_part and image_part.inline_data and image_part.inline_data.data:
                        image_bytes = image_part.inline_data.data
                        image = Image.open(io.BytesIO(image_bytes))

                        slug = "".join(c for c in garment_name.lower() if c.isalnum() or c in " -").replace(" ", "-")
                        image_filename = f"{slug}.png"
                        image_path = Path(context.results_dir) / image_filename

                        image.save(image_path, 'PNG')
                        self.logger.info(f"✅ Successfully saved image to '{image_path}'")
                    else:
                        self.logger.error(f"❌ Gemini API call for '{garment_name}' was successful but returned no image data.")
                else:
                    self.logger.error(f"❌ Gemini API call for '{garment_name}' returned no content parts.")
            else:
                self.logger.error(f"❌ Gemini API call for '{garment_name}' returned no candidates. Prompt may have been blocked.")

        except Exception as e:
            self.logger.error(f"❌ Gemini API call failed for '{garment_name}': {e}", exc_info=True)

    def _load_prompts_from_file(self, context: RunContext) -> dict:
        """A fallback to load prompts directly from the JSON file if needed."""
        try:
            prompts_path = Path(context.results_dir) / settings.PROMPTS_FILENAME
            if prompts_path.exists():
                with open(prompts_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                self.logger.warning(f"⚠️ Prompts file not found at {prompts_path}.")
                return {}
        except Exception:
            self.logger.error("❌ Could not load or parse prompts from file.", exc_info=True)
            return {}