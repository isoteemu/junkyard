
import re
from typing import Callable, List
from newspaper import Article
from pydantic import BaseModel
from pydantic.networks import AnyHttpUrl
from urllib.parse import urlparse, ParseResult

class Href(BaseModel):
    url: AnyHttpUrl
    title: str


class NewspaperOutlet(BaseModel):
    name: str
    # url: AnyHttpUrl

    matching_urls: List[AnyHttpUrl | ParseResult | re.Pattern]

    

    # def get(self, url: AnyHttpUrl) -> Article:
    #     raise NotImplementedError()
