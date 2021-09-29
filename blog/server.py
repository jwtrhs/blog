from dataclasses import dataclass, field
import socket
import ssl
import typing
from urllib.parse import urlparse

from blog.util import get_logger


_LOG = get_logger(__name__)


@dataclass(frozen=True)
class Status:
    http: int
    gemini: int
    phrase: str

    @property
    def is_ok(self) -> bool:
        return (self.http <= 200 and self.http < 300) or (self.gemini >= 20 and self.gemini <= 30)

    @property
    def value(self, protocol: str) -> int:
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
            response = f"HTTP/1.1 {self.status.http} {self.status.phrase}\r\n".encode("utf-8")
            if self.mime_type:
                response += f"Content-Type: {self.mime_type}\r\n".encode("utf-8")
            response += b"\r\n"
            if self.body:
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


@dataclass(frozen=True)
class Server:
    routes: typing.List[Route]
    error_handlers: typing.Dict[Status, typing.Callable] = field(default_factory=dict)

    def _match_route(self, request: RequestBase) -> typing.Optional[typing.Callable]:
        for route in self.routes:
            if response := route.handle(request):
                _LOG.debug(f"Matched route: {request.url} -> {route.path}")
                return response

        raise ServerError(status=STATUS_NOT_FOUND)

    def _handle_error_response(self, request: Request, status: Status):
        if status in self.error_handlers:
            return self.error_handlers[status](request)
        return Response(status=status)

    def _run_loop(self, sock: socket.SocketType) -> None:
        while True:
            conn, addr = sock.accept()
            try:
                data = conn.recv(1024)
                try:
                    request = RequestBase.loads(data.decode("utf-8"))
                    response = self._match_route(request)
                except ServerError as error:
                    _LOG.info(error)
                    response = self._handle_error_response(request=request, status=error.status)
                except RuntimeError as error:
                    _LOG.error(error)
                    response = self._handle_error_response(request=request, status=STATUS_ERROR)
                conn.sendall(response.dumpb(protocol=request.protocol))
            finally:
                conn.close()

    def run(
        self,
        host: str,
        port: int,
        crt_file: typing.Optional[str],
        key_file: typing.Optional[str],
    ) -> None:

        _LOG.debug(f"Starting server at {host}:{port}...")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0) as sock:
            sock.bind((host, port))
            sock.listen(5)
            if crt_file and key_file:
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                context.load_cert_chain(crt_file, key_file)
                with context.wrap_socket(sock, server_side=True) as ssock:
                    self._run_loop(ssock)
            else:
                self._run_loop(sock)
