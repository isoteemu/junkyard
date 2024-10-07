"""
WikiPedia Loader

Based on the WikipediaLoader from the langchain_community package, this loader fetches the complete content of the
Wikipedia page, and formats them into sections.

TODO: Make into context aware splitter
"""

import getpass
import logging
import os
from typing import Any, Dict, List, Optional, Set, Tuple
from dotenv import load_dotenv
import keyring
from langchain_core.documents import Document

from langchain_community.vectorstores.chroma import Chroma
#from langchain_community.embeddings import GPT4AllEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings

from langchain_community.utilities import WikipediaAPIWrapper as _WikipediaAPIWrapper

import mwparserfromhell

logger = logging.getLogger(__name__)

class WikipediaAPIWrapper(_WikipediaAPIWrapper):
    SECTIONS_TO_IGNORE: Set = set(
        (
            "See also",
            "References",
            "External links",
            "Further reading",
            "Footnotes",
            "Bibliography",
            "Sources",
            "Citations",
            "Literature",
            "Footnotes",
            "Notes and references",
            "Photo gallery",
            "Works cited",
            "Photos",
            "Gallery",
            "Notes",
            "References and sources",
            "References and notes",
        ) + (
            "Lähteet",
            "Aiheesta muualla",
        )
    )

    def _page_to_document(self, page_title: str, wiki_page: Any) -> Document:
        # patch bigger content limit size for the document
        original_max_chars = self.doc_content_chars_max
        self.doc_content_chars_max = -1
        doc = super()._page_to_document(page_title, wiki_page)
        self.doc_content_chars_max = original_max_chars
        return doc

    def _subsections(
        self, section: mwparserfromhell.wikicode.Wikicode, parent_tiles=List[str]
    ) -> List[Tuple[List[str], str]]:
        """
        From a Wikipedia section, return a flattened list of all nested subsections.

        Each subsection is a tuple, where:
        - the first element is a list of parent subtitles, starting with the page title
        - the second element is the text of the subsection (but not any children)
        """
        headings = [str(h) for h in section.filter_headings()]
        if not headings:
            return []
        title = headings[0]
        cleaned_title = title.strip("=" + " ")
        if cleaned_title in self.SECTIONS_TO_IGNORE:
            logger.debug(f"Ignoring section {cleaned_title}")
            return []

        if len(headings) == 0:
            logger.debug(f"No headings in section {cleaned_title}")
            return []

        titles = parent_tiles + [cleaned_title]
        full_text = str(section)
        logger.debug(f"Found section {titles}, splitting body at {title}")
        section_text = full_text.split(title)[1]

        if len(headings) == 1:
            logger.debug(f"Found section {titles}, no subsections")
            # no subsections
            return [(titles, section_text)]

        # try:
        #     section_text = section_text.split(headings[0])[1]
        # except IndexError as e:
        #     logger.debug(f"Failed to split section {titles} at {headings[0]}")
        #     raise e
        first_subtitle = headings[1]
        section_text = section_text.split(first_subtitle)[0]
        results = [(titles, section_text)]
        for subsection in section.get_sections(levels=[len(titles) + 1]):
            results.extend(self._subsections(subsection, titles))

        return results

    def _split_into_sections(self, document: Document) -> List[str]:
        """From a Wikipedia :class:`Document`, return a list of documents, one for each section."""

        parsed_text = mwparserfromhell.parse(document.page_content)

        # Format the summary content
        summary_text = document.metadata.get("summary", "")[0:self.doc_content_chars_max]
        title = document.metadata.get("title", "")
        docs = [Document(
            page_content=f"# {title}\n{summary_text}",
            metadata={
                **document.metadata,
                **{
                    "title": title,
                },
            },
        )]

        # Format the section content
        for section in parsed_text.get_sections(levels=[2]):
            for subsection_title_parts, subsection_text in self._subsections(
                section, [title]
            ):
                # Format the section content
                section_content = ""
                for i, subtitle in enumerate(subsection_title_parts):
                    section_content += f"{'#' * (i + 1)} {subtitle}\n"
                section_content += subsection_text

                docs.append(Document(
                    page_content=section_content.strip(),
                    metadata={
                        **document.metadata,
                        **{"title": " > ".join(subsection_title_parts)},
                    },
                ))
        return docs

    def load(self, query: str) -> List[Document]:
        docs = []
        for page in super().load(query):
            logger.debug(f"Loading page {page.metadata['title']}")
            docs += self._split_into_sections(page)
        return docs


if __name__ == "__main__":
    from rich.logging import RichHandler
    from rich import print

    logging.basicConfig(level=logging.INFO, handlers=[RichHandler()])

    load_dotenv()

    os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")

    if "OPENAI_API_KEY" not in os.environ:
        os.environ['OPENAI_API_KEY'] = keyring.get_password("openai", getpass.getuser())

    import requests_cache

    requests_cache.install_cache("/tmp/test_cache")

    with open("sidosryhma.json") as fd:
        import json
        data = json.load(fd)

    loader = WikipediaAPIWrapper(
        lang="en", load_all_available_meta=False
    )

    # Process all topics
    docs = []
    for interest_group in data:
        print(docs)
        _d = loader.load(interest_group['wikipedia query'])
        docs += _d

    for d in docs:
        snippet = d.page_content[:120] + "..." if len(d.page_content) > 120 else d.page_content
        print(f"TITLE: {d.metadata['title']}")
        print(f"PAGE:\n{snippet}")
        print()

    #embeddings = OpenAIEmbeddings()
    #embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L12-v2")

    db = Chroma.from_documents(docs, embeddings, persist_directory="/tmp/chroma_test_db")
    
    for interest_group in data:
        print({
            "wikipedia query": interest_group['wikipedia query'],
        })
        r = db.similarity_search_with_score(interest_group['rag query'])

        for doc, score in r:
            snippet = doc.page_content[:120] + "..." if len(doc.page_content) > 120 else doc.page_content
            print({
                "name": interest_group['name'],
                "reasoning": interest_group['reasoning'],
                "rag query": interest_group['rag query'],
                "title": doc.metadata['title'],
                "page": snippet,
                "score": score,
            })
