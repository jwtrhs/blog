FROM python:3.13-alpine

RUN apk add uv

RUN mkdir /srv/app
WORKDIR /srv/app

# Install the project's dependencies using the lockfile and settings
COPY .python-version pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY . .

CMD ["uv", "run", "python", "-m", "blog.app"]
