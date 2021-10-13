import os

STATIC_DIRECTORY = os.getenv("BLOG_STATIC_DIRECTORY", "static")
TEMPLATE_DIRECTORY = os.getenv("BLOG_TEMPLATE_DIRECTORY", "template")
post_DIRECTORY = os.getenv("BLOG_post_DIRECTORY", "post")
