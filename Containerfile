FROM alpine:3

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Setup the app directory
RUN mkdir /app
WORKDIR /app

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=bind,source=.python-version,target=.python-version \
  --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
  --mount=type=bind,source=uv.lock,target=uv.lock \
  uv sync --frozen --no-install-project

# Copy the app
COPY . .

CMD ["uv", "run", "python", "-m", "blog.app"]
