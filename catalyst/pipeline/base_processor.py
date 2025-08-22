# catalyst/pipeline/base_processor.py
from abc import ABC, abstractmethod
from catalyst.context import RunContext
from ..utilities.logger import get_logger


class BaseProcessor(ABC):
    """Abstract base class for a pipeline step."""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    async def process(self, context: RunContext) -> RunContext:
        """Processes the context and returns the modified context."""
        pass
