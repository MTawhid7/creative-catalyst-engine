# catalyst/pipeline/processors/generation/nanobanana_generator.py

import asyncio
import json
import re
import io
from pathlib import Path

from google import genai
from google.genai import types
from google.genai.types import HarmCategory, HarmBlockThreshold
from PIL import Image

from .base_generator import BaseImageGenerator
from catalyst.context import RunContext
from catalyst import settings

# --- START OF IMPROVEMENT ---
# Define constants for the retry mechanism to make it easily configurable.
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5
# --- END OF IMPROVEMENT ---


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
                "⚠ CRITICAL: GEMINI_API_KEY not set. Nano Banana generator is disabled."
            )
            return

        try:
            # Use the correct modern SDK pattern to create the client
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
            self.logger.info(
                "✅ Google Gemini (Nano Banana) client configured successfully."
            )
        except Exception as e:
            self.logger.critical(
                f"⚠ CRITICAL: Failed to configure Gemini client: {e}", exc_info=True
            )
            self.client = None

    async def generate_images(self, context: RunContext) -> RunContext:
        """
        Creates and runs image generation tasks in parallel using the Gemini API.
        """
        if not self.client:
            self.logger.error(
                "⚠ Halting generation: Gemini client was not initialized."
            )
            return context

        self.logger.info("🌀 Activating Nano Banana (Gemini) generation strategy...")

        prompts_data = self._load_prompts_from_file(context)
        if not prompts_data:
            self.logger.error("⚠ Could not load prompts. Halting generation.")
            return context

        tasks = []
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
        """
        Generates a single image using Gemini with retries and safety settings,
        then saves it with a typed filename.
        """
        cleaned_prompt = re.sub(r"\*\*.*?\*\*|^- ", "", prompt, flags=re.MULTILINE)
        cleaned_prompt = cleaned_prompt.replace("\n", " ")
        cleaned_prompt = " ".join(cleaned_prompt.split())

        # --- START OF RETRY & SAFETY SETTINGS IMPLEMENTATION ---
        for attempt in range(MAX_RETRIES):
            self.logger.info(
                f"Generating image for: '{garment_name}' ({prompt_type}) - Attempt {attempt + 1}/{MAX_RETRIES}..."
            )
            try:
                if not self.client:
                    self.logger.error(
                        "⚠ Gemini client is not available; aborting task."
                    )
                    return

                # Define safety settings to be less restrictive
                safety_settings = [
                    types.SafetySetting(
                        category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                        threshold=HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                        threshold=HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                        threshold=HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                        threshold=HarmBlockThreshold.BLOCK_NONE,
                    ),
                ]

                # Use the correct modern SDK pattern for image generation
                # CRITICAL: Must include response_modalities with both TEXT and IMAGE
                generation_config = types.GenerateContentConfig(
                    response_modalities=[
                        "TEXT",
                        "IMAGE",
                    ],  # Required for image generation
                    safety_settings=safety_settings,
                    temperature=0.7,  # Add some creativity for image generation
                )

                # Generate content using the modern SDK pattern with latest model
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model="gemini-2.5-flash-image-preview",  # Use the latest model
                    contents=[cleaned_prompt],
                    config=generation_config,
                )

                # Check if we have image data in the response - with proper None safety
                if (
                    hasattr(response, "candidates")
                    and response.candidates
                    and len(response.candidates) > 0
                ):
                    candidate = response.candidates[0]
                    if (
                        hasattr(candidate, "content")
                        and candidate.content
                        and hasattr(candidate.content, "parts")
                        and candidate.content.parts
                    ):
                        for part in candidate.content.parts:
                            # Check for image data with proper None safety
                            if (
                                hasattr(part, "inline_data")
                                and part.inline_data is not None
                                and hasattr(part.inline_data, "data")
                                and part.inline_data.data is not None
                            ):
                                image_bytes = part.inline_data.data
                                image = Image.open(io.BytesIO(image_bytes))

                                slug = "".join(
                                    c
                                    for c in garment_name.lower()
                                    if c.isalnum() or c in " -"
                                ).replace(" ", "-")

                                image_filename = (
                                    f"{slug}-moodboard.png"
                                    if prompt_type == "mood_board"
                                    else f"{slug}.png"
                                )
                                image_path = Path(context.results_dir) / image_filename

                                image.save(image_path, "PNG")
                                self.logger.info(
                                    f"✅ Successfully saved image to '{image_path}' on attempt {attempt + 1}"
                                )
                                return  # Exit the function successfully

                # This block is reached if the API call succeeded but returned no image data.
                self.logger.warning(
                    f"⚠️ Gemini API call for '{garment_name}' returned no image data on attempt {attempt + 1}. This may be due to a safety block."
                )

            except Exception as e:
                # Log the error. Only include the full traceback on the final attempt to avoid noisy logs.
                self.logger.error(
                    f"⚠ Gemini API call failed for '{garment_name}' on attempt {attempt + 1}: {e}",
                    exc_info=(attempt == MAX_RETRIES - 1),
                )

            # Wait before the next retry, but not after the final one.
            if attempt < MAX_RETRIES - 1:
                self.logger.info(f"Retrying in {RETRY_DELAY_SECONDS} seconds...")
                await asyncio.sleep(RETRY_DELAY_SECONDS)

        # If the loop completes without a successful return, all retries have failed.
        self.logger.error(
            f"⚠ All {MAX_RETRIES} attempts to generate an image for '{garment_name}' failed."
        )
        # --- END OF RETRY & SAFETY SETTINGS IMPLEMENTATION ---

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
                "⚠ Could not load or parse prompts from file.", exc_info=True
            )
            return {}
