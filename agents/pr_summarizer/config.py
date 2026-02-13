from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    github_token: str
    github_repository: str
    copilot_model: str = "gpt-4"

    model_config = SettingsConfigDict(env_file=".env")


settings = AgentSettings()