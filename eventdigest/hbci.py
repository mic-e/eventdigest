from datetime import datetime, timedelta
import os
import tempfile
import sys
from .util import run_task, multiprocessed
from .event import Event, EventSource
from collections import defaultdict


# we need to run query_bank in a different process due to a limitation in
# python-aqbanking. python-aqbanking segfaults when creating two different
# BankingRequestor objects, as is needed for querying two different banks.
# by running a fork befor each independent use of aqbanking functionality,
# we avoid this.
@multiprocessed
def query_bank(bank_code, account_numbers, uname, pin):
    """
    yields transaction and balance events for accounts that are configured
    in aqbanking (e.g. using GnuCash)

    in case of an error or timeout, an error event containing the program
    output and exception traceback is yielded.
    """
    import aqbanking

    now = datetime.now()

    yield EventSource("HBCI %s" % bank_code)

    pin_name = "PIN_%d_%s" % (bank_code, uname)
    pin_value = pin
    config_dir = os.path.expanduser('~/.aqbanking')
    bank_code = str(bank_code)
    if not isinstance(account_numbers, tuple):
        account_numbers = (account_numbers,)

    account_numbers = list(map(str, account_numbers))

    rq = aqbanking.BankingRequestor(
        pin_name=pin_name,
        pin_value=pin_value,
        config_dir=config_dir,
        bank_code=bank_code,
        account_numbers=account_numbers)

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
            currency = transaction['value_currency']
            value = transaction.get('value', 0)
            account = transaction['local_account_number']
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
                uid=uid,
                short=short,
                raw=transaction))
    else:
        events[now].append(Event(
            short="could not fetch transactions",
            full="could not fetch transactions:\n" +
                 "\n    " + "\n    ".join(transactions_output.split('\n'))))

    if balances:
        maxaccountwidth = max(len(a) for a in account_numbers)
        for i, b in enumerate(balances):
            balance = b['booked_balance']
            account_number = account_numbers[i]
            short = "balance for {:>{}}: {:8.2f}".format(
                account_number,
                maxaccountwidth,
                balance)

            events[now].append(Event(short=short, raw=b))
    else:
        events[now].append(Event(
            short="could not fetch balances",
            full="could not fetch balances:\n" +
                 "\n    " + "\n    ".join(balances_output.split('\n'))))

    for date, eventlist in sorted(events.items()):
        for event in eventlist:
            yield event
