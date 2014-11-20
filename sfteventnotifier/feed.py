from .event import Event
import feedparser
from datetime import datetime
import traceback
from .util import sanitize_markdown


def query_feed(name, url):
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
            full=sanitize_markdown(
                "could not fetch feed:" +
                "\n    " + "\n    ".join(traceback.format_exc().split('\n'))))

        return

    for entry in feed['entries']:
        uid = 'feed-' + url + '-' + entry['id']
        short = sanitize_markdown(entry['title'])
        if len(short) > 120:
            short = short[:120] + '...'
        short = "[[link]]({}) {}".format(entry['link'], short)

        yield Event(
            source=eventsource,
            uid=uid,
            short=short,
            raw=entry)
