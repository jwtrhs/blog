---
slug: adding-gemini-support
title: Adding support for the Gemini protocol to my blog
author: Jonathon Waterhouse
summary: 
created_at: 2021-10-13
---

After seeing support for the Gemini protocol grow over the last year or so, I decided to add support for it to my little micro-blog. This post is quick overview of how I migrated my old server from HTTP-only to a HTTP/Gemini hybrid server, both served over the same port!

The [code for the server](https://git.sr.ht/~jwaterhouse/blog/tree/master/item/blog/server.py) itself is only ~200 LoC if you'd prefer to just read that.

Previously my blog was a simple static site generator that takes markdown formatted posts organised in a structured file system (this determines the URL path of each post), parses them to HTML and then serves them out. It's written in Python and has few dependencies. The only HTTP method supported is GET with the routing and request handling done with [Starlette](https://starlette.io). The handy python library [Python-Markdown](https://python-markdown.github.io/) handles the Markdown-HTML conversion and [Jinja](https://jinja.palletsprojects.com/) does a small amount of templating to render the posts into a basic layout. All up it's <400 LoC and runs on a small home server tucked inside a cupboard in my house.

I like that the code driving this blog is simple. It's easy to modify if I want to add support for something (which I generally don't), but mostly it just gets out of my way. I wanted to keep that simplicity when adding a new protocol.

It turns out a GET-only HTTP server is just about Gemini-ready, aside from the protocol differences of course. Gemini is a simple protocol, but HTTP (1.1) is too (as long as you don't support most of the optional stuff, anyway). I ended up ditching Starlette and writing my own request/response parser for both HTTP and Gemini, with a simple Python socket server to handle connections. This was actually a lot easier than I anticipated. Each protocol is plaintext, with an easily distinguishable header (or start-) line that I use to detect the request type and parse it accordingly. The only part of the request I care about is the URL path - the rest of the request data is discarded.

With a request parsed and path extracted, the rest of the internal logic like routing and handlers is the same between Gemini/HTTP. When it's time to send back a response the code formats it into the same type as the request. And done.

The python package [md2gemini](https://github.com/makeworld-the-better-one/md2gemini) does a great job of parsing the markdown posts into `text/gemini`.

A final little note on deployment - in Gemini TLS is part of the protocol and there is no "unsecure" version like for HTTP vs. HTTPS. It was easy enough to add TLS/HTTPS support to my little server, however my production deployment uses an Nginx proxy to handle TLS-termination and servers underneath know nothing of the certificates, etc and hence are all unsecured. So the Gemini server actually runs in "unsecured" mode, which feels wrong somehow even though to the client everying is secured.
