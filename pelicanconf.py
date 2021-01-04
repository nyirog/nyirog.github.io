#!/usr/bin/env python
# -*- coding: utf-8 -*- #

AUTHOR = 'Nyirő Gergő'
SITENAME = 'nyirog'
SITEURL = 'https://nyirog.github.io'

PATH = 'content'

TIMEZONE = 'Europe/Budapest'

DEFAULT_LANG = 'en'

# Feed generation is usually not desired when developing
FEED_DOMAIN = SITEURL
FEED_ALL_ATOM = "feeds/all.atom.xml"
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Blogroll
LINKS = (
    ('Pelican', 'https://getpelican.com/'),
)

# Social widget
SOCIAL = (
    ('github', 'https://github.com/nyirog'),
)

DEFAULT_PAGINATION = 10

# Uncomment following line if you want document-relative URLs when developing
#RELATIVE_URLS = True
