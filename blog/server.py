from dataclasses import dataclass, field
import socket
import ssl
import typing
from urllib.parse import urlparse

from blog.util import get_logger


_LOG = get_logger(__name__)


@dataclass(frozen=True)
class Status:
    code: int
    phrase: str

    def __str__(self):
        return f"Status(code={self.code}, phrase={self.phrase})"


STATUS_OK = Status(code=200, phrase="OK")
STATUS_NOT_FOUND = Status(code=404, phrase="Not Found")
STATUS_ERROR = Status(code=500, phrase="Server Error")


class UnknownProtocolError(Exception):
    pass


class ServerError(Exception):
    status: Status

    def __init__(self, status: Status):
        self.status = status

    def __str__(self):
        return f"ServerError(status={self.status})"


@dataclass(frozen=True)
class Request:
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
            return cls(method=method, url=url)
        else:
            raise UnknownProtocolError(raw)

    def dumps(self) -> str:
        return f"{self.method} {urlparse(self.url).path} HTTP/1.1"


@dataclass(frozen=True)
class Response:
    status: Status
    mime_type: typing.Optional[str] = None
    body: typing.Optional[bytes] = None

    def dumpb(self, include_body: bool = True) -> bytes:
        """Serialise the response; HEAD passes include_body=False.

        Content-Length is always the length of the body GET would return, so a
        HEAD response is framed by its headers alone, and Connection: close
        states what the server does after every response.
        """
        body = self.body or b""
        response = f"HTTP/1.1 {self.status.code} {self.status.phrase}\r\n".encode(
            "utf-8"
        )
        if self.mime_type:
            response += f"Content-Type: {self.mime_type}\r\n".encode("utf-8")
        response += f"Content-Length: {len(body)}\r\n".encode("utf-8")
        response += b"Connection: close\r\n"
        response += b"\r\n"
        if include_body:
            response += body

        return response


class SuccessResponse(Response):
    def __init__(self, mime_type: typing.Optional[str], body: bytes):
        super().__init__(status=STATUS_OK, mime_type=mime_type, body=body)


@dataclass(frozen=True)
class Handler:
    def handle(self, request: Request) -> Response:
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

    def _run_loop(self, sock: socket.socket) -> None:
        ip, port = sock.getsockname()
        _LOG.debug(f"Server listening on {ip}:{port}...")
        while True:
            conn = None
            try:
                conn, _ = sock.accept()
                data = conn.recv(1024)
                try:
                    request = Request.loads(data.decode("utf-8", errors="replace"))
                except UnknownProtocolError:
                    # Nothing to answer: an empty read is a TCP probe or port
                    # scan that connected and closed, anything else is not
                    # HTTP/1.x. Either way it is the client's problem, and it
                    # used to escape to the `raise` below and stop the server.
                    if data:
                        _LOG.warning(f"Dropping non-HTTP/1.x request: {data[:80]!r}")
                    continue
                response = None
                try:
                    response = self._match_route(request)
                except ServerError as error:
                    _LOG.info(error)
                    response = self._handle_error_response(
                        request=request, status=error.status
                    )
                except RuntimeError as error:
                    _LOG.error(error)
                    response = self._handle_error_response(
                        request=request, status=STATUS_ERROR
                    )
                except socket.error as error:
                    _LOG.warning(error)
                if response:
                    conn.sendall(response.dumpb(include_body=request.method != "HEAD"))
            except (ConnectionError, ssl.SSLError) as e:
                _LOG.error(e)
            except Exception as e:
                _LOG.critical(e)
                raise
            finally:
                if conn:
                    conn.close()

    def run(
        self,
        host: str,
        port: int,
        crt_file: typing.Optional[str],
        key_file: typing.Optional[str],
    ) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
            sock.listen()
            if crt_file and key_file:
                _LOG.debug(f"SSL enabled with {crt_file} and {key_file}...")
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                context.load_cert_chain(crt_file, key_file)
                with context.wrap_socket(sock, server_side=True) as ssock:
                    self._run_loop(ssock)
            else:
                self._run_loop(sock)
