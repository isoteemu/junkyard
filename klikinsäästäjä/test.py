from functools import lru_cache
import re
import wikipedia
import mwparserfromhell


# Cache requests to the web
try:

    import requests_cache
    if not requests_cache.get_cache():
        requests_cache.install_cache('/tmp/demo_cache')
except Exception as e:
    pass

#print(wikipedia.search("Barack"))

@lru_cache(maxsize=100)
def get_page(query):
    try:
        page = wikipedia.page(query, auto_suggest=True)
        return page
    except wikipedia.exceptions.DisambiguationError as e:
        print(e.options)
        return None
    except wikipedia.exceptions.PageError as e:
        print(e)
        return None

page = get_page("Finnish literature")

def split_into_sections(title, text):
    mw = mwparserfromhell.parse(str(page.content))
    headings = [str(h) for h in parsed_text.filter_headings()]
    return sections

print(mw.filter_headings())

#parsed_text = mwparserfromhell.parse(str(page.content))


