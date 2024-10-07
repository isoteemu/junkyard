from klikinsäästäjä import *
from klikinsäästäjä import _patched_get_location_hint_from_locale


def main(url):

    # Get locale
    locale = LOCALE
    locale_hint = random.choice(_patched_get_location_hint_from_locale(locale))

    with sync_playwright() as playwright:
        # TODO: Maybe change into edge for edgegpt
        browser = playwright.firefox.launch(headless=True, firefox_user_prefs={
            "media.autoplay.default": 0,
        })
        browser_context = browser.new_context(
            locale=locale.replace("_", "-"),
            geolocation={
                "longitude": locale_hint['Center']['Longitude'],
                "latitude": locale_hint['Center']['Latitude'],
            },
        )

        article = fetch_page_html(url, browser=browser)

        content_length = len(article.article_html)
        logger.debug("Content length: %r", content_length)
        if content_length < 100:
            raise Exception("Content length is too short")

        cookies = browser_context.cookies()
        logger.debug("Browser cookies: %r", cookies, extra={'cookies': cookies})

        browser_context.close()
        browser.close()

    instructions = """
The following news page article may contain content of intrest groups or people who has vested interest on the topic.
Based on the context of the article, provide a list of people or groups who may have vested interest on the topic:
- Vested interest groups
- Interviewed people
- People mentioned in the article
- People or groups who are affected by the topic

Provide reasoning for the interest groups, and how they relate to the page article.
Include a wikipedia api compatible query to find more information about the group or person.
Write a search query to find more information of the group or person in the context of possible bias or vested interest. Detail the issue in the context of the page article. Be specific and provide as much information and context as possible from the article.

Page URL: {{original_url|escape}}
Page title: {{_title|striptags|escape}}

Use the following template for your answer:
```json
[
    {
        'lang': '{languange code of the article}',
        "name": {Group or person name},
        "wikipedia query": {Query to find more information about the group or person},
        "reasoning": {Reasoning for the vested interest},
        "rag query": {Search query to find more information of the group or person and how they relate in the context of the page article},
    },
    ...
]
```
"""
    prompt = Template(instructions).render(**article.__dict__)

    context = md(article.article_html, heading_style="ATX").strip()

    print(context)

    truncated_context = repr(context[:150]) + " ... " + repr(context[-100:]) if len(context) > 255 else context
    logger.debug("Extracted context: %r", truncated_context, extra={'markup': True, 'context': context})

    bot_response = query_bot_suggestion(prompt, context)
    print(bot_response)
    return bot_response



if __name__ == '__main__':
    import sys
    r = main(sys.argv[1])
    d = parse_bot_response(r)
    with open('sidosryhma.json', 'w') as fd:
        json.dump(d, fd, indent=4, ensure_ascii=False)
