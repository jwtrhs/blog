import argparse

from starlette.applications import Starlette
import uvicorn

from server.routes import routes
from server.util import get_logger


_LOG = get_logger(__name__)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', type=str, default='0.0.0.0')
    parser.add_argument('--port', type=int, default=8888)
    parser.add_argument('--workers', type=int, default=1)
    parser.add_argument('--debug', default=False, action='store_true')
    args = parser.parse_args()

    app = Starlette(
        debug=args.debug,
        routes=routes,
    )

    _LOG.debug(f'Starting server at {args.host}:{args.port} with {args.workers} workers.')
    uvicorn.run(app, host=args.host, port=args.port, workers=args.workers)
