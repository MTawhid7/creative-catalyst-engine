# catalyst/pipeline/processors/generation/base_generator.py

from abc import abstractmethod
from typing import Optional
from catalyst.context import RunContext
from catalyst.pipeline.base_processor import BaseProcessor


class BaseImageGenerator(BaseProcessor):
    @abstractmethod
    async def process(
        self, context: RunContext, temperature_override: Optional[float] = None
    ) -> RunContext:
        pass
