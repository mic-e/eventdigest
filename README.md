Designed to be installed as a cronjob; sends a mail containing a digest of all new events.

Depends
-------

 - [My patched version](https://github.com/mic-e/python-aqbanking) of [python-aqbanking](https://github.com/emdete/python-aqbanking), installed via `python3 setup.py install`
 - [My patched version](https://github.com/mic-e/dkb-visa/) of [the dkb visa QIF exporter](https://github.com/hoffie/dkb-visa), installed to `/usr/local/bin/dkbfetcher`

Configuration
-------------

 - Install via `python3 setup.py install`
 - `mkdir -p ~/.eventdigest/digests`
 - create `~/.eventdigest/cfg`

The cfg file may contain any amount of empty lines and comments (starting with '#').
Every other line is interpreted as a call to a python function that yields Event and EventSource objects.
See `eventdigest.__main__` for available imported yielder methods.

The shortlinks that are used by default in the `query_feed` events require the local link shortener to be running.
In `/etc/hosts`, create an alias `l` -> `127.0.0.1`, and make sure to auto-launch the link shortener with your
desktop environment (`python3 -m localshortener`)

License
-------

GPLv3+
