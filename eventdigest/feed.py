from .event import Event
from .util import shorten
import feedparser
from datetime import datetime
import traceback


def query_feed(name, url, formatstring='{shortlink} {title}', limit=None):
    eventsource = name
    now = datetime.now()

    try:
        feed = feedparser.parse(url)

        if feed['status'] != 200:
            raise Exception('status != 200')

    except:
        yield Event(
            source=eventsource,
            uid='feed-fetchfail-' + url + '-' + str(now),
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
            source=eventsource,
            uid=uid,
            short=short,
            raw=entry)
