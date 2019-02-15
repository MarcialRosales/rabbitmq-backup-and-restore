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

def queues(vhost):
    return '/api/queues/%s' % (vhost)

def shovels(vhost):
    return '/api/shovels/%s' % (vhost)

def shovel_parameter(vhost, queue):
    return "/api/parameters/shovel/%s/%s" % (vhost, queue)

def get_from(base_url, credentials, path):
    request = urllib2.Request('%s%s' % (base_url, path))

    base64string = base64.encodestring('%s:%s' % (credentials[0], credentials[1])).replace('\n', '')
    request.add_header("Authorization", "Basic %s" % base64string)

    return urllib2.urlopen(request)

def put_into(base_url, credentials, path, payload):
    request = urllib2.Request('%s%s' % (base_url, path), data=payload)
    base64string = base64.encodestring('%s:%s' % (credentials[0], credentials[1])).replace('\n', '')

    request.add_header("Authorization", "Basic %s" % base64string)
    request.add_header("Content-Type", "application/json")
    request.get_method = lambda : 'PUT'

    return urllib2.urlopen(request)

def delete_from(base_url, credentials, path):
    request = urllib2.Request('%s%s' % (base_url, path))
    base64string = base64.encodestring('%s:%s' % (credentials[0], credentials[1])).replace('\n', '')

    request.add_header("Authorization", "Basic %s" % base64string)
    request.add_header("Content-Type", "application/json")
    request.get_method = lambda : 'DELETE'

    return urllib2.urlopen(request)

def extract_credentials(uri):
    p = re.compile('.*\/\/(.*)@.*')
    return p.findall(uri)[0].split(':')

def remove_credentials_from_url(uri):
    p = re.compile('.*\/\/(.*)@.*')
    return uri.replace('%s@' % p.findall(uri)[0], '')

def start_transfer(source_http, source_vhost, source_amqp, target_http, target_vhost, target_amqp):
    print "Transfer messages [vhost %s at %s] -> [vhost %s at %s]" % (source_vhost, source_http, target_vhost, target_http)

    source_credentials = extract_credentials(source_http)
    source_base_url = remove_credentials_from_url(source_http)
    target_http = remove_credentials_from_url(target_http)

    queuesToMigrate = find_queues_with_messages(source_base_url, source_credentials, source_vhost)
    if len(queuesToMigrate) < 1:
        print "There are no messages to transfer"
        exit();

    shovel(source_base_url, source_credentials, source_vhost, queuesToMigrate, source_amqp, target_amqp)

def check_transfer(http, vhost):
    print "Check Transfer messages from [vhost %s at %s]" % (vhost, http)

    source_credentials = extract_credentials(http)
    source_base_url = remove_credentials_from_url(http)

    queuesToMigrate = find_queues_with_messages(source_base_url, source_credentials, vhost)
    if len(queuesToMigrate) > 0:
        print "Transfer has not complete yet. There are %d queues with content" % (len(queuesToMigrate))
        exit -1

    resp = get_from(source_base_url, source_credentials, shovels(vhost))
    list_of_shovels = json.load(resp)
    if len(list_of_shovels) > 0:
        print "The following shovels are still running. Stop them to complete the transfer"
        for s in list_of_shovels :
            print " - %s " % (s["name"])
    else:
        print "Transfer fully completed. There are no queues with messages nor shovels running"

def find_queues_with_messages(base_url, credentials, vhost):
    resp = get_from(base_url, credentials, queues(vhost))
    jsonQueues = json.load(resp)

    queuesNamesToMigrate = []
    queuesToMigrate = []
    if len(jsonQueues) <= 0:
        print "No queues detected"
    else:
        for q in jsonQueues:
            if q["messages"] > 0 :
                queuesNamesToMigrate.append(q["name"])
                queuesToMigrate.append(q)

    if len(queuesToMigrate) > 0:
        print "Detected following non-empty queues:"
        for q in queuesToMigrate:
            print " - %s (%d)" % (q["name"], q["messages"])

    return queuesNamesToMigrate

def stop_transfer(source_http, source_vhost):
    print "Stop Transfer messages from [vhost %s at %s]" % (source_vhost, source_http)

    source_credentials = extract_credentials(source_http)
    source_base_url = remove_credentials_from_url(source_http)

    source_credentials = extract_credentials(source_http)
    source_base_url = remove_credentials_from_url(source_http)

    resp = get_from(source_base_url, source_credentials, shovels(source_vhost))
    list_of_shovels = json.load(resp)

    for s in list_of_shovels :
        delete_from(source_base_url, source_credentials, shovel_parameter(source_vhost, s["name"]))
        print "Deleted shovel %s " % (s["name"])


def hello():
    print "hello"

def shovel(base_url, credentials, vhost, queuesToMigrate, source_amqp, target_amqp):
    for queue in queuesToMigrate:
        print "Creating Shovel for queue %s " % (queue)

        shovelConfig = {
            'value' : {
                'src-uri' : source_amqp,
                'src-queue' : queue,
                'dest-uri' : target_amqp,
                'dest-queue' : queue,
                'ack-mode' : "on-confirm"
            }
        }
        resp = put_into(base_url, credentials, shovel_parameter(vhost, queue), json.dumps(shovelConfig))

def wait_until_all_shovels_complete(base_url, credentials, vhost):
    shovelsAtWork = True
    while shovelsAtWork:

        resp = get_from(base_url, credentials, shovels(vhost))
        list_of_shovels = json.load(resp)

        shovelsAtWork = False
        shovelsInAction = 0;
        for s in list_of_shovels :
            if s["state"] <> "terminated" :
                shovelsAtWork = True
                shovelsInAction += 1;

        if shovelsAtWork :
            print 'Still migrating %d queues ' % (shovelsInAction)
            sys.stdout.flush()
            time.sleep( monitorShovelIntervalSec )

    print 'All shovels have completed'

def assert_all_queues_are_empty_or_fail(base_url, credentials, vhost):

    queuesToMigrate = find_queues_with_messages(base_url, credentials, vhost)

    if len(queuesToMigrate) > 0:
        print "Transfer did not complete. There are %d queues with content" % (len(queuesToMigrate))
        exit -1
    else: print "Transfer Completed "
