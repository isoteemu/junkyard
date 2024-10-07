import logging
import re
from typing import Union
import newspaper
import requests

from klikinsaastaja_ng.utils import markdownify, setup_logging
from klikinsaastaja_ng.main import generate_bot_prompt
from klikinsaastaja_ng.models import NewspaperOutlet
from urllib.parse import ParseResult, urlparse


NEWSPAPER_OUTLETS = []

logger = logging.getLogger(__name__)

class RequestsSession:

    _session: requests.Session

    def get(self, url) -> newspaper.Article:
        if not hasattr(self, "_session"):
            self._session = requests.Session()

        req = self._session.get(url)
        req.raise_for_status()

        article = newspaper.Article(url)
        article.download(req.text).parse()
        article.url = req.url

        return article


class IltaLehti(RequestsSession, NewspaperOutlet):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            name="IltaLehti",
            matching_urls=[
                urlparse("//www.iltalehti.fi"),
            ],
            **kwargs,
        )


class GenericOutletProvider(NewspaperOutlet, RequestsSession):
    ...


NEWSPAPER_OUTLETS.append(IltaLehti())


def outlet(url) -> NewspaperOutlet:
    article_url_parts = urlparse(url)

    # Find the outlet that matches the URL
    # Warning: there be dragons here
    for outlet in NEWSPAPER_OUTLETS:
        logger.debug("Checking outlet %s: %r", outlet.name, outlet.matching_urls)
        for outlet_url_rule in outlet.matching_urls:
            logger.debug("Checking outlet %s rule %s", outlet.name, outlet_url_rule)
            if isinstance(outlet_url_rule, re.Pattern):
                if outlet_url_rule.match(url):
                    logger.debug(f"Matched `re.Pattern` outlet {outlet.name} for URL {url}")
                    return outlet

                continue  # URL part does not match, try next outlet
            elif isinstance(outlet_url_rule, str):
                logger.debug("Converting string to ParseResult")
                outlet_url_rule = urlparse(outlet_url_rule)

            # Compare the parts of the URL that are defined in the matching URL
            for key in outlet_url_rule._fields:
                logger.debug(f"Checking outlet {outlet.name} for URL {url} part {key}")
                if outlet_part := getattr(outlet_url_rule, key):
                    if outlet_part != getattr(article_url_parts, key):
                        logger.debug("Outlet url part %r does not match %r, try next outlet", outlet_part, getattr(article_url_parts, key))
                        break  # URL part does not match, try next outlet
            else:
                logger.debug(f"Matched outlet {outlet.name} for URL {url}")
                return outlet

    logger.warning("No outlet matched %r, returning generic provider", url)
    return GenericOutletProvider(name="GenericOutletProvider", matching_urls=[])


def build(url: str, prompt: str, **kwargs):
    source = outlet(url)
    article = source.get(url)

    prompt = generate_bot_prompt(article, prompt=prompt, **kwargs)
    context = markdownify(article.article_html)

    return prompt, context


if __name__ == "__main__":
    setup_logging(logger)
    url = "https://www.iltalehti.fi/politiikka/a/5a5ef968-928b-4110-8949-ee87352643f4"
    news_outlet = outlet(url)
    article = news_outlet.get(url)
    print(article.title)
