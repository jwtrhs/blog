import argparse
import mimetypes
import os
import typing

from blog import settings
from blog.server import Handler, Request, Response, Route, Server, ServerError, STATUS_NOT_FOUND, SuccessResponse
from blog.util import get_articles, get_logger, render_template


_LOG = get_logger(__name__)


class HomeHandler(Handler):
    def handle_http(self, request: Request) -> Response:
        return SuccessResponse(
            mime_type="text/html",
            body=render_template("home.html.j2", {"articles": get_articles()}).encode("utf-8"),
        )

    def handle_gemini(self, request: Request) -> Response:
        return SuccessResponse(
            mime_type="text/gemini",
            body=render_template("home.gmi.j2", {"articles": get_articles()}).encode("utf-8"),
        )


class StaticHandler(Handler):
    def _create_response(self, request: Request) -> Response:
        filepath = os.path.join(settings.STATIC_DIRECTORY, request.path_params["path"])
        if not os.path.exists(filepath):
            raise ServerError(status=STATUS_NOT_FOUND)
        with open(filepath, "rb") as f:
            return SuccessResponse(mime_type=mimetypes.guess_type(filepath)[0], body=f.read())

    def handle_http(self, request: Request) -> Response:
        return self._create_response(request)

    def handle_gemini(self, request: Request) -> Response:
        return self._create_response(request)


class ArticleHandler(Handler):
    def _get_article(self, request: Request) -> typing.Dict:
        slug = request.path_params["slug"]
        articles = get_articles()

        if slug not in articles:
            raise ServerError(status=STATUS_NOT_FOUND)

        return articles[slug]

    def handle_http(self, request: Request) -> Response:
        article = self._get_article(request)

        return SuccessResponse(
            mime_type="text/html",
            body=render_template("article.html.j2", {"article": article}).encode("utf-8"),
        )

    def handle_gemini(self, request: Request) -> Response:
        article = self._get_article(request)

        return SuccessResponse(
            mime_type="text/gemini",
            body=render_template("article.gmi.j2", {"article": article}).encode("utf-8"),
        )


class ArticleContentHandler(ArticleHandler):
    def _get_content_filepath(self, request: Request) -> str:
        article = self._get_article(request)

        path = request.path_params["path"]
        content_filepath = os.path.join(article["root_directory"], path)
        if not os.path.exists(content_filepath):
            raise ServerError(status=STATUS_NOT_FOUND)

        return content_filepath

    def _create_response(self, request: Request) -> Response:
        content_filepath = self._get_content_filepath(request)
        with open(content_filepath, "rb") as f:
            return SuccessResponse(mime_type=mimetypes.guess_type(content_filepath)[0], body=f.read())

    def handle_http(self, request: Request) -> Response:
        return self._create_response(request)

    def handle_gemini(self, request: Request) -> Response:
        return self._create_response(request)


class NotFoundHandler(Handler):
    def handle_http(self, request: Request) -> Response:
        return Response(
            status=STATUS_NOT_FOUND,
            mime_type="text/html",
            body=render_template("not_found.html.j2").encode("utf-8"),
        )

    def handle_gemini(self, request: Request) -> Response:
        return Response(status=STATUS_NOT_FOUND)


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
            Route("/", HomeHandler()),
            Route("/static/{path}", StaticHandler()),
            Route("/article/{slug}/", ArticleHandler()),
            Route("/article/{slug}/{path}", ArticleContentHandler()),
        ],
        error_handlers={
            STATUS_NOT_FOUND: NotFoundHandler(),
        },
    )

    server.run(
        host=args.host,
        port=args.port,
        crt_file=args.crt_file,
        key_file=args.key_file,
    )
