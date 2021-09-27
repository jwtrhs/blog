import argparse
from dataclasses import dataclass
import mimetypes
import os
import socket
import ssl
import typing
from urllib.parse import urlparse

from server import settings
from server.util import get_articles, get_logger, render_template


_LOG = get_logger(__name__)


@dataclass(frozen=True)
class Status:
    http: str
    gemini: str
    phrase: str

    @property
    def value(self, protocol: str) -> str:
        if protocol == "http":
            return self.http
        elif protocol == "gemini":
            return self.gemini
        else:
            raise RuntimeError(f"Unknown protocol: {protocol}")


STATUS_OK = Status(http=200, gemini=20, phrase="OK")
STATUS_NOT_FOUND = Status(http=404, gemini=51, phrase="Not Found")
STATUS_ERROR = Status(http=500, gemini=50, phrase="Server Error")


class ServerError(Exception):

    status: Status

    def __init__(self, status: Status):
        self.status = status


@dataclass(frozen=True)
class RequestBase:

    protocol: str
    url: str

    @classmethod
    def loads(cls, raw: str) -> "RequestBase":
        if raw.startswith("GET"):
            url = raw.split("\r\n")[0].lstrip("GET ").rsplit(" ", 1)[0]
            return cls(protocol="http", url=url)
        elif raw.startswith("gemini://"):
            return cls(protocol="gemini", url=raw.strip())
        else:
            raise RuntimeError(raw)

    def dumps(self) -> str:
        if self.protocol == "http":
            return f"GET {urlparse(self.url).path} HTTP/1.1"
        elif self.protocol == "gemini":
            return f"{self.url}\r\n"
        else:
            raise ServerError(f"Unknown protocol: {self.protocol}")


@dataclass(frozen=True)
class Request(RequestBase):

    path_params: typing.Dict[str, str]


@dataclass(frozen=True)
class Response:

    status: Status
    mime_type: typing.Optional[str] = None
    body: typing.Optional[bytes] = None

    def dumpb(self, protocol: str) -> bytes:
        if protocol == "http":
            response = f"HTTP/1.1 {self.status.http} {self.status.phrase}".encode("utf-8")
            if self.mime_type:
                response += f"\r\nContent-Type: {self.mime_type}".encode("utf-8")
            if self.body:
                response += b"\r\n\r\n"
                response += self.body
        elif protocol == "gemini":
            response = f"{self.status.gemini} {self.mime_type or ''}\r\n".encode("utf-8")
            if self.body:
                response += self.body
        else:
            raise ServerError(f"Unknown protocol: {self.protocol}")

        return response


class SuccessResponse(Response):
    def __init__(self, mime_type: str, body: bytes):
        super().__init__(status=STATUS_OK, mime_type=mime_type, body=body)


class Route:

    path: str
    parts: typing.List[str]
    handler: typing.Callable

    def __init__(self, path: str, handler: typing.Callable):
        self.path = path
        self.parts = path.split("/")
        self.handler = handler

    def handle(self, request: RequestBase) -> typing.Optional[Response]:
        parsed_url = urlparse(request.url)
        path_parts = parsed_url.path.split("/", len(self.parts))

        path_params = {}
        for route_part, url_part in zip(self.parts, path_parts):
            if route_part.startswith("{") and route_part.endswith("}"):
                route_name = route_part.lstrip("{").rstrip("}")
                path_params[route_name] = url_part
            elif route_part != url_part:
                return

        return self.handler(Request(protocol=request.protocol, url=request.url, path_params=path_params))


class Router:

    routes: typing.List[Route]

    def __init__(self, routes: typing.List[Route]):
        self.routes = routes

    def match(self, request: RequestBase) -> typing.Optional[typing.Callable]:
        for route in self.routes:
            if response := route.handle(request):
                _LOG.debug(f"Matched route: {request.url} -> {route.path}")
                return response

        raise ServerError(status=STATUS_NOT_FOUND)


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


def _main_loop(sock, router: Router):
    while True:
        conn, addr = sock.accept()
        try:
            data = conn.recv(1024)
            try:
                request = RequestBase.loads(data.decode("utf-8"))
                response = router.match(request)
            except ServerError as error:
                response = Response(status=error.status)
            except RuntimeError:
                response = Response(status=STATUS_ERROR)
            conn.sendall(response.dumpb(protocol=request.protocol))
        finally:
            conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8888)
    parser.add_argument("--crt_file", type=str, default=None)
    parser.add_argument("--key_file", type=str, default=None)
    parser.add_argument("--debug", default=False, action="store_true")
    args = parser.parse_args()

    router = Router(
        [
            Route("/", get_home),
            Route("/static/{path}", get_static),
            Route("/article/{slug}/", get_article_content),
            Route("/article/{slug}/{path}", get_article_content),
        ]
    )

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0) as sock:
        sock.bind((args.host, args.port))
        sock.listen(5)
        if args.crt_file and args.key_file:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(args.crt_file, args.key_file)
            with context.wrap_socket(sock, server_side=True) as ssock:
                _main_loop(ssock, router)
        else:
            _main_loop(sock, router)
