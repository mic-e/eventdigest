#!/usr/bin/env python3


def main():
    # import all event yielders that the cfg may use
    from .hbci import query_bank
    from .dkb import query_dkb_visa

    for call in open('cfg').read().split('\n'):
        if not call.strip() or call.strip().startswith('#'):
            continue

        for e in eval(call):
            print(e.full)

if __name__ == '__main__':
    main()
