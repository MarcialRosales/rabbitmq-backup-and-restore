#!/usr/bin/python

import os
import sys
import time
import json
import urllib2
import base64
import socket
import subprocess

src_http_host="localhost"
src_amqp_host="localhost"
src_http_port="15672"
src_amqp_port="5672"
src_node_name="node1"
src_vhost="test1"
src_username="user"
src_password="user"

dest_host="localhost"
dest_amqp_port="5674"
dest_username="user2"
dest_password="user2"
dest_vhost="NewVH"

monitorShovelIntervalSec=30

apiUrl          = "http://%s:%s/api" % (src_http_host, src_http_port)
queuesUrl       = apiUrl + "/queues/%s" % ( src_vhost)
putExchangeUrl  = apiUrl + "/exchanges/%s" % ( src_vhost)
putQueueUrl     = apiUrl + "/queues/%s" % ( src_vhost)
putBindingUrl   = apiUrl + "/bindings/%s" % ( src_vhost)
connectionsUrl  = apiUrl + "/vhosts/%s/connections" % ( src_vhost)
shovelUrl       = apiUrl + "/parameters/shovel/%s" % ( src_vhost )
shovelsUrl      = apiUrl + "/shovels"

#*****************************************************************************************
# 1. Get information about queues to migrate: Select queues which are not empty
queuesRequest = urllib2.Request(queuesUrl)
base64string = base64.encodestring('%s:%s' % (src_username, src_password)).replace('\n', '')
queuesRequest.add_header("Authorization", "Basic %s" % base64string)

resp = urllib2.urlopen(queuesRequest)
jsonQueues = json.load(resp)

queuesToMigrate = [];
if len(jsonQueues) <= 0:
    print "No queues detected"
else:
    for q in jsonQueues:
        print "%s (%d)" % (q["name"], q["messages"])
        if q["messages"] > 0 : queuesToMigrate.append(q["name"])


if len(queuesToMigrate) < 1:
    print "There is nothing to migrate"
    exit();

#*****************************************************************************************
# 2. Make sure there are no AMQP connections
connectionsRequest = urllib2.Request(connectionsUrl)
connectionsRequest.add_header("Authorization", "Basic %s" % base64string)
resp = urllib2.urlopen(connectionsRequest)
jsonConnections = json.load(resp)

if len(jsonConnections) > 0: exit("There are still connections!!")


#*****************************************************************************************
# 3. Create a Shovel for each queue determined on the previous step to shovel its contents
# over to the destination cluster.

if len(queuesToMigrate) > 0: print "Creating Shovels for %d queues ...." % (len(queuesToMigrate))

for x in queuesToMigrate:
    print "Creating Exchange for queue %s " % (x)

    putExchangeBody = { "type":"fanout","auto_delete":"false","durable":"true","internal":"false","arguments":{} }
    finalPutExchangeUrl = putExchangeUrl + "/" + x + "-exchange"
    req = urllib2.Request(finalPutExchangeUrl, data=json.dumps(putExchangeBody))
    req.add_header("Authorization", "Basic %s" % base64string)
    req.add_header("Content-Type", "application/json")
    req.get_method = lambda : 'PUT'
    resp = urllib2.urlopen(req)

    print "Declaring cloned queues for queue %s " % (x)

    putQueueBody = {"auto_delete":"false","durable":"true","arguments":{}}
    finalPutQueueUrl = putQueueUrl + "/" + x + "-copy1"
    req = urllib2.Request(finalPutQueueUrl, data=json.dumps(putQueueBody))
    req.add_header("Authorization", "Basic %s" % base64string)
    req.add_header("Content-Type", "application/json")
    req.get_method = lambda : 'PUT'
    resp = urllib2.urlopen(req)

    finalPutBindingUrl = putBindingUrl + "/e/" + x + "-exchange/q/" + x + "-copy1"
    req = urllib2.Request(finalPutBindingUrl, data=json.dumps({}))
    req.add_header("Authorization", "Basic %s" % base64string)
    req.add_header("Content-Type", "application/json")
    req.get_method = lambda : 'POST'
    resp = urllib2.urlopen(req)

    finalPutQueueUrl = putQueueUrl + "/" + x + "-copy2"
    req = urllib2.Request(finalPutQueueUrl, data=json.dumps(putQueueBody))
    req.add_header("Authorization", "Basic %s" % base64string)
    req.add_header("Content-Type", "application/json")
    req.get_method = lambda : 'PUT'
    resp = urllib2.urlopen(req)

    finalPutBindingUrl = putBindingUrl + "/e/" + x + "-exchange/q/" + x + "-copy2"
    req = urllib2.Request(finalPutBindingUrl, data=json.dumps({}))
    req.add_header("Authorization", "Basic %s" % base64string)
    req.add_header("Content-Type", "application/json")
    req.get_method = lambda : 'POST'
    resp = urllib2.urlopen(req)



for x in queuesToMigrate:
    print "Creating Shovel for queue %s " % (x)

    shovelConfig = {
        'value' : {
            'src-uri' : "amqp://%s:%s@%s:%s/%s" % ( src_username, src_password, src_amqp_host, src_amqp_port, src_vhost ),
            'src-queue' : x,
            'dest-uri' : "amqp://%s:%s@%s:%s/%s" % ( src_username, src_password, src_amqp_host, src_amqp_port, src_vhost ),
            'dest-exchange' : x + ".exchange",
            'ack-mode' : "on-confirm",
            'delete-after' : "queue-length",
        }
    }

    newShovelUrl = shovelUrl + "/" + x
    shovelReq = urllib2.Request(newShovelUrl, data=json.dumps(shovelConfig))
    shovelReq.add_header("Authorization", "Basic %s" % base64string)
    shovelReq.add_header("Content-Type", "application/json")
    shovelReq.get_method = lambda : 'PUT'
    resp = urllib2.urlopen(shovelReq)

#*****************************************************************************************
# 4. Wait for all shovels to finish processing abandoned queues
# Assumption here is that no other Shovels than those created by us are configured and
# used in the system.
# We do that by querying the Shovel plugin REST API for the shovel status.

shovelsAtWork = True
while shovelsAtWork:

    shovelsReq = urllib2.Request(shovelsUrl)
    shovelsReq.add_header("Authorization", "Basic %s" % base64string)
    resp = urllib2.urlopen(shovelsReq)
    shovels = json.load(resp)

    shovelsAtWork = False
    shovelsInAction = 0;
    for s in shovels :
        if s["state"] <> "terminated" :
            shovelsAtWork = True
            shovelsInAction += 1;

    if shovelsAtWork :
        print 'Still migrating %d queues ' % (shovelsInAction)
        sys.stdout.flush()
        time.sleep( monitorShovelIntervalSec )


#*****************************************************************************************
# 5. Check if all queues are empty
queuesRequest = urllib2.Request(queuesUrl)
base64string = base64.encodestring('%s:%s' % (src_username, src_password)).replace('\n', '')
queuesRequest.add_header("Authorization", "Basic %s" % base64string)

resp = urllib2.urlopen(queuesRequest)
jsonQueues = json.load(resp)

queuesToMigrate = [];
for q in jsonQueues:
    if q["messages"] > 0 :
        print "%s (%d)" % (q["name"], q["messages"])
        queuesToMigrate.append(q["name"])

if len(queuesToMigrate) > 0:
    print "Migration did not complete. There are %d queues with content" % (len(queuesToMigrate))
else: print "Completed migration "
