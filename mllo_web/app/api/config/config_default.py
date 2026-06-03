from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOG_LEVEL = Literal["debug", "info", "warning", "error", "critical"]
SPARQL_BACKEND = Literal["mobi", "graphdb"]
LLM_CLIENT_TYPE = Literal["openai_compatible", "azure_foundry"]


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = Field(default="127.0.0.1",
                      description="IP address to bind to. Use `0.0.0.0` to serve to your local network.")
    port: int = Field(default=5252, description="Port to bind to.")
    dev: bool = Field(default=True, description="Run in development mode.")
    allow_credentials: bool = Field(default=True, description="Allow CORS credentials.")
    allow_origins: list[str] = Field(default=[], description="Allowed CORS origins.")
    allow_methods: list[str] = Field(default=["*"], description="Methods allowed for CORS.")
    allow_headers: list[str] = Field(default=["*"], description="Headers allowed for CORS.")

    log_level: LOG_LEVEL = Field(default="info", description="Emit logging messages at this level or higher.")

    # Switch between "mobi" and "graphdb"
    sparql_backend: SPARQL_BACKEND = Field(default="graphdb", description="SPARQL backend to use: 'mobi' or 'graphdb'.")

    # MOBI settings
    mobi_endpoint: str = Field(default="https://localhost:8443/mobirest/sparql",
                               description="Endpoint for MOBI SPARQL client.")
    mobi_auth_type: str = Field(default="basic", description="Auth type for MOBI.")
    mobi_auth_username: str = Field(default="admin", description="Username for MOBI.")
    mobi_auth_password: str = Field(default="admin", description="Password for MOBI.")

    # GraphDB settings
    graphdb_url: str = Field(
        default="http://localhost:7200",
        description="Base URL for GraphDB."
    )
    graphdb_default_repo: str = Field(
        default="mllo",
        description="Default GraphDB repository."
    )
    graphdb_endpoint: str | None = Field(
        default=None,
        description="Optional full GraphDB repository endpoint override."
    )
    graphdb_auth_type: str = Field(default="none", description="Auth type for GraphDB: 'basic' or 'none'.")
    graphdb_auth_username: str = Field(default="admin", description="Username for GraphDB.")
    graphdb_auth_password: str = Field(default="admin", description="Password for GraphDB.")

    # LLM settings (default: OpenAI-compatible endpoint style)
    llm_client_type: LLM_CLIENT_TYPE = Field(
        default="openai_compatible",
        description="LLM client implementation to use: 'openai_compatible' or 'azure_foundry'."
    )
    llm_base_url: str = Field(
        default="http://localhost:1234/v1",
        description="Base URL for the LLM API."
    )
    llm_chat_completions_path: str = Field(
        default="/chat/completions",
        description="Path appended to llm_base_url when llm_chat_completions_url is not set."
    )
    llm_chat_completions_url: str | None = Field(
        default=None,
        description="Optional full URL override for chat completions (useful for Azure Foundry/OpenAI endpoints)."
    )
    llm_model: str = Field(
        default="openai/gpt-oss-120b",
        description="Model name sent to chat completions when llm_send_model is true."
    )
    llm_send_model: bool = Field(
        default=True,
        description="Whether to include model in the chat completions request payload."
    )
    llm_api_key: str | None = Field(
        default=None,
        description="Optional API key for LLM endpoint."
    )
    llm_api_key_header: str = Field(
        default="Authorization",
        description="Header name used for llm_api_key."
    )
    llm_api_key_prefix: str = Field(
        default="Bearer",
        description="Prefix prepended to llm_api_key (e.g., 'Bearer'). Use empty string for raw keys."
    )
    llm_api_version: str | None = Field(
        default=None,
        description="Optional API version value to be sent as query parameter (e.g., Azure '2024-05-01-preview')."
    )
    llm_api_version_param: str = Field(
        default="api-version",
        description="Query parameter name for llm_api_version."
    )
    llm_timeout_seconds: float = Field(
        default=120.0,
        description="Timeout in seconds for LLM API calls."
    )
    llm_max_tokens: int = Field(
        default=1024,
        description="max_tokens value for openai_compatible client payload."
    )
    llm_max_completion_tokens: int = Field(
        default=1024,
        description="max_completion_tokens value for azure_foundry client payload."
    )
    llm_temperature: float = Field(
        default=0.0,
        description="temperature value for openai_compatible client payload."
    )
    llm_azure_send_temperature: bool = Field(
        default=False,
        description="Whether azure_foundry client should send temperature."
    )
    llm_azure_temperature: float = Field(
        default=1.0,
        description="temperature value for azure_foundry payload when llm_azure_send_temperature is true."
    )

    @model_validator(mode="after")
    def derive_graphdb_endpoint(self) -> "AppConfig":
        if not self.graphdb_endpoint:
            self.graphdb_endpoint = f"{self.graphdb_url.rstrip('/')}/repositories/{self.graphdb_default_repo}"
        return self

def get_config() -> AppConfig:
    config = AppConfig()

    if config.dev:
        config.allow_origins = ["*"]

    return config
