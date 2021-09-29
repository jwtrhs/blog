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
            Request(protocol="http", method="GET", url="/1/2/3"),
        ),
        (
            "gemini://test/1/2/3\r\n",
            Request(protocol="gemini", method=None, url="gemini://test/1/2/3"),
        ),
    ],
)
def test_request_loads(url, expected):
    assert Request.loads(url) == expected


@pytest.mark.parametrize(
    ("input_request", "expected"),
    [
        (
            Request(protocol="http", method="GET", url="/1/2/3"),
            "GET /1/2/3 HTTP/1.1",
        ),
        (
            Request(protocol="gemini", method=None, url="gemini://test/1/2/3"),
            "gemini://test/1/2/3\r\n",
        ),
    ],
)
def test_request_base_dumps(input_request, expected):
    assert input_request.dumps() == expected


@pytest.mark.parametrize(
    ("response", "protocol", "expected"),
    [
        (
            Response(status=STATUS_OK, mime_type="mime_type", body=b"body"),
            "gemini",
            b"20 mime_type\r\nbody",
        ),
    ],
)
def test_response_dumpb(response, protocol, expected):
    assert response.dumpb(protocol) == expected
