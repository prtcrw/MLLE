from __future__ import annotations

import copy
import locale
import os
import re
import shutil
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Optional

import yaml
from pydantic import BaseModel, Field, PrivateAttr, field_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

import mllo_web.configs as model_configs
from mllo_web.frontend.cli.arg_parser import MlloArgs

INIT_FILE = Path("mllo-web.yaml")
LEGACY_INIT_FILE = Path("mllo-web.init")
LOG_FORMAT = Literal["plain", "color", "syslog", "legacy"]
LOG_LEVEL = Literal["debug", "info", "warning", "error", "critical"]
CONFIG_SCHEMA_VERSION = "1.0.0"


class URLRegexTokenPair(BaseModel):
    url_regex: str = Field(description="Regular expression to match against the URL")
    token: str = Field(description="Token to use when the URL matches the regex")

    @field_validator("url_regex")
    @classmethod
    def validate_url_regex(cls, v: str) -> str:
        """Validate that the value is a valid regex."""
        try:
            re.compile(v)
        except re.error as e:
            raise ValueError(f"Invalid regex: {e}")
        return v


class MlloAppConfig(BaseSettings):
    """Mllo's global app configuration.

    Typically, you won't need to interact with this class directly. Instead, use the `get_config` function from `mllo_web.app.services.config` to get a singleton config object.

    Attributes:
        host: IP address to bind to. Use `0.0.0.0` to serve to your local network.
        port: Port to bind to.
        allow_origins: Allowed CORS origins.
        allow_credentials: Allow CORS credentials.
        allow_methods: Methods allowed for CORS.
        allow_headers: Headers allowed for CORS.
        ssl_certfile: SSL certificate file for HTTPS. See https://www.uvicorn.org/settings/#https.
        ssl_keyfile: SSL key file for HTTPS. See https://www.uvicorn.org/settings/#https.
        log_tokenization: Enable logging of parsed prompt tokens.
        log_handlers: Log handler. Valid options are "console", "file=<path>", "syslog=path|address:host:port", "http=<url>".
        log_format: Log format. Use "plain" for text-only, "color" for colorized output, "legacy" for 2.3-style logging and "syslog" for syslog-style.<br>Valid values: `plain`, `color`, `syslog`, `legacy`
        log_level: Emit logging messages at this level or higher.<br>Valid values: `debug`, `info`, `warning`, `error`, `critical`
        log_sql: Log SQL queries. `log_level` must be `debug` for this to do anything. Extremely verbose.
    """

    _root: Optional[Path] = PrivateAttr(default=None)
    _config_file: Optional[Path] = PrivateAttr(default=None)

    # fmt: off

    # WEB
    host: str = Field(default="127.0.0.1",
                      description="IP address to bind to. Use `0.0.0.0` to serve to your local network.")
    port: int = Field(default=5252, description="Port to bind to.")
    allow_origins: list[str] = Field(default=[], description="Allowed CORS origins.")
    allow_credentials: bool = Field(default=True, description="Allow CORS credentials.")
    allow_methods: list[str] = Field(default=["*"], description="Methods allowed for CORS.")
    allow_headers: list[str] = Field(default=["*"], description="Headers allowed for CORS.")
    ssl_certfile: Optional[Path] = Field(default=None,
                                         description="SSL certificate file for HTTPS. See https://www.uvicorn.org/settings/#https.")
    ssl_keyfile: Optional[Path] = Field(default=None,
                                        description="SSL key file for HTTPS. See https://www.uvicorn.org/settings/#https.")

    # MISC FEATURES
    log_tokenization: bool = Field(default=False, description="Enable logging of parsed prompt tokens.")

    # LOGGING
    log_handlers: list[str] = Field(default=["console"],
                                    description='Log handler. Valid options are "console", "file=<path>", "syslog=path|address:host:port", "http=<url>".')
    # note - would be better to read the log_format values from logging.py, but this creates circular dependencies issues
    log_format: LOG_FORMAT = Field(default="color",
                                   description='Log format. Use "plain" for text-only, "color" for colorized output, "legacy" for 2.3-style logging and "syslog" for syslog-style.')
    log_level: LOG_LEVEL = Field(default="info", description="Emit logging messages at this level or higher.")
    log_sql: bool = Field(default=False,
                          description="Log SQL queries. `log_level` must be `debug` for this to do anything. Extremely verbose.")

    # fmt: on

    model_config = SettingsConfigDict(env_prefix="mllo_", env_ignore_empty=True)

    def update_config(self, config: dict[str, Any] | MlloAppConfig, clobber: bool = True) -> None:
        """Updates the config, overwriting existing values.

        Args:
            config: A dictionary of config settings, or instance of `MlloAppConfig`. If an instance of \
                `MlloAppConfig`, only the explicitly set fields will be merged into the singleton config.
            clobber: If `True`, overwrite existing values. If `False`, only update fields that are not already set.
        """

        if isinstance(config, dict):
            new_config = self.model_validate(config)
        else:
            new_config = config

        for field_name in new_config.model_fields_set:
            new_value = getattr(new_config, field_name)
            current_value = getattr(self, field_name)

            if field_name in self.model_fields_set and not clobber:
                continue

            if new_value != current_value:
                setattr(self, field_name, new_value)

    def write_file(self, dest_path: Path, as_example: bool = False) -> None:
        """Write the current configuration to file. This will overwrite the existing file.

        A `meta` stanza is added to the top of the file, containing metadata about the config file. This is not stored in the config object.

        Args:
            dest_path: Path to write the config to.
        """
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "w") as file:
            # Meta fields should be written in a separate stanza - skip legacy_models_yaml_path
            meta_dict = self.model_dump(mode="json", include={"schema_version"})

            # User settings
            config_dict = self.model_dump(
                mode="json",
                exclude_unset=False if as_example else True,
                exclude_defaults=False if as_example else True,
                exclude_none=True if as_example else False,
                exclude={"schema_version", "legacy_models_yaml_path"},
            )

            if as_example:
                file.write(
                    "# This is an example file with default and example settings. Use the values here as a baseline.\n\n"
                )
            file.write("# Internal metadata - do not edit:\n")
            file.write(yaml.dump(meta_dict, sort_keys=False))
            file.write("\n")
            file.write("# Put user settings here - see https://Mllo-ai.github.io/mllo/features/CONFIGURATION/:\n")
            if len(config_dict) > 0:
                file.write(yaml.dump(config_dict, sort_keys=False))

    def _resolve(self, partial_path: Path) -> Path:
        return (self.root_path / partial_path).resolve()

    @property
    def root_path(self) -> Path:
        """Path to the runtime root directory, resolved to an absolute path."""
        if self._root:
            root = Path(self._root).expanduser().absolute()
        else:
            root = self.find_root().expanduser().absolute()
        self._root = root  # insulate ourselves from relative paths that may change
        return root.resolve()

    @property
    def config_file_path(self) -> Path:
        """Path to mllo.yaml, resolved to an absolute path."""
        resolved_path = self._resolve(self._config_file or INIT_FILE)
        assert resolved_path is not None
        return resolved_path

    @staticmethod
    def find_root() -> Path:
        """Choose the runtime root directory when not specified on command line or init file."""
        if os.environ.get("MLLO_WEB_ROOT"):
            root = Path(os.environ["MLLO_WEB_ROOT"])
        elif venv := os.environ.get("VIRTUAL_ENV", None):
            root = Path(venv).parent.resolve()
        else:
            root = Path("~/mllo-web").expanduser().resolve()
        return root


