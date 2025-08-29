# catalyst/pipeline/processors/generation.py

import base64
import json
import re
from pathlib import Path

# --- START OF CHANGE: ADD ASYNCIO FOR PARALLEL EXECUTION ---
import asyncio

# --- END OF CHANGE ---
from openai import AsyncOpenAI

from catalyst.pipeline.base_processor import BaseProcessor
from catalyst.context import RunContext
from ... import settings


class DalleImageGenerationProcessor(BaseProcessor):
    """
    The final pipeline step. Takes the generated prompts from the context
    and calls the DALL-E 3 API to generate and save the final images concurrently.
    """

    def __init__(self):
        super().__init__()
        self.client = AsyncOpenAI(api_key=settings.DALLE_API_KEY)

    async def process(self, context: RunContext) -> RunContext:
        """
        Creates a list of all image generation tasks and runs them in parallel.
        """
        self.logger.info("🎨 Starting DALL-E 3 image generation...")

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

        # --- START OF CHANGE: SHIFT FROM SERIAL LOOP TO PARALLEL TASK GATHERING ---
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

            # Create a coroutine for each image generation task but don't run it yet.
            task = self._generate_and_save_image(
                final_garment_prompt, garment_name, context
            )
            tasks.append(task)

        if not tasks:
            self.logger.warning("No valid image generation tasks were created.")
            return context

        # Now, run all the created tasks concurrently and wait for them all to complete.
        self.logger.info(
            f"🚀 Launching {len(tasks)} image generation tasks in parallel..."
        )
        await asyncio.gather(*tasks)
        # --- END OF CHANGE ---

        self.logger.info("✅ All image generation tasks complete.")
        return context

    async def _generate_and_save_image(
        self, prompt: str, garment_name: str, context: RunContext
    ):
        """
        Generates and saves a single image. This method is now called concurrently.
        """
        # --- START OF CHANGE: ADD PROMPT CLEANING LOGIC ---
        self.logger.info(f"Cleaning prompt for DALL-E 3: '{garment_name}'...")
        # 1. Remove markdown headings and bullets
        cleaned_prompt = re.sub(r"\*\*.*?\*\*|^- ", "", prompt, flags=re.MULTILINE)
        # 2. Replace all newline characters with spaces
        cleaned_prompt = cleaned_prompt.replace("\n", " ")
        # 3. Collapse multiple spaces into a single space
        cleaned_prompt = " ".join(cleaned_prompt.split())
        # --- END OF CHANGE ---

        self.logger.info(f"Generating image for: '{garment_name}'...")
        try:
            response = await self.client.images.generate(
                model="dall-e-3",
                prompt=cleaned_prompt,  # Use the cleaned prompt
                size="1024x1024",
                quality="hd",
                n=1,
                response_format="b64_json",
            )

            if response.data and response.data[0].b64_json:
                image_data_b64 = response.data[0].b64_json
                image_data = base64.b64decode(image_data_b64)

                slug = "".join(
                    c for c in garment_name.lower() if c.isalnum() or c in " -"
                ).replace(" ", "-")
                image_filename = f"{slug}.png"
                image_path = Path(context.results_dir) / image_filename

                with open(image_path, "wb") as f:
                    f.write(image_data)

                self.logger.info(f"✅ Successfully saved image to '{image_path}'")
            else:
                revised_prompt = (
                    response.data[0].revised_prompt if response.data else "N/A"
                )
                self.logger.error(
                    f"❌ DALL-E 3 API call for '{garment_name}' was successful but returned no image data. "
                    f"This may be due to a content filter. Revised prompt was: '{revised_prompt}'"
                )

        except Exception as e:
            self.logger.error(
                f"❌ DALL-E 3 API call failed for '{garment_name}': {e}",
                exc_info=True,
            )

    def _load_prompts_from_file(self, context: RunContext) -> dict:
        """A fallback to load prompts directly from the JSON file if needed."""
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
