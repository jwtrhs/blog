import os

STATIC_DIRECTORY = os.getenv("BLOG_STATIC_DIRECTORY", "static")
TEMPLATE_DIRECTORY = os.getenv("BLOG_TEMPLATE_DIRECTORY", "template")
CONTENT_DIRECTORY = os.getenv("BLOG_CONTENT_DIRECTORY", "content")
POST_DIRECTORY = os.getenv("BLOG_POST_DIRECTORY", "content/post")
