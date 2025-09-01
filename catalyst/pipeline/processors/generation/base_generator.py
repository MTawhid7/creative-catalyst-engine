from abc import ABC, abstractmethod
from catalyst.context import RunContext
from catalyst.utilities.logger import get_logger


class BaseImageGenerator(ABC):
    """
    Abstract Base Class for an image generation strategy.
    This defines the 'contract' that all image generators must follow.
    """

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    async def generate_images(self, context: RunContext) -> RunContext:
        """
        The main method to generate and save images based on the context.
        It must take a RunContext and return a (potentially modified) RunContext.
        """
        pass
