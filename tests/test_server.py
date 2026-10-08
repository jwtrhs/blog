import socket
import threading

from blog.server import (
    Handler,
    Request,
    Response,
    Route,
    Server,
    STATUS_NOT_FOUND,
    STATUS_OK,
    SuccessResponse,
)

import pytest


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "GET /1/2/3 HTTP/1.1",
            Request(method="GET", url="/1/2/3"),
        ),
    ],
)
def test_request_loads(url, expected):
    assert Request.loads(url) == expected


@pytest.mark.parametrize(
    ("input_request", "expected"),
    [
        (
            Request(method="GET", url="/1/2/3"),
            "GET /1/2/3 HTTP/1.1",
        ),
    ],
)
def test_request_base_dumps(input_request, expected):
    assert input_request.dumps() == expected


@pytest.mark.parametrize(
    ("response", "include_body", "expected"),
    [
        (
            Response(status=STATUS_OK, mime_type="mime_type", body=b"body"),
            True,
            b"HTTP/1.1 200 OK\r\nContent-Type: mime_type\r\n"
            b"Content-Length: 4\r\nConnection: close\r\n\r\nbody",
        ),
        # HEAD: same headers, including the GET body's length, and no body.
        (
            Response(status=STATUS_OK, mime_type="mime_type", body=b"body"),
            False,
            b"HTTP/1.1 200 OK\r\nContent-Type: mime_type\r\n"
            b"Content-Length: 4\r\nConnection: close\r\n\r\n",
        ),
        (
            Response(status=STATUS_NOT_FOUND),
            True,
            b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\nConnection: close\r\n\r\n",
        ),
    ],
)
def test_response_dumpb(response, include_body, expected):
    assert response.dumpb(include_body=include_body) == expected


class _OkHandler(Handler):
    def handle(self, request: Request) -> Response:
        return SuccessResponse(mime_type="text/plain", body=b"ok")


@pytest.mark.parametrize(
    "junk",
    [
        b"",  # a TCP probe or port scan: connect, send nothing, close
        b"\xff\xfe\x00 not http\r\n\r\n",  # not UTF-8, not HTTP/1.x
    ],
)
def test_run_loop_survives_non_http_connection(junk):
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    server = Server(routes=[Route(path="/", handler=_OkHandler())])
    thread = threading.Thread(target=server._run_loop, args=(listener,), daemon=True)
    thread.start()
    address = listener.getsockname()

    with socket.create_connection(address, timeout=5) as junk_conn:
        junk_conn.sendall(junk)
        junk_conn.shutdown(socket.SHUT_WR)
        # The server closes the connection without answering.
        assert junk_conn.recv(1024) == b""

    with socket.create_connection(address, timeout=5) as conn:
        conn.sendall(b"GET / HTTP/1.1\r\nHost: test\r\n\r\n")
        response = b""
        while chunk := conn.recv(1024):
            response += chunk

    assert thread.is_alive()
    assert response.startswith(b"HTTP/1.1 200 OK\r\n")
    assert response.endswith(b"\r\n\r\nok")
