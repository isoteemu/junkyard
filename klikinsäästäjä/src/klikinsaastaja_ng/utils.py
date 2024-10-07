import json
import logging
import re
from typing import Dict, List

from markdownify import markdownify as _markdownify

logger = logging.getLogger(__name__)


def setup_logging(logger=None):
    """
    Setup logging
    """
    if not logger:
        from . import logger

    from rich.console import Console
    from rich.logging import RichHandler
    from rich.pretty import install as pretty_install

    logging_level = logging.DEBUG

    logger.setLevel(logging_level)
    console = Console(log_time=True, log_time_format='%H:%M:%S-%f')
    logging.basicConfig(level=logging.DEBUG, handlers=[logging.NullHandler()])  # redirect default logger to null

    pretty_install(console=console)
    rh = RichHandler(show_time=True, omit_repeated_times=False, show_level=True, show_path=False,
                     markup=False, rich_tracebacks=True, log_time_format='%H:%M:%S-%f', level=logging_level, console=console)
    rh.setLevel(logging_level)
    logger.addHandler(rh)


def markdownify(html: str) -> str:
    """
    Convert HTML to markdown.
    """
    return _markdownify(html, heading_style="ATX").strip()


def parse_bot_response(response: str) -> Dict | List:
    """
    Parses the response from the bot.
    """
    # Get data from md response block
    match = re.split(r"```json\n(.*)\n```", response, flags=re.MULTILINE | re.DOTALL)
    logger.debug("Match: %r", match)
    text = match[1]
    data = json.loads(text)
    return data
