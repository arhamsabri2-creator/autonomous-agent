import os
import requests
from dotenv import load_dotenv
load_dotenv()

NEWSAPI_KEY = os.getenv('NEWSAPI_KEY')

def get_top_news(topic='technology', language='en', page_size=5):
    try:
        url = 'https://newsapi.org/v2/everything'
        params = {
            'q': topic,
            'language': language,
            'sortBy': 'publishedAt',
            'pageSize': page_size,
            'apiKey': NEWSAPI_KEY
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if data.get('status') != 'ok':
            return f'NewsAPI error: {data.get("message", "Unknown error")}'
        articles = data.get('articles', [])
        if not articles:
            return f'No news found for topic: {topic}'
        output = f'Latest news on {topic}:\n\n'
        for i, article in enumerate(articles, 1):
            title = article.get('title', 'No title')
            source = article.get('source', {}).get('name', 'Unknown')
            description = article.get('description', 'No description')
            url = article.get('url', '')
            published = article.get('publishedAt', '')[:10]
            output += f'{i}. {title}\n'
            output += f'   Source: {source} | Date: {published}\n'
            output += f'   {description}\n'
            output += f'   URL: {url}\n\n'
        return output.strip()
    except Exception as e:
        return f'News fetch error: {str(e)}'

def get_india_tech_news(page_size=5):
    return get_top_news('India technology startup', page_size=page_size)

def get_ai_news(page_size=5):
    return get_top_news('artificial intelligence AI', page_size=page_size)
