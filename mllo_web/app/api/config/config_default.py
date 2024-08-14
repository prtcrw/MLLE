from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings

LOG_LEVEL = Literal["debug", "info", "warning", "error", "critical"]


class AppConfig(BaseSettings):
    host: str = Field(default="127.0.0.1",
                      description="IP address to bind to. Use `0.0.0.0` to serve to your local network.")
    port: int = Field(default=5252, description="Port to bind to.")
    dev: bool = Field(default=True, description="Run in development mode.")
    allow_credentials: bool = Field(default=True, description="Allow CORS credentials.")
    allow_origins: list[str] = Field(default=[], description="Allowed CORS origins.")
    allow_methods: list[str] = Field(default=["*"], description="Methods allowed for CORS.")
    allow_headers: list[str] = Field(default=["*"], description="Headers allowed for CORS.")

    # Logging
    log_level: LOG_LEVEL = Field(default="info", description="Emit logging messages at this level or higher.")

    # SPARQL Client
    sparql_client_endpoint: str = Field(default="https://localhost:8443/mobirest/sparql",
                                        description="Endpoint to use for SPARQL client.")
    sparql_client_auth_type: str = Field(default="basic", description="Auth type for SPARQL client.")
    sparql_client_auth_username: str = Field(default="admin", description="Username for SPARQL client.")
    sparql_client_auth_password: str = Field(default="admin", description="Username for SPARQL client.")


def get_config() -> AppConfig:
    config = AppConfig()

    if config.dev:
        config.allow_origins = ["*"]

    return config
