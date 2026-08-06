from .LLMEnums import LLMEnums
from .providers import (
    CoHereProvider,
    GeminiProvider,
    GLMProvider,
    OllamaProvider,
)


class LLMProviderFactory:
    def __init__(self, config: object):
        self.config = config

    def create(self, provider: str):
        normalized_provider = str(provider).strip().upper()

        if normalized_provider == LLMEnums.GEMINI.value:
            return GeminiProvider(
                api_key=self.config.GEMINI_API_KEY,
                api_url=self.config.GEMINI_API_URL,
                default_input_max_characters=(
                    self.config.INPUT_DEFAULT_MAX_CHARACTERS
                ),
                default_generation_max_output_tokens=(
                    self.config.GENERATION_DEFAULT_MAX_TOKENS
                ),
                default_generation_temperature=(
                    self.config.GENERATION_DEFAULT_TEMPERATURE
                ),
            )

        if normalized_provider == LLMEnums.OLLAMA.value:
            return OllamaProvider(
                api_url=self.config.OLLAMA_API_URL,
                default_input_max_characters=(
                    self.config.INPUT_DEFAULT_MAX_CHARACTERS
                ),
                default_generation_max_output_tokens=(
                    self.config.GENERATION_DEFAULT_MAX_TOKENS
                ),
                default_generation_temperature=(
                    self.config.GENERATION_DEFAULT_TEMPERATURE
                ),
            )

        if normalized_provider == LLMEnums.COHERE.value:
            return CoHereProvider(
                api_key=self.config.COHERE_API_KEY,
                default_input_max_characters=(
                    self.config.INPUT_DEFAULT_MAX_CHARACTERS
                ),
                default_generation_max_output_tokens=(
                    self.config.GENERATION_DEFAULT_MAX_TOKENS
                ),
                default_generation_temperature=(
                    self.config.GENERATION_DEFAULT_TEMPERATURE
                ),
            )

        if normalized_provider == LLMEnums.GLM.value:
            return GLMProvider(
                api_key=self.config.GLM_API_KEY,
                api_url=self.config.GLM_API_URL,
                default_input_max_characters=(
                    self.config.INPUT_DEFAULT_MAX_CHARACTERS
                ),
                default_generation_max_output_tokens=(
                    self.config.GENERATION_DEFAULT_MAX_TOKENS
                ),
                default_generation_temperature=(
                    self.config.GENERATION_DEFAULT_TEMPERATURE
                ),
            )

        raise ValueError(
            f"unsupported LLM provider: {provider}"
        )
