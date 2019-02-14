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

source_hostname = ''
source_http = ''
source_credentials = []
target_hostname = ''
target_http = ''
target_credentials = []
source_amqp = ''
target_amqp = ''
source_vhost = '%2F'
target_vhost = '%2F'

def main(argv):
   source_uri = 'guest:guest@localhost'
   target_uri = ''
   https = False
   http_port = 15672
   amqps = False
   amqp_port = 5672

   try:
      opts, args = getopt.getopt(argv,"",[
      "h" ,
      "http=",
      "https=",
      "amqp=",
      "amqps=",
      "source=", "target=",
      "source-vhost=", "target-vhost=" ])

   except getopt.GetoptError:
      print 'transfer.py --source <uri> --source-vhost <vhost> --target <uri> --target-vhost <vhost>'
      sys.exit(2)
   for opt, arg in opts:
      if opt == '-h':
         print 'transfer.py --source <uri> --target <hostname> --target <uri> --target-vhost <vhost>'
         sys.exit()
      elif opt in ("--source"):
         source = arg
      elif opt in ("--target"):
         target = arg
      elif opt in ("--source-vhost"):
         source_vhost = arg
      elif opt in ("--target-vhost"):
         target_vhost = arg
      elif opt in ("--http"):
         https = False
         http_port = arg
      elif opt in ("--https"):
         https = True
         http_port = arg
      elif opt in ("--amqp"):
         amqps = False
         amqp_port = arg
      elif opt in ("--https"):
         amqps = True
         amqp_port = arg

   source_hostname = remove_credentials_from_url(source_uri)
   target_hostname = remove_credentials_from_url(target_uri)
   source_http =  "%s://%s"  % ((False:"http", True:"https")[https], source_hostname)
   target_http =  "%s://%s"  % ((False:"http", True:"https")[https], target_hostname)
   source_credentials = extract_credentials(source_uri)
   target_credentials = extract_credentials(target_uri)

   source_amqp =  "%s://%s/%s"  % ((False:"amqp", True:"amqps")[amqps], source_uri, source_vhost)
   target_amqp =  "%s://%s/%s"  % ((False:"amqp", True:"amqps")[amqps], target_uri, target_vhost)

   transfer()

def queues(url, src_vhost):
    return '%s/api/queues/%s' % (url, src_vhost)

def http_url(url):
    return "http://%s" % (url)

def https_url(url):
    return "https://%s" % (url)

def amqps_url(url):
    return "amqps://%s" % (url)

def amqp_url(url):
    return "amqp://%s" % (url)

def get_from_source():
    request = urllib2.Request(source_http)

    base64string = base64.encodestring('%s:%s' % (source_credentials[0], source_credentials[1])).replace('\n', '')
    request.add_header("Authorization", "Basic %s" % base64string)

    return urllib2.urlopen(request)

def extract_credentials(url):
    p = re.compile('.*\/\/(.*)@.*')
    return p.findall(url)[0].split(':')

def remove_credentials_from_url(uri):
    p = re.compile('(.*)@.*')
    return uri.replace('%s@' % p.findall(url)[0], '')

def transfer():
    print "Transfer messages [vhost %s at %s] -> [vhost %s at %s]" % (source_vhost, source_hostname, target_vhost, target_hostname)

    queuesToMigrate = find_source_queues_with_messages
    if len(queuesToMigrate) < 1:
        print "There is nothing to migrate"
        exit();

    shovel(queuesToMigrate)

def amqp_url(source_amqp, source_vhost):
    return

def find_source_queues_with_messages():
    resp = get_from_source(queues())
    jsonQueues = json.load(resp)

    queuesToMigrate = [];
    jsonQueuesToMigrate = [];
    if len(jsonQueues) <= 0:
        print "No queues detected"
    else:
        print "Detected following non-empty queues:"
        for q in jsonQueues:
            print " - %s (%d)" % (q["name"], q["messages"])
            if q["messages"] > 0 :
                queuesToMigrate.append(q["name"])
                jsonQueuesToMigrate.append(q)

    return queuesToMigrate

def shovel_parameter(vhost):
    return "/parameters/shovel/%s" % ( src_vhost )

def shovel(queuesToMigrate, ):
    for x in queuesToMigrate:
        print "Creating Shovel for queue %s " % (x)

        shovelConfig = {
            'value' : {
                'src-uri' : source_amqp,
                'src-queue' : x,
                'dest-uri' : target_amqp),
                'dest-queue' : x,
                'ack-mode' : "on-confirm",
                'delete-after' : "queue-length",
            }
        }

        shovelUrl = put_into_source(shovel_parameter())

        newShovelUrl = shovelUrl + "/" + x
        shovelReq = urllib2.Request(newShovelUrl, data=json.dumps(shovelConfig))
        shovelReq.add_header("Authorization", "Basic %s" % base64string)
        shovelReq.add_header("Content-Type", "application/json")
        shovelReq.get_method = lambda : 'PUT'
        resp = urllib2.urlopen(shovelReq)

main(sys.argv[1:])
