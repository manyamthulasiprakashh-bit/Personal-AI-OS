from app.providers.base import BaseProvider
from app.config import get_settings
from app.providers.job import (
    JobProvider,
    LLMJobProvider,
    MockJobProvider,
    UnavailableJobProvider,
)
from app.providers.learning import LearningProvider
from app.providers.mock import MockProvider


def get_provider() -> BaseProvider:
    return MockProvider()


def get_learning_provider() -> LearningProvider:
    return MockProvider()


def get_job_provider() -> JobProvider:
    settings = get_settings()
    provider_name = settings.job_provider.strip().lower()
    if provider_name == "mock":
        return MockJobProvider()
    if provider_name == "llm":
        return LLMJobProvider(settings)
    return UnavailableJobProvider("invalid job provider configuration")
