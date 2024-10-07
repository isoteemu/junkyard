import requests

def fetch_latest_iltalehti() -> List[Href]:
    latest_url = r"https://api.il.fi/v1/articles/iltalehti/lists/latest?limit=30&image_sizes[]=size138"
    base_url = r"https://www.iltalehti.fi/{category[category_name]}/a/{article_id}"

    response = requests.get(latest_url)
    data = response.json()

    article_links = []

    for article in data["response"]:
        # Skip content that has sponsored content metadata
        if article.get('metadata', {}).get('sponsored_content', False):
            logger.debug("Skipping sponsored content: %r", article['title'])
            continue

        url = base_url.format(**article)
        article_links.append(Href(url, article['title']))

    return article_links
