Designed to be installed as a cronjob; sends a mail containing a digest of all new events.

Depends
-------

[My patched version](https://github.com/mic-e/python-aqbanking) of [python-aqbanking](https://github.com/emdete/python-aqbanking), installed via `python3 setup.py install`
[My patched version](https://github.com/mic-e/dkb-visa/) of [the dkb visa QIF exporter](https://github.com/hoffie/dkb-visa), installed to `/usr/local/bin/dkbfetcher`

Configuration
-------------

create a directory `~/.eventdigest` and `~/.eventdigest/digests`. Create a file `~/.eventdigest/cfg`.
The cfg file may contain any amount of empty lines and comments (starting with '#').
Every other line is interpreted as a call to a python function that yields Event and EventSource objects.
See `eventdigest.__main__` for available imported yielder methods.


License
-------

GPLv3+
