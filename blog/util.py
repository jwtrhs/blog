from collections import OrderedDict
import datetime
import functools
import logging
import os
import typing

import jinja2
import markdown

from blog import settings


def get_logger(name: str):
    logging.basicConfig(level=logging.DEBUG)
    return logging.getLogger(name)


def render_template(filepath: str, context: typing.Optional[typing.Dict] = None) -> str:
    @functools.lru_cache(maxsize=1)
    def _get_jinja2_env() -> jinja2.Environment:
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(settings.TEMPLATE_DIRECTORY),
        )
        return env

    env = _get_jinja2_env()
    template = env.get_template(filepath)
    return template.render(context or {})


def parse_markdown(
    root_directory: str,
    markdown_file: str,
    other_files: typing.Optional[typing.List[str]] = None,
) -> typing.Dict[str, typing.Any]:
    md = markdown.Markdown(
        extensions=["meta", "fenced_code", "toc"],
        extension_configs={
            "toc": {
                "baselevel": 1,
                "toc_depth": "2-2",
            },
        },
    )
    with open(os.path.join(root_directory, markdown_file), "r") as f:
        markdown_content = f.read()
        html = md.convert(markdown_content)

    metadata = md.Meta
    title = metadata["title"][0] if metadata.get("title") else None
    created_at = metadata["created_at"][0] if metadata.get("created_at") else None
    slug = metadata["slug"][0] if metadata.get("slug") else None
    summary = metadata["summary"][0] if metadata.get("summary") else None
    is_draft = metadata["is_draft"][0] if metadata.get("is_draft") else False

    return {
        "title": title,
        "created_at": datetime.datetime.fromisoformat(created_at)
        if created_at
        else None,
        "slug": slug,
        "summary": summary,
        "is_draft": is_draft,
        "markdown": markdown_content,
        "html": html,
        "html_toc": md.toc,
        "root_directory": root_directory,
        "markdown_file": markdown_file,
        "other_files": other_files,
    }


def _get_posts() -> OrderedDict:
    posts = {}
    for root, directories, files in os.walk(settings.POST_DIRECTORY):
        md_files = [it for it in files if it.endswith(".md")]
        if not md_files:
            continue
        md_file = md_files[0]
        other_files = [it for it in files if it != md_file]
        post = parse_markdown(root, md_file, other_files)
        assert post["title"], "title is required"
        assert post["created_at"], "created_at is required"
        assert post["slug"], "slug is required"
        assert post["slug"] not in posts, "slug is duplicate"
        if post["is_draft"]:
            pass
        posts[post["slug"]] = post

    ordered_posts = OrderedDict()
    for item in sorted(
        list(posts.values()), key=lambda it: it["created_at"], reverse=True
    ):
        ordered_posts[item["slug"]] = item

    return ordered_posts


@functools.lru_cache(maxsize=1)
def _get_posts_cached():
    return _get_posts()


def get_posts(use_cache: bool = True) -> OrderedDict:
    if use_cache:
        return _get_posts_cached()

    return _get_posts()
