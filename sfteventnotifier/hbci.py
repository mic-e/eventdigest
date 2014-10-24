from datetime import datetime, timedelta
import aqbanking
import os
import tempfile
import sys
from .util import run_task
from .event import Event
from collections import defaultdict


def get_transactions(bank_code, account_number, uname, pin):
    eventsource = "HBCI %s" % bank_code

    pin_name = "PIN_%d_%s" % (bank_code, uname)
    pin_value = pin
    config_dir = os.path.expanduser('~/.aqbanking')
    bank_code = str(bank_code)
    account_numbers = str(account_number).split(',')

    rq = aqbanking.BankingRequestor(
        pin_name=pin_name.encode(),
        pin_value=pin_value.encode(),
        config_dir=config_dir.encode(),
        bank_code=bank_code.encode(),
        account_numbers=[an.encode() for an in account_numbers])

    transactions, output_request_transactions = run_task(
        rq.request_transactions,
        False,
        from_time=datetime.now() - timedelta(days=9001),
        to_time=datetime.now(),
    )

    balances, output_request_balances = run_task(rq.request_balances)

    events = defaultdict(lambda: [])
    for transaction in transactions:
        uid = transaction['ui']
        currency = transaction['value_currency'].decode()
        value = transaction['value']
        account = transaction['local_account_number'].decode()
        type_ = transaction['transaction_text']
        date = str(transaction['valuta_date'].date())
        purpose = transaction.get('purpose', '')

        short = "{:<16} {:7.2f} {:>3} {} {}".format(type_, value, currency, date, purpose)

        events[date].append(Event(
            source=eventsource,
            uid=uid,
            short=short,
            raw=transaction))

    for date, eventlist in sorted(events.items()):
        for event in eventlist:
            yield event
