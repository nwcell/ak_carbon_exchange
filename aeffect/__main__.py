#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""CarbonEffect"""

import sys
import argparse
import logging
import urlparse

import aeffect

################################################################################
## ┏┳┓┏━┓╻┏┓╻
## ┃┃┃┣━┫┃┃┗┫
## ╹ ╹╹ ╹╹╹ ╹

def main():

    parser = argparse.ArgumentParser(
                description=aeffect.__description__,
                formatter_class=argparse.RawTextHelpFormatter
            )

    parser.add_argument('-v',
        dest='verbose',
        action='count',
        help='add multiple times for increased verbosity')

    subparsers = parser.add_subparsers(title='Command', dest='command')

    init_parser = subparsers.add_parser('initdb',
                    help='Initialize the database',
                    formatter_class=argparse.RawDescriptionHelpFormatter
                )

    init_parser.add_argument('mongodb',
        action='store',
        help='mongodb://[username:password@]host1[:port1][,host2[:port2],...[,hostN[:portN]]][/[database][?options]]',
        metavar='MONGODBURI')

    init_parser.add_argument('--example-file',
        action='store',
        help='Load in example data (Lorem Ipsum, Fake Clients, Fake Data)')


    server_parser = subparsers.add_parser('runserver',
                    help='HTTP server',
                    formatter_class=argparse.RawDescriptionHelpFormatter
                )

    server_parser.add_argument('listen',
        action='store',
        help='http://host[:port]',
        metavar='LISTENURI')

    server_parser.add_argument('mongodb',
        action='store',
        help='mongodb://[username:password@]host1[:port1][,host2[:port2],...[,hostN[:portN]]][/[database][?options]]',
        metavar='MONGODBURI')

    args = parser.parse_args()

    loglevel = logging.CRITICAL

    if args.verbose >= 4:
        loglevel = logging.DEBUG
    elif args.verbose == 3:
        loglevel = logging.INFO
    elif args.verbose == 2:
        loglevel = logging.WARNING
    elif args.verbose == 1:
        loglevel = logging.ERROR

    logging.basicConfig(level=loglevel)

    logger = logging.getLogger('arguments')

    for arg, value in vars(args).iteritems():
        logger.debug('%s:%s' % (arg, value))

    logger = logging.getLogger('general')
    logger.info('Revving up')

    return

if __name__ == '__main__':
    sys.exit(main())
