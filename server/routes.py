import functools
import os
import typing

from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import Response, FileResponse, HTMLResponse
from starlette.routing import Route

from server import settings
from server.util import get_articles, render_template


def _get_articles(request: Request) -> typing.Dict:
    @functools.lru_cache(maxsize=1)
    def _get_articles_cached():
        return get_articles()
    if request.app.debug:
        # Reload articles from disk in debug mode
        return get_articles()
    return _get_articles_cached()


async def get_home(request: Request) -> Response:
    articles = _get_articles(request)
    return HTMLResponse(render_template('home.html.j2', {'articles': articles}))


async def get_static(request: Request) -> Response:
    filepath = os.path.join(settings.STATIC_DIRECTORY, request.path_params['path'])
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404)
    return FileResponse(filepath)


async def get_article_content(request: Request) -> Response:
    slug = request.path_params['slug']
    path = request.path_params.get('path')
    articles = _get_articles(request)

    if slug not in articles:
        raise HTTPException(status_code=404)

    article = articles[slug]

    if path:
        filepath = os.path.join(article['root_directory'], path)
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404)
        return FileResponse(filepath)

    return HTMLResponse(render_template('post.html.j2', {'article': article}))


routes = [
    Route('/', get_home, methods=['GET']),
    Route('/static/{path}', get_static, methods=['GET']),
    Route('/article/{slug}/', get_article_content, methods=['GET']),
    Route('/article/{slug}/{path}', get_article_content, methods=['GET']),
]
