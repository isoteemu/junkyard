import asyncio
from enum import Enum
import json
import logging
from pathlib import Path
from typing import Dict, List
from platformdirs import user_data_dir
from .settings import settings

from EdgeGPT.EdgeGPT import Chatbot, ConversationStyle

logger = logging.getLogger(__name__)

# Path to the cookies file
COOKIES_FILE = Path(user_data_dir("klikinsaastaja-ng"), "edgegpt-cookies.json")

# Monekypatch get_location_hint_from_locale to support Finnish
from EdgeGPT.utilities import get_location_hint_from_locale as _get_location_hint_from_locale  # noqa: E402
import EdgeGPT.request  # noqa: E402


# Add support for Finnish. Enums cannot be modified, so we need to create a new one.
class PatchedLocationHint(Enum):
    FI = {
        "locale": "fi-FI",
        "LocationHint": [
            {
                "country": "Finland",
                "state": "",
                "city": "Helsinki",
                "timezoneoffset": 2,
                "countryConfidence": 8,
                "Center": {
                    "Latitude": 60.1699,
                    "Longitude": 24.9384,
                },
                "RegionType": 2,
                "SourceType": 1,
            },
        ],
    }


def _patched_get_location_hint_from_locale(locale: str) -> List[Dict]:
    """
    Gets the location hint from the locale.

    This is a patched version of the original function to ad support for Finnish.
    """
    # Fi-fi -> fi-FI
    locale = locale.replace("_", "-")
    _region, _locale = locale.split("-", 1)
    locale = f"{_region.lower()}-{_locale.upper()}"

    # Find the location hint from the locale
    hint = next((hint for hint in PatchedLocationHint if hint.value["locale"] == locale), None)
    if hint is None:
        # Fallback to original function
        return _get_location_hint_from_locale(locale)

    return hint.value["LocationHint"]


# Replace the original function with the patched one
EdgeGPT.request.get_location_hint_from_locale = _patched_get_location_hint_from_locale


async def async_invoke_bot(prompt: str, webpage_context: str = None, locale="fi_FI"):

    # Load cookies
    cookies = []
    if settings.edgegpt_bing_cookie__U:
        cookies.append({
            'name': '_U',
            'value': settings.edgegpt_bing_cookie__U,
        })

    if COOKIES_FILE.exists():
        logger.debug("Loading cookies %s", COOKIES_FILE)
        cookies += json.loads(COOKIES_FILE.read_text())

    bot = await Chatbot.create(cookies=cookies, proxy="http://proxy.jyu.fi:8080")
    response = await bot.ask(
        prompt=prompt,
        conversation_style=ConversationStyle.precise,
        simplify_response=True,
        locale=locale,
        webpage_context=webpage_context,
        no_search=True,
        mode="gpt4-turbo",
    )
    logger.debug(response)
    #print(response)
    await bot.close()
    return response['text']


def invoke(prompt: str, webpage_context: str = None, locale="fi_FI"):
    """ Run async_invoke_bot() as a synchronous function """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()

    response = loop.run_until_complete(async_invoke_bot(prompt, webpage_context, locale=locale))
    return response
