from datetime import datetime
import re
import csv
import hashlib
import traceback
from .event import Event
from subprocess import Popen, TimeoutExpired, PIPE


def parse(csvlines):
    """
    parses DKB VISA CSV lines

    returns a tuple of (balance, list(transaction)),
    where transaction is a tuple (value, currency, date, purpose, uid)
    """
    balanceline = csvlines[4]
    m = re.match(r'^"Saldo:";"(\d+\.\d+) EUR";$', balanceline)
    if not m:
        raise Exception("balance line is invalid: " + repr(balanceline))

    balance = m.group(1)
    try:
        balance = float(balance)
    except Exception as e:
        raise Exception("balance not a number: " + repr(balance)) from e

    transactions = []

    if not csvlines[7].startswith('"Umsatz abgerechnet";"Wertstellung"'):
        raise Exception("unexpected header in line 8: " + csvlines[7])

    for fields in csv.reader(csvlines[8:], delimiter=';'):
        if len(fields) == 0:
            continue
        if len(fields) != 7:
            raise Exception("invalid field count: " + repr(fields))

        _, wertstellung, _, description, value, foreign_value, _ = fields

        m = re.match(r'^(\d{2})\.(\d{2})\.(\d{4})$', wertstellung)
        if not m:
            raise Exception("not a valid date: " + wertstellung)

        value = float(value.replace(',', '.'))
        currency = "EUR"
        date = m.group(3) + "-" + m.group(2) + "-" + m.group(1)
        purpose = description
        if foreign_value:
            purpose += " (" + foreign_value + ")"
        uid = 'dkbvisa-' + date + str(value) + purpose
        uid = hashlib.sha512(uid.encode()).hexdigest()

        transactions.append((value, currency, date, purpose, uid))

    return balance, transactions


def query_dkb_visa(username, cc, pin):
    """
    yields transaction and balance events for a DKB VISA card

    in case of an error or timeout, an error event containing the program
    output and exception traceback is yielded

    @param cc:
        last 4 digits of credit card number
    """
    now = datetime.now()
    cc = str(cc)

    # dkbfetcher is a modified version of https://github.com/hoffie/dkb-visa,
    # which takes PIN as stdin and dumps the raw CSV to stdout
    invocation = ['dkbfetcher',
                  '--userid', username,
                  '--cardid', cc,
                  '--from-date', '01.01.1970',
                  '--output', '-',
                  '--raw']

    proc = Popen(invocation, stdout=PIPE, stderr=PIPE, stdin=PIPE)

    eventsource = "DKB VISA " + cc

    try:
        stdout, stderr = proc.communicate(input=pin.encode(), timeout=30)
    except TimeoutExpired:
        yield Event(
            source=eventsource,
            uid="dkb-visa:timeout:{}:{}".format(now, cc),
            short="timeout while fetching CSV")
        return

    stdout = stdout.decode('iso-8859-1', errors='replace')
    stderr = stderr.decode('utf-8', errors='replace')

    if proc.returncode != 0:
        yield Event(
            source=eventsource,
            uid="dkb-visa:fetchfail:{}:{}".format(now, cc),
            short="failure while fetching CSV",
            full="could not fetch CSV: return code = " +
                 str(proc.returncode) +
                 "\n    " + "\n    ".join(stderr.split('\n')))
        return

    if not stdout.strip():
        yield Event(
            source=eventsource,
            uid="dkb-visa:fetchfail:{}:{}".format(now, cc),
            short="failure while fetching CSV",
            full="could not fetch CSV:" +
                 "\n    " + "\n    ".join(stderr.split('\n')))
        return

    csvlines = stdout.split('\n')

    try:
        balance, transactions = parse(csvlines)
    except:
        yield Event(
            source=eventsource,
            uid="dkb-visa:parsefail:{}:{}".format(now, cc),
            short="failure while parsing CSV",
            full="could not parse CSV:" +
                 "\n    " + "\n    ".join(traceback.format_exc().split('\n')))
        return

    for value, currency, date, purpose, uid in transactions:
        short = "{:<16} {:8.2f} {:>3} {} {}".format(
            "CC-Transaction",
            value,
            currency,
            date,
            purpose)

        yield Event(
            source=eventsource,
            uid=uid,
            short=short)

    yield Event(
        source=eventsource,
        uid="dkb-visa:balance:{}:{}:{}".format(now, balance, cc),
        short="balance for DKB VISA {}: {:8.2f}".format(cc, balance))
