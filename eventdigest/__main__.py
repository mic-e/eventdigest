#!/usr/bin/env python3
from .util import PersistentDict, cfgpath
from .mail import mail_self
from datetime import datetime
now = datetime.now()
import os


def main():
    # import all event yielders that the cfg may use
    from .hbci import query_bank
    from .dkb import query_dkb_visa
    from .feed import query_feed

    sentevents = PersistentDict(table='events')
    newevents = []

    for call in open(cfgpath + '/cfg').read().split('\n'):
        if not call.strip() or call.strip().startswith('#'):
            continue

        try:
            for e in eval(call):
                if e.uid in sentevents:
                    continue

                newevents.append(e)
        except Exception as e:
            raise Exception("uncaught exception during " + call) from e

    # create the email
    subject = "digest " + str(now)
    body = []
    currentsource = None
    for e in newevents:
        if e.source != currentsource:
            currentsource = e.source
            body.append(currentsource + "\n|\n")

        body[-1] += "| " + '\n| '.join(e.full.split('\n')) + "\n"

    body = '\n'.join(body)

    filename = cfgpath + "/digests/" + now.strftime('%Y-%m-%d-%H-%M-%S-%f')

    open(filename, 'w').write(body)

    mail_self(subject, body)

    for e in newevents:
        sentevents[e.uid] = str(now)


if __name__ == '__main__':
    try:
        main()
    except:
        import traceback
        mail_self("notifier failed", traceback.format_exc())
