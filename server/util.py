from collections import OrderedDict
import datetime
import functools
import logging
import os
import typing

import jinja2
import markdown

from server import settings


def get_logger(name: str):
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


def parse_article(
    root_directory: str,
    markdown_file: str,
    other_files: typing.List[str],
) -> typing.Tuple[typing.Dict, str]:
    md = markdown.Markdown(extensions=['meta'])
    with open(os.path.join(root_directory, markdown_file), 'r') as f:
        html = md.convert(f.read())
    metadata = md.Meta
    title = metadata['title'][0] if metadata.get('title') else None
    created_at = metadata['created_at'][0] if metadata.get('created_at') else None
    slug = metadata['slug'][0] if metadata.get('slug') else None
    summary = metadata['summary'][0] if metadata.get('summary') else None
    assert title, 'title is required'
    assert created_at, 'created_at is required'
    assert slug, 'slug is required'

    return {
        'title': title,
        'created_at': datetime.datetime.fromisoformat(created_at),
        'summary': summary,
        'slug': slug,
        'html': html,
        'root_directory': root_directory,
        'markdown_file': markdown_file,
        'other_files': other_files,
    }


def get_articles():
    articles = {}
    for root, directories, files in os.walk(settings.CONTENT_DIRECTORY):
        md_files = [it for it in files if it.endswith('.md')]
        if not md_files:
            continue
        md_file = md_files[0]
        other_files = [it for it in files if it != md_file]
        article = parse_article(root, md_file, other_files)
        assert article['slug'] not in articles, 'slug is duplicate'
        articles[article['slug']] = article

    ordered_articles = OrderedDict()
    for item in sorted(list(articles.values()), key=lambda it: it['created_at'], reverse=True):
        ordered_articles[item['slug']] = item

    return ordered_articles
