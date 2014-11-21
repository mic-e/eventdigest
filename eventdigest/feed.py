from .event import Event, EventSource
from .util import shorten
import feedparser
import traceback


def query_feed(name, url, formatstring='{shortlink} {title}', limit=None):
    yield EventSource(name)

    try:
        feed = feedparser.parse(url)

        if feed['status'] != 200:
            raise Exception('status != 200')

    except:
        yield Event(
            short="failure while fetching feed",
            full="could not fetch feed:" +
                 "\n    " + "\n    ".join(traceback.format_exc().split('\n')))

        return

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

        uid = 'feed-' + url + '-' + uid

        shortlink = 'http://l:8080/' + shorten(link)

        short = formatstring.format(
            title=title,
            link=link,
            shortlink=shortlink)

        yield Event(
            uid=uid,
            short=short,
            raw=entry)
