from blog.server import (
    Request,
    Response,
    STATUS_NOT_FOUND,
    STATUS_OK,
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
