#!/usr/bin/python

import os
import sys
import re
import getopt
import time
import json
import urllib2
import base64
import socket
import subprocess
from shovel import start_transfer


def help():
    print 'start-shovel.py --source-http <uri> --source-vhost <vhost> --source-amqp <uri>'
    print '            --target-http <uri> --target-vhost <vhost> --target-amqp <uri>'
    print '             '
    print ' http uri : http[s]://username:password@hostname:[port]'
    print ' amqp uri : amqp[s]://username:password@hostname:[port]'

def main(argv):

    source_http = ''
    target_http = ''
    source_amqp = ''
    target_amqp = ''
    source_vhost = '%2F'
    target_vhost = '%2F'

    try:
      opts, args = getopt.getopt(argv,"",[
      "h" ,
      "source-http=", "target-http=",
      "source-amqp=", "target-amqp=",
      "source-vhost=", "target-vhost=" ])

    except getopt.GetoptError:
      help()
      sys.exit(2)
    for opt, arg in opts:
      if opt == '-h':
         help()
         sys.exit()
      elif opt in ("--source-http"):
         source_http = arg
      elif opt in ("--target-http"):
         target_http = arg
      elif opt in ("--source-amqp"):
         source_amqp = arg
      elif opt in ("--target-amqp"):
         target_amqp = arg
      elif opt in ("--source-vhost"):
         source_vhost = arg
      elif opt in ("--target-vhost"):
         target_vhost = arg

    start_transfer(source_http, source_vhost, source_amqp, target_http, target_vhost, target_amqp)


main(sys.argv[1:])
