from blog.server import (
    Request,
    Response,
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
    ("response", "expected"),
    [
        (
            Response(status=STATUS_OK, mime_type="mime_type", body=b"body"),
            b"HTTP/1.1 200 OK\r\nContent-Type: mime_type\r\n\r\nbody",
        ),
    ],
)
def test_response_dumpb(response, expected):
    assert response.dumpb() == expected
