from enum import Enum
from pathlib import Path

from importlib.resources import files
from jinja2 import Template

import newspaper

import platformdirs


class PromptFiles(Enum):
    INTEREST_GROUP = 'vested_groups_prompt.txt.j2'
    ARTICLE_TITLE = 'article_title_prompt.txt.j2'


def user_prompt_file(prompt: PromptFiles) -> Path:
    return Path(platformdirs.user_data_dir("klikinsaastaja-ng")) / prompt.value


def get_prompt(prompt: PromptFiles):

    _user_prompt_file = user_prompt_file(prompt)
    if _user_prompt_file.exists():
        return _user_prompt_file.read_text()

    resource = f"data/{prompt.value}"
    return files(__package__).joinpath(resource).read_text(encoding="utf-8")


def generate_bot_prompt(article: newspaper.Article, prompt: str | PromptFiles, **kwargs):
    """
    Generates a prompt for the article.

    :param article: The article to generate the prompt for
    :param prompt: The prompt to use. Can be a string or a PromptFiles enum value
    :param kwargs: Additional context to pass to the template
    """

    if isinstance(prompt, PromptFiles):
        prompt = get_prompt(prompt)

    prompt = Template(prompt).render(**article.__dict__, **kwargs)

    return prompt