class DefaultMlloAppConfig(MlloAppConfig):
    """A version of `MlloAppConfig` that does not automatically parse any settings from environment variables
    or any file.

    This is useful for writing out a default config file.

    Note that init settings are set if provided.
    """

    @classmethod
    def settings_customise_sources(
            cls,
            settings_cls: type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (init_settings,)


def load_and_migrate_config(config_path: Path) -> MlloAppConfig:
    """Load and migrate a config file to the latest version.

    Args:
        config_path: Path to the config file.

    Returns:
        An instance of `MlloAppConfig` with the loaded and migrated settings.
    """
    assert config_path.suffix == ".yaml"
    with open(config_path, "rt", encoding=locale.getpreferredencoding()) as file:
        loaded_config_dict: dict[str, Any] = yaml.safe_load(file)

    assert isinstance(loaded_config_dict, dict)

    try:
        # Meta is not included in the model fields, so we need to validate it separately
        config = MlloAppConfig.model_validate(loaded_config_dict)
        assert (
                config.schema_version == CONFIG_SCHEMA_VERSION
        ), f"Invalid schema version, expected {CONFIG_SCHEMA_VERSION}: {config.schema_version}"
        return config
    except Exception as e:
        raise RuntimeError(f"Failed to load config file {config_path}: {e}") from e


@lru_cache(maxsize=1)
def get_config() -> MlloAppConfig:
    """Get the global singleton app config.

    When first called, this function:
    - Creates a config object. `pydantic-settings` handles merging of settings from environment variables, but not the init file.
    - Retrieves any provided CLI args from the MlloArgs class. It does not _parse_ the CLI args; that is done in the main entrypoint.
    - Sets the root dir, if provided via CLI args.
    - Logs in to HF if there is no valid token already.
    - Copies all legacy configs to the legacy conf dir (needed for conversion from ckpt to diffusers).
    - Reads and merges in settings from the config file if it exists, else writes out a default config file.

    On subsequent calls, the object is returned from the cache.
    """
    # This object includes environment variables, as parsed by pydantic-settings
    config = MlloAppConfig()

    args = MlloArgs.args

    # This flag serves as a proxy for whether the config was retrieved in the context of the full application or not.
    # If it is False, we should just return a default config and not set the root, log in to HF, etc.
    if not MlloArgs.did_parse:
        return config

    # Set CLI args
    if root := getattr(args, "root", None):
        config._root = Path(root)
    if config_file := getattr(args, "config_file", None):
        config._config_file = Path(config_file)

    # Create the example config file, with some extra example values provided
    example_config = DefaultMlloAppConfig()
    example_config.remote_api_tokens = [
        URLRegexTokenPair(url_regex="cool-models.com", token="my_secret_token"),
        URLRegexTokenPair(url_regex="nifty-models.com", token="some_other_token"),
    ]
    example_config.write_file(config.config_file_path.with_suffix(".example.yaml"), as_example=True)

    # Copy all legacy configs - We know `__path__[0]` is correct here
    configs_src = Path(model_configs.__path__[
                           0])  # pyright: ignore [reportUnknownMemberType, reportUnknownArgumentType, reportAttributeAccessIssue]
    shutil.copytree(configs_src, config.legacy_conf_path, dirs_exist_ok=True)

    if config.config_file_path.exists():
        config_from_file = load_and_migrate_config(config.config_file_path)
        # Clobbering here will overwrite any settings that were set via environment variables
        config.update_config(config_from_file, clobber=False)
    else:
        # We should never write env vars to the config file
        default_config = DefaultMlloAppConfig()
        default_config.write_file(config.config_file_path, as_example=False)

    return config
