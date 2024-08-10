from argparse import ArgumentParser, Namespace, RawTextHelpFormatter
from typing import Optional

from mllo_web.version import __version__

_root_help = r"""Path to the runtime root directory. If omitted, the app will search for the root directory in the following order:
- The `$MLLO_WEB_ROOT` environment variable
- The currently active virtual environment's parent directory
- `$HOME/mllo-web`"""

_config_file_help = r"""Path to the mllo-web.yaml configuration file. If omitted, the app will search for the file in the root directory."""

_parser = ArgumentParser(description="MLLO", formatter_class=RawTextHelpFormatter)
_parser.add_argument("--root", type=str, help=_root_help)
_parser.add_argument("--config", dest="config_file", type=str, help=_config_file_help)
_parser.add_argument("--version", action="version", version=__version__, help="Displays the version and exits.")


class MlloArgs:
    """Helper class for parsing CLI args.

    Args should never be parsed within the application code, only in the CLI entrypoints. Parsing args within the
    application creates conflicts when running tests or when using application modules directly.

    If the args are needed within the application, the consumer should access them from this class.

    Example:
    ```
    # In a CLI wrapper
    from mllo-web.frontend.cli.arg_parser import MlloArgs
    MlloArgs.parse_args()

    # In the application
    from mllo-web.frontend.cli.arg_parser import MlloArgs
    args = MlloArgs.args
    """

    args: Optional[Namespace] = None
    did_parse: bool = False

    @staticmethod
    def parse_args() -> Optional[Namespace]:
        """Parse CLI args and store the result."""
        MlloArgs.args = _parser.parse_args()
        MlloArgs.did_parse = True
        return MlloArgs.args
