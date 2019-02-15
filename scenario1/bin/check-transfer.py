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
from shovel import check_transfer

def help():
    print 'stop-shovel.py --source-http <uri> --source-vhost <vhost>'
    print '             '
    print ' http uri : http[s]://username:password@hostname:[port]'

def main(argv):

   source_vhost = '%2F';
   source_http = ''

   try:
      opts, args = getopt.getopt(argv,"",[
      "h" ,
      "source-http=",
      "source-vhost="])

   except getopt.GetoptError:
      help()
      sys.exit(2)
   for opt, arg in opts:
      if opt == '-h':
         help()
         sys.exit()
      elif opt in ("--source-http"):
         source_http = arg
      elif opt in ("--source-vhost"):
         source_vhost = arg

   check_transfer(source_http, source_vhost)

main(sys.argv[1:])
