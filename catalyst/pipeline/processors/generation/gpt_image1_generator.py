# catalyst/pipeline/processors/generation/gpt_image1_generator.py

import asyncio
import base64
import json
import re
from pathlib import Path

from openai import AsyncOpenAI

from .base_generator import BaseImageGenerator
from catalyst.context import RunContext
from catalyst import settings


class GptImage1Generation(BaseImageGenerator):
    """
    An image generation strategy for the legacy gpt-image-1 model.

    This class serves as an archived example of how to interact with the older
    model, adapted to the new pluggable generator architecture. It generates
    images in parallel.
    """

    def __init__(self):
        super().__init__()
        # NOTE: The API key setting might be different for this model.
        # We use DALLE_API_KEY for consistency as per the original file.
        self.client = AsyncOpenAI(api_key=settings.DALLE_API_KEY)
        from catalyst.utilities.logger import get_logger

        self.logger = get_logger(self.__class__.__name__)

    async def generate_images(self, context: RunContext) -> RunContext:
        """
        Creates a list of all image generation tasks and runs them in parallel.
        """
        self.logger.info("🎨 Activating legacy GPT-Image-1 generation strategy...")

        if not context.final_report.get("detailed_key_pieces"):
            self.logger.warning(
                "⚠️ No key pieces found in the report. Skipping image generation."
            )
            return context

        prompts_data = self._load_prompts_from_file(context)
        if not prompts_data:
            self.logger.error(
                "❌ Could not load any prompts to generate images. Halting generation."
            )
            return context

        # --- ASYNCHRONOUS TASK GATHERING ---
        self.logger.info(
            "Building a list of image generation tasks to run in parallel..."
        )
        tasks = []
        for garment_name, prompts in prompts_data.items():
            final_garment_prompt = prompts.get("final_garment")
            if not final_garment_prompt:
                self.logger.warning(
                    f"⚠️ No 'final_garment' prompt found for '{garment_name}'. Skipping."
                )
                continue

            # Create a coroutine for each image generation task
            task = self._generate_and_save_image(
                final_garment_prompt, garment_name, context
            )
            tasks.append(task)

        if not tasks:
            self.logger.warning("No valid image generation tasks were created.")
            return context

        # Run all the created tasks concurrently and wait for them to complete
        self.logger.info(
            f"🚀 Launching {len(tasks)} image generation tasks in parallel..."
        )
        await asyncio.gather(*tasks)
        # --- END OF ASYNCHRONOUS LOGIC ---

        self.logger.info("✅ All GPT-Image-1 generation tasks complete.")
        return context

    async def _generate_and_save_image(
        self, prompt: str, garment_name: str, context: RunContext
    ):
        """Generates a single image and saves it to the results directory."""

        # It's good practice to clean prompts for all models
        self.logger.info(f"Cleaning prompt for GPT-Image-1: '{garment_name}'...")
        cleaned_prompt = re.sub(r"\*\*.*?\*\*|^- ", "", prompt, flags=re.MULTILINE)
        cleaned_prompt = cleaned_prompt.replace("\n", " ")
        cleaned_prompt = " ".join(cleaned_prompt.split())

        self.logger.info(f"Generating image for: '{garment_name}'...")
        try:
            # This block is adapted directly from your provided gpt-image-1 code
            response = await self.client.images.generate(
                model="gpt-image-1",
                prompt=cleaned_prompt,
                size="1024x1024",
                quality="high",  # Use "high" for gpt-image-1
                n=1,
            )

            if response.data and len(response.data) > 0:
                image_item = response.data[0]
                if hasattr(image_item, "b64_json") and image_item.b64_json:
                    image_data = base64.b64decode(image_item.b64_json)

                    slug = "".join(
                        c for c in garment_name.lower() if c.isalnum() or c in " -"
                    ).replace(" ", "-")
                    image_filename = f"{slug}.png"
                    image_path = Path(context.results_dir) / image_filename

                    with open(image_path, "wb") as f:
                        f.write(image_data)

                    self.logger.info(f"✅ Successfully saved image to '{image_path}'")
                else:
                    revised_prompt = getattr(image_item, "revised_prompt", "N/A")
                    self.logger.error(
                        f"❌ GPT Image API call for '{garment_name}' returned no image data. "
                        f"Revised prompt was: '{revised_prompt}'"
                    )
            else:
                self.logger.error(
                    f"❌ GPT Image API call for '{garment_name}' returned no data."
                )

        except Exception as e:
            self.logger.error(
                f"❌ GPT Image API call failed for '{garment_name}': {e}",
                exc_info=True,
            )

    def _load_prompts_from_file(self, context: RunContext) -> dict:
        """A fallback to load prompts directly from the JSON file if needed."""
        # This helper function is generic and can be reused
        try:
            prompts_path = Path(context.results_dir) / settings.PROMPTS_FILENAME
            if prompts_path.exists():
                with open(prompts_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                self.logger.warning(
                    f"⚠️ Prompts file not found at {prompts_path}. Cannot generate images."
                )
                return {}
        except Exception:
            self.logger.error(
                "❌ Could not load or parse prompts from file as a fallback.",
                exc_info=True,
            )
            return {}
