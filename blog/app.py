import argparse
import mimetypes
import os

from blog import settings
from blog.server import Request, Response, Route, Server, ServerError, STATUS_NOT_FOUND, SuccessResponse
from blog.util import get_articles, get_logger, render_template


_LOG = get_logger(__name__)


def get_home(request: Request) -> Response:
    articles = get_articles()
    mime_type = "text/html" if request.protocol == "http" else "text/gemini"
    template = "home.html.j2" if request.protocol == "http" else "home.gmi.j2"
    return SuccessResponse(
        mime_type=mime_type,
        body=render_template(template, {"articles": articles}).encode("utf-8"),
    )


def get_static(request: Request) -> Response:
    filepath = os.path.join(settings.STATIC_DIRECTORY, request.path_params["path"])
    if not os.path.exists(filepath):
        raise ServerError(status=STATUS_NOT_FOUND)
    with open(filepath, "rb") as f:
        return SuccessResponse(mime_type=mimetypes.guess_type(filepath)[0], body=f.read())


def get_article_content(request: Request) -> Response:
    slug = request.path_params["slug"]
    path = request.path_params.get("path")
    articles = get_articles()

    if slug not in articles:
        raise ServerError(status=STATUS_NOT_FOUND)

    article = articles[slug]

    if path:
        filepath = os.path.join(article["root_directory"], path)
        if not os.path.exists(filepath):
            raise ServerError(status=STATUS_NOT_FOUND)
        with open(filepath, "rb") as f:
            return SuccessResponse(mime_type=mimetypes.guess_type(filepath)[0], body=f.read())

    mime_type = "text/html" if request.protocol == "http" else "text/gemini"
    template = "article.html.j2" if request.protocol == "http" else "article.gmi.j2"
    return SuccessResponse(
        mime_type=mime_type,
        body=render_template(template, {"article": article}).encode("utf-8"),
    )


def get_not_found(request: Request) -> Response:
    if request.protocol == "http":
        return Response(
            status=STATUS_NOT_FOUND,
            mime_type="text/html",
            body=render_template("not_found.html.j2").encode("utf-8"),
        )
    elif request.protocol == "gemini":
        return Response(status=STATUS_NOT_FOUND)
    else:
        raise RuntimeError(f"Unknown protocol: {request.protocol}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8888)
    parser.add_argument("--crt_file", type=str, default=None)
    parser.add_argument("--key_file", type=str, default=None)
    parser.add_argument("--debug", default=False, action="store_true")
    args = parser.parse_args()

    server = Server(
        routes=[
            Route("/", get_home),
            Route("/static/{path}", get_static),
            Route("/article/{slug}/", get_article_content),
            Route("/article/{slug}/{path}", get_article_content),
        ],
        error_handlers={
            STATUS_NOT_FOUND: get_not_found,
        },
    )

    server.run(
        host=args.host,
        port=args.port,
        crt_file=args.crt_file,
        key_file=args.key_file,
    )
