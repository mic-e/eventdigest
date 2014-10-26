from datetime import datetime, timedelta
import os
import tempfile
import sys
from .util import run_task, multiprocessed
from .event import Event
from collections import defaultdict


# we need to run query_bank in a different process due to a limitation in
# python-aqbanking. python-aqbanking segfaults when creating two different
# BankingRequestor objects, as is needed for querying two different banks.
# by running a fork befor each independent use of aqbanking functionality,
# we avoid this.
@multiprocessed
def query_bank(bank_code, account_number, uname, pin):
    """
    yields transaction and balance events for accounts that are configured
    in aqbanking (e.g. using GnuCash)

    in case of an error or timeout, an error event containing the program
    output and exception traceback is yielded.
    """
    import aqbanking

    now = datetime.now()

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

    transactions, transactions_output = run_task(
        rq.request_transactions,
        [],
        20,
        True,
        from_time=now - timedelta(days=9001),
        to_time=now,
    )

    balances, balances_output = run_task(rq.request_balances, [], 10, True)

    events = defaultdict(lambda: [])
    if transactions:
        for transaction in transactions:
            uid = transaction['ui']
            currency = transaction['value_currency'].decode()
            value = transaction.get('value', 0)
            account = transaction['local_account_number'].decode()
            type_ = transaction['transaction_text']
            date = transaction['valuta_date']
            purpose = transaction.get('purpose', '')

            short = "{:<16} {:8.2f} {:>3} {} {}".format(
                type_,
                value,
                currency,
                str(date.date()),
                purpose)

            events[date].append(Event(
                source=eventsource,
                uid=uid,
                short=short,
                raw=transaction))
    else:
        events[now].append(Event(
            source=eventsource,
            uid="fetchfail:transactions:{}".format(now),
            short="could not fetch transactions",
            full="could not fetch transactions:\n\n    {}\n".format(
                "\n    ".join(transactions_output.split('\n')))))

    if balances:
        maxaccountwidth = max(len(a) for a in account_numbers)
        for i, b in enumerate(balances):
            balance = b['booked_balance']
            account_number = account_numbers[i]
            short="balance for {:>{}}: {:8.2f}".format(
                account_number,
                maxaccountwidth,
                balance)

            events[now].append(Event(
                source=eventsource,
                uid="balance:{}:{}:{}".format(now, balance, account_number),
                short=short,
                raw=b))
    else:
        events[now].append(Event(
            source=eventsource,
            uid="fetchfail:balances:{}".format(now),
            short="could not fetch balances",
            full="could not fetch balances:\n\n    {}\n".format(
                "\n    ".join(balances_output.split('\n')))))

    for date, eventlist in sorted(events.items()):
        for event in eventlist:
            yield event
