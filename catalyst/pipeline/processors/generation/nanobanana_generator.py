# catalyst/pipeline/processors/generation/nanobanana_generator.py

import asyncio
import io
import json
import re
from pathlib import Path

from google import genai
from google.genai import types
from google.genai.types import HarmCategory, HarmBlockThreshold
from PIL import Image

from .base_generator import BaseImageGenerator
from catalyst.context import RunContext
from catalyst import settings


class NanoBananaGeneration(BaseImageGenerator):
    """
    A versatile image generation strategy using the Google Gemini API,
    refactored for dependency injection, lazy client creation, and unified settings.
    """

    def __init__(self, client=None):
        """
        Initializes the generator. An optional client can be injected for testing.
        """
        super().__init__()
        self._client = client
        self._initialized_client = None

    def _get_client(self):
        """
        Lazily initializes and returns the Gemini client.
        """
        if self._initialized_client:
            return self._initialized_client
        if self._client:
            self._initialized_client = self._client
            return self._client
        if settings.GEMINI_API_KEY:
            try:
                self._initialized_client = genai.Client(api_key=settings.GEMINI_API_KEY)
                self.logger.info(
                    "✅ Google Gemini client configured successfully for NanoBanana."
                )
                return self._initialized_client
            except Exception as e:
                self.logger.critical(
                    f"CRITICAL: Failed to configure Gemini client: {e}", exc_info=True
                )
        self.logger.critical(
            "CRITICAL: GEMINI_API_KEY not set. Nano Banana generator is disabled."
        )
        return None

    async def process(self, context: RunContext) -> RunContext:
        """Orchestrates the image generation process for each key piece in the trend report."""
        client = self._get_client()
        if not client:
            self.logger.error(
                "Halting generation: Gemini client is not initialized or is disabled."
            )
            return context

        self.logger.info("🎨 Activating Nano Banana (Gemini) generation strategy...")
        prompts_data = self._load_prompts_from_file(context)
        if not prompts_data:
            self.logger.warning("Could not load prompts. Halting image generation.")
            return context

        tasks = [
            self._generate_and_save_image(
                prompt_text, garment_name, context, p_type, client
            )
            for garment_name, prompts in prompts_data.items()
            for p_type, prompt_text in prompts.items()
            if prompt_text
        ]
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
        self,
        prompt: str,
        garment_name: str,
        context: RunContext,
        prompt_type: str,
        client,
    ):
        """Generates a single image with retries, saves it, and injects its relative path."""
        cleaned_prompt = " ".join(
            re.sub(r"\*\*.*?\*\*|^- ", "", prompt, flags=re.MULTILINE)
            .replace("\n", " ")
            .split()
        )

        for attempt in range(settings.RETRY_AI_CONTENT_ATTEMPTS):
            self.logger.info(
                f"Generating image for: '{garment_name}' ({prompt_type}) - Attempt {attempt + 1}/{settings.RETRY_AI_CONTENT_ATTEMPTS}..."
            )
            try:
                # --- START: THE DEFINITIVE FIX ---
                # Revert to the explicit, correct list of harm categories that the API accepts.
                safety_settings = [
                    types.SafetySetting(
                        category=cat, threshold=HarmBlockThreshold.BLOCK_NONE
                    )
                    for cat in [
                        HarmCategory.HARM_CATEGORY_HARASSMENT,
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    ]
                ]
                # --- END: THE DEFINITIVE FIX ---

                generation_config = types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                    safety_settings=safety_settings,
                    temperature=0.7,
                )

                response = await client.aio.models.generate_content(
                    model="gemini-2.5-flash-image-preview",
                    contents=[cleaned_prompt],
                    config=generation_config,
                )

                if (
                    response.candidates
                    and response.candidates[0].content
                    and response.candidates[0].content.parts
                ):
                    for part in response.candidates[0].content.parts:
                        if part.inline_data and part.inline_data.data:
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
                                f"✅ Successfully saved image to '{image_path}'"
                            )
                            relative_path = (
                                f"results/{context.results_dir.name}/{image_path.name}"
                            )
                            for piece in context.final_report.get(
                                "detailed_key_pieces", []
                            ):
                                if piece.get("key_piece_name") == garment_name:
                                    path_key = (
                                        "mood_board_relative_path"
                                        if prompt_type == "mood_board"
                                        else "final_garment_relative_path"
                                    )
                                    piece[path_key] = relative_path
                                    self.logger.info(
                                        f"✅ Injected relative path '{relative_path}' into report."
                                    )
                                    break
                            return

                self.logger.warning(
                    f"⚠️ Gemini API call for '{garment_name}' returned no image data on attempt {attempt + 1}."
                )

            except Exception as e:
                self.logger.error(
                    f"❌ Gemini API call failed for '{garment_name}' on attempt {attempt + 1}: {e}",
                    exc_info=(attempt == settings.RETRY_AI_CONTENT_ATTEMPTS - 1),
                )

            if attempt < settings.RETRY_AI_CONTENT_ATTEMPTS - 1:
                await asyncio.sleep(settings.RETRY_BACKOFF_DELAY_SECONDS)

        self.logger.error(
            f"❌ All {settings.RETRY_AI_CONTENT_ATTEMPTS} attempts to generate an image for '{garment_name}' failed."
        )

    def _load_prompts_from_file(self, context: RunContext) -> dict:
        """Loads prompts from the JSON, or warns if it fails."""
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
