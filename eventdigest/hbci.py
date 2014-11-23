from datetime import datetime, timedelta
import os
import tempfile
import sys
from .util import run_task, multiprocessed, indent
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

    if not transactions:
        raise Exception("could not fetch transactions:\n\n" +
                        indent(transactions_output))

    balances, balances_output = run_task(rq.request_balances, [], 10, True)

    events = defaultdict(lambda: [])

    if not balances:
        raise Exception("could not fetch balances:\n\n" +
                        indent(balances_output))

    for transaction in transactions:
        uid = transaction['ui']
        currency = transaction['value_currency']
        value = transaction.get('value', 0)
        account = transaction['local_account_number']
        type_ = transaction['transaction_text']
        date = transaction['valuta_date']
        purpose = transaction.get('purpose', '')

        text = "{:<20} {:8.2f} {:>3} {} \0{}".format(
            type_,
            value,
            currency,
            str(date.date()),
            purpose)

        events[date].append(Event(uid=uid, text=text))

    for i, b in enumerate(balances):
        balance = b['booked_balance']
        account_number = account_numbers[i]
        text = "balance {:>12} {:8.2f} EUR".format(
            account_number,
            balance)

        events[now].append(Event(text))

    for date, eventlist in reversed(sorted(events.items())):
        for event in eventlist:
            yield event
