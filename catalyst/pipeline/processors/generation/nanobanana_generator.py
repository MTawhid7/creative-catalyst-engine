# catalyst/pipeline/processors/generation/nanobanana_generator.py

import asyncio
import json
import re
import io
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image

from .base_generator import BaseImageGenerator
from catalyst.context import RunContext
from catalyst import settings


class NanoBananaGeneration(BaseImageGenerator):
    """
    An image generation strategy that uses the Google Gemini Image Preview API.
    It generates all images (final garment and mood board) in parallel.
    """

    def __init__(self):
        super().__init__()
        self.client = None

        if not settings.GEMINI_API_KEY:
            self.logger.critical(
                "❌ CRITICAL: GEMINI_API_KEY not set. Nano Banana generator is disabled."
            )
            return

        try:
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
            self.logger.info(
                "✅ Google Gemini (Nano Banana) client configured successfully."
            )
        except Exception as e:
            self.logger.critical(
                f"❌ CRITICAL: Failed to configure Gemini client: {e}", exc_info=True
            )
            self.client = None

    async def generate_images(self, context: RunContext) -> RunContext:
        """
        Creates and runs image generation tasks in parallel using the Gemini API.
        """
        if not self.client:
            self.logger.error(
                "❌ Halting generation: Gemini client was not initialized."
            )
            return context

        self.logger.info("🍌 Activating Nano Banana (Gemini) generation strategy...")

        prompts_data = self._load_prompts_from_file(context)
        if not prompts_data:
            self.logger.error("❌ Could not load prompts. Halting generation.")
            return context

        tasks = []
        # --- START OF MOOD BOARD FIX ---
        for garment_name, prompts in prompts_data.items():
            for prompt_type, prompt_text in prompts.items():
                if not prompt_text:
                    self.logger.warning(
                        f"⚠️ No prompt text found for '{prompt_type}' on '{garment_name}'. Skipping."
                    )
                    continue
                task = self._generate_and_save_image(
                    prompt_text, garment_name, context, prompt_type
                )
                tasks.append(task)
        # --- END OF MOOD BOARD FIX ---

        if not tasks:
            self.logger.warning("No valid image generation tasks were created.")
            return context

        self.logger.info(
            f"🚀 Launching {len(tasks)} image generation tasks in parallel..."
        )
        await asyncio.gather(*tasks)

        self.logger.info("✅ Nano Banana (Gemini) image generation complete.")
        return context

    async def _generate_and_save_image(
        self, prompt: str, garment_name: str, context: RunContext, prompt_type: str
    ):
        """Generates a single image using Gemini and saves it with a typed filename."""
        self.logger.info(
            f"Cleaning prompt for Gemini: '{garment_name}' ({prompt_type})..."
        )
        cleaned_prompt = re.sub(r"\*\*.*?\*\*|^- ", "", prompt, flags=re.MULTILINE)
        cleaned_prompt = cleaned_prompt.replace("\n", " ")
        cleaned_prompt = " ".join(cleaned_prompt.split())

        self.logger.info(f"Generating image for: '{garment_name}' ({prompt_type})...")
        try:
            client = self.client
            if client is None:
                self.logger.error("❌ Gemini client is not available; aborting task.")
                return

            response = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.5-flash-image-preview",
                contents=cleaned_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"]
                ),
            )

            if (
                response.candidates
                and response.candidates[0].content
                and response.candidates[0].content.parts
            ):
                image_part = next(
                    (
                        p
                        for p in response.candidates[0].content.parts
                        if hasattr(p, "inline_data")
                    ),
                    None,
                )

                if (
                    image_part
                    and image_part.inline_data
                    and image_part.inline_data.data
                ):
                    image_bytes = image_part.inline_data.data
                    image = Image.open(io.BytesIO(image_bytes))

                    slug = "".join(
                        c for c in garment_name.lower() if c.isalnum() or c in " -"
                    ).replace(" ", "-")

                    # --- START OF MOOD BOARD FIX ---
                    if prompt_type == "mood_board":
                        image_filename = f"{slug}-moodboard.png"
                    else:
                        image_filename = f"{slug}.png"
                    # --- END OF MOOD BOARD FIX ---

                    image_path = Path(context.results_dir) / image_filename

                    image.save(image_path, "PNG")
                    self.logger.info(f"✅ Successfully saved image to '{image_path}'")
                else:
                    self.logger.error(
                        f"❌ Gemini API call for '{garment_name}' returned no image data."
                    )
            else:
                self.logger.error(
                    f"❌ Gemini API call for '{garment_name}' returned no candidates. Prompt may have been blocked."
                )

        except Exception as e:
            self.logger.error(
                f"❌ Gemini API call failed for '{garment_name}': {e}", exc_info=True
            )

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
            self.logger.error(
                "❌ Could not load or parse prompts from file.", exc_info=True
            )
            return {}
