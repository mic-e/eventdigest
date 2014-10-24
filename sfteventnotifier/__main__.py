#!/usr/bin/env python3


def main():
    exec(open('cfg').read(), globals())

    from .hbci import get_transactions
    for e in get_transactions(bank_code, account_number, uname, pin):
        print(e)
        # print(e.raw)

if __name__ == '__main__':
    main()
