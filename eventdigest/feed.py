from .event import Event, EventSource
from .util import shorten
import feedparser
import traceback


def query_feed(name, url, formatstring='{shortlink} {title}', limit=None):
    yield EventSource(name)

    feed = feedparser.parse(url)

    if feed['status'] != 200:
        raise Exception('status != 200')

    entries = feed['entries']
    if limit:
        entries = entries[:limit]

    for entry in entries:
        title = entry['title']
        if len(title) > 120:
            title = title[:120] + '...'

        try:
            link = entry['feedburner_origlink']
        except:
            link = entry['link']

        try:
            uid = entry['id']
        except:
            uid = link

        yield Event(
            formatstring.format(title=title,
                                link=link,
                                shortlink='http://l:8080/' + shorten(link)),
            uid='feed-'+ url + '-' + uid)
