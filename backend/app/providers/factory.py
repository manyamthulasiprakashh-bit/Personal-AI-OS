from app.providers.base import BaseProvider
from app.providers.learning import LearningProvider
from app.providers.mock import MockProvider


def get_provider() -> BaseProvider:
    return MockProvider()


def get_learning_provider() -> LearningProvider:
    return MockProvider()
