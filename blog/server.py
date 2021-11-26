from dataclasses import dataclass, field
import socket
import ssl
import typing
from urllib.parse import urlparse

from blog.util import get_logger


_LOG = get_logger(__name__)

_PROTOCOL_HTTP = "http"
_PROTOCOL_GEMINI = "gemini"


@dataclass(frozen=True)
class Status:
    http: int
    gemini: int
    phrase: str

    @property
    def is_ok(self) -> bool:
        return (self.http <= 200 and self.http < 300) or (self.gemini >= 20 and self.gemini < 30)

    def value(self, protocol: str) -> int:
        if protocol == _PROTOCOL_HTTP:
            return self.http
        elif protocol == _PROTOCOL_GEMINI:
            return self.gemini
        else:
            raise RuntimeError(f"Unknown protocol: {protocol}")


STATUS_OK = Status(http=200, gemini=20, phrase="OK")
STATUS_NOT_FOUND = Status(http=404, gemini=51, phrase="Not Found")
STATUS_ERROR = Status(http=500, gemini=50, phrase="Server Error")


class UnknownProtocolError(Exception):
    pass


class ServerError(Exception):

    status: Status

    def __init__(self, status: Status):
        self.status = status


@dataclass(frozen=True)
class Request:

    protocol: str
    method: typing.Optional[str]
    url: str
    path_params: typing.Dict[str, str] = field(default_factory=dict)

    @classmethod
    def loads(cls, raw: str) -> "Request":
        start_line = raw.split("\r\n")[0]
        if start_line.endswith("HTTP/1.0") or start_line.endswith("HTTP/1.1"):
            parts = start_line.split(" ")
            method = parts[0]
            url = " ".join(parts[1:-1])
            return cls(protocol=_PROTOCOL_HTTP, method=method, url=url)
        elif start_line.startswith("gemini://"):
            return cls(protocol=_PROTOCOL_GEMINI, method=None, url=raw.strip())
        else:
            raise UnknownProtocolError(raw)

    def dumps(self) -> str:
        if self.protocol == _PROTOCOL_HTTP:
            return f"{self.method} {urlparse(self.url).path} HTTP/1.1"
        elif self.protocol == _PROTOCOL_GEMINI:
            return f"{self.url}\r\n"
        else:
            raise UnknownProtocolError(f"Unknown protocol: {self.protocol}")


@dataclass(frozen=True)
class Response:

    status: Status
    mime_type: typing.Optional[str] = None
    body: typing.Optional[bytes] = None

    def dumpb(self, protocol: str) -> bytes:
        if protocol == _PROTOCOL_HTTP:
            response = f"HTTP/1.1 {self.status.http} {self.status.phrase}\r\n".encode("utf-8")
            if self.mime_type:
                response += f"Content-Type: {self.mime_type}\r\n".encode("utf-8")
            response += b"\r\n"
            if self.body:
                response += self.body
        elif protocol == _PROTOCOL_GEMINI:
            response = f"{self.status.gemini} {self.mime_type or ''}\r\n".encode("utf-8")
            if self.body:
                response += self.body
        else:
            raise RuntimeError(f"Unknown protocol: {protocol}")

        return response


class SuccessResponse(Response):
    def __init__(self, mime_type: typing.Optional[str], body: bytes):
        super().__init__(status=STATUS_OK, mime_type=mime_type, body=body)


@dataclass(frozen=True)
class Handler:
    def handle(self, request: Request) -> Response:
        if request.protocol == _PROTOCOL_HTTP:
            return self.handle_http(request)
        elif request.protocol == _PROTOCOL_GEMINI:
            return self.handle_gemini(request)
        else:
            raise RuntimeError(f"Unknown protocol: {request.protocol}")

    def handle_http(self, request: Request) -> Response:
        raise ServerError(status=STATUS_ERROR)

    def handle_gemini(self, request: Request) -> Response:
        raise ServerError(status=STATUS_ERROR)


@dataclass(frozen=True)
class Route:

    path: str
    handler: Handler

    def handle(self, request: Request) -> typing.Optional[Response]:
        parsed_url = urlparse(request.url)
        route_parts = self.path.split("/")
        path_parts = parsed_url.path.split("/", len(route_parts))

        path_params = {}
        for route_part, url_part in zip(route_parts, path_parts):
            if route_part.startswith("{") and route_part.endswith("}"):
                route_name = route_part.lstrip("{").rstrip("}")
                path_params[route_name] = url_part
            elif route_part != url_part:
                return None

        return self.handler.handle(
            Request(
                protocol=request.protocol,
                method=request.method,
                url=request.url,
                path_params=path_params,
            ),
        )


@dataclass(frozen=True)
class Server:
    routes: typing.List[Route]
    error_handlers: typing.Dict[Status, Handler] = field(default_factory=dict)

    def _match_route(self, request: Request) -> Response:
        for route in self.routes:
            if response := route.handle(request):
                _LOG.debug(f"Matched route: {request.url} -> {route.path}")
                return response

        raise ServerError(status=STATUS_NOT_FOUND)

    def _handle_error_response(self, request: Request, status: Status) -> Response:
        try:
            if status in self.error_handlers:
                return self.error_handlers[status].handle(request)
        except ServerError as error:
            status = error.status
        return Response(status=status)

    def _run_loop(self, sock: socket.SocketType) -> None:
        while True:
            conn, addr = sock.accept()
            try:
                data = conn.recv(1024)
                response = None
                try:
                    request = Request.loads(data.decode("utf-8"))
                    response = self._match_route(request)
                except ServerError as error:
                    _LOG.info(error)
                    response = self._handle_error_response(request=request, status=error.status)
                except RuntimeError as error:
                    _LOG.error(error)
                    response = self._handle_error_response(request=request, status=STATUS_ERROR)
                except UnknownProtocolError as error:
                    _LOG.warn(error)
                if response:
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
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
            sock.listen(5)
            if crt_file and key_file:
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                context.load_cert_chain(crt_file, key_file)
                with context.wrap_socket(sock, server_side=True) as ssock:
                    self._run_loop(ssock)
            else:
                self._run_loop(sock)
