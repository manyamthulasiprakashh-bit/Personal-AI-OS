from app.providers.base import BaseProvider
from app.providers.mock import MockProvider


def get_provider() -> BaseProvider:
    return MockProvider()
