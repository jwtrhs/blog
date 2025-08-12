import argparse
import json
import mimetypes
import os
import typing

from blog import settings
from blog.server import (
    Handler,
    Request,
    Response,
    Route,
    Server,
    ServerError,
    STATUS_NOT_FOUND,
    SuccessResponse,
)
from blog.util import get_posts, parse_markdown, render_template


class HomeHandler(Handler):
    def handle(self, request: Request) -> Response:
        return SuccessResponse(
            mime_type="text/html",
            body=render_template("home.html.j2", {"posts": get_posts()}).encode(
                "utf-8"
            ),
        )


class StaticHandler(Handler):
    def _create_response(self, request: Request) -> Response:
        filepath = os.path.join(settings.STATIC_DIRECTORY, request.path_params["path"])
        if not os.path.exists(filepath):
            raise ServerError(status=STATUS_NOT_FOUND)
        with open(filepath, "rb") as f:
            return SuccessResponse(
                mime_type=mimetypes.guess_type(filepath)[0], body=f.read()
            )

    def handle(self, request: Request) -> Response:
        return self._create_response(request)


class PostDirectoryHandler(Handler):
    def handle(self, request: Request) -> Response:
        return SuccessResponse(
            mime_type="text/html",
            body=render_template(
                "posts_directory.html.j2", {"posts": get_posts()}
            ).encode("utf-8"),
        )


class PostHandler(Handler):
    def _get_post(self, request: Request) -> typing.Dict:
        slug = request.path_params["slug"]
        posts = get_posts()

        if slug not in posts:
            raise ServerError(status=STATUS_NOT_FOUND)

        return posts[slug]

    def handle(self, request: Request) -> Response:
        post = self._get_post(request)

        return SuccessResponse(
            mime_type="text/html",
            body=render_template("post.html.j2", {"post": post}).encode("utf-8"),
        )


class PostContentHandler(PostHandler):
    def _get_content_filepath(self, request: Request) -> str:
        post = self._get_post(request)

        path = request.path_params["path"]
        content_filepath = os.path.join(post["root_directory"], path)
        if not os.path.exists(content_filepath):
            raise ServerError(status=STATUS_NOT_FOUND)

        return content_filepath

    def _create_response(self, request: Request) -> Response:
        content_filepath = self._get_content_filepath(request)
        with open(content_filepath, "rb") as f:
            return SuccessResponse(
                mime_type=mimetypes.guess_type(content_filepath)[0], body=f.read()
            )

    def handle(self, request: Request) -> Response:
        return self._create_response(request)


class CvHandler(Handler):
    def handle(self, request: Request) -> Response:
        return SuccessResponse(
            mime_type="text/html",
            body=render_template(
                "cv.html.j2",
                {"cv": parse_markdown(settings.CONTENT_DIRECTORY, "cv.md")},
            ).encode("utf-8"),
        )


class MatrixHandler(Handler):
    def handle(self, request: Request) -> Response:
        return SuccessResponse(
            mime_type="application/json",
            body=json.dumps({"m.server": "matrix.wtrhs.com:8448"}).encode("utf-8"),
        )


class NotFoundHandler(Handler):
    def handle(self, request: Request) -> Response:
        return Response(
            status=STATUS_NOT_FOUND,
            mime_type="text/html",
            body=render_template("not_found.html.j2").encode("utf-8"),
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host", type=str, default=os.getenv("BLOG_APP_HOST", "0.0.0.0")
    )
    parser.add_argument(
        "--port", type=int, default=int(os.getenv("BLOG_APP_PORT", 8888))
    )
    parser.add_argument(
        "--crt_file", type=str, default=os.getenv("BLOG_APP_TLS_CRT_FILE")
    )
    parser.add_argument(
        "--key_file", type=str, default=os.getenv("BLOG_APP_TLS_KEY_FILE")
    )
    parser.add_argument("--debug", default=False, action="store_true")
    args = parser.parse_args()

    server = Server(
        routes=[
            Route("/", HomeHandler()),
            Route("/static/{path}", StaticHandler()),
            Route("/post/", PostDirectoryHandler()),
            Route("/post/{slug}/", PostHandler()),
            Route("/post/{slug}/{path}", PostContentHandler()),
            Route("/cv", CvHandler()),
            Route("/.well-known/matrix/server", MatrixHandler()),
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
