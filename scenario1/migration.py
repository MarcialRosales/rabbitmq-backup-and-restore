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
dest_http_host="localhost"
src_amqp_host="localhost"
src_http_port="15672"

src_amqp_port="5672"
src_node_name="node1"
src_vhost="test1"
src_username="user"
src_password="user"

dest_host="localhost"
dest_http_port="15674"
dest_amqp_port="5674"
dest_username="user2"
dest_password="user2"
dest_vhost="NewVH"

monitorShovelIntervalSec=30

apiUrl          = "http://%s:%s/api" % (src_http_host, src_http_port)
queuesUrl       = apiUrl + "/queues/%s" % ( src_vhost)
connectionsUrl  = apiUrl + "/vhosts/%s/connections" % ( src_vhost)
shovelUrl       = apiUrl + "/parameters/shovel/%s" % ( src_vhost )
shovelsUrl      = apiUrl + "/shovels"

destApiUrl      = "http://%s:%s/api" % (dest_http_host, dest_http_port)
putQueueUrl     = destApiUrl + "/queues/%s" % ( dest_vhost)

#*****************************************************************************************
# 1. Get information about queues to migrate: Select queues which are not empty
queuesRequest = urllib2.Request(queuesUrl)
base64string = base64.encodestring('%s:%s' % (src_username, src_password)).replace('\n', '')
dest_base64string = base64.encodestring('%s:%s' % (dest_username, dest_password)).replace('\n', '')
queuesRequest.add_header("Authorization", "Basic %s" % base64string)

resp = urllib2.urlopen(queuesRequest)
jsonQueues = json.load(resp)

queuesToMigrate = [];
jsonQueuesToMigrate = [];
if len(jsonQueues) <= 0:
    print "No queues detected"
else:
    for q in jsonQueues:
        print "%s (%d)" % (q["name"], q["messages"])
        if q["messages"] > 0 :
            queuesToMigrate.append(q["name"])
            jsonQueuesToMigrate.append(q)


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

for q in jsonQueuesToMigrate:

    print "Creating queue %s with arguments %s in dest" % (q["name"], json.dumps(q["arguments"]))
    putQueueBody = {"auto_delete":"false","durable":"true","arguments": q["arguments"]}
    finalPutQueueUrl = putQueueUrl + "/" + q["name"]
    print "using url : %s with body :  %s " % (finalPutQueueUrl, json.dumps(putQueueBody))

    req = urllib2.Request(finalPutQueueUrl, data=json.dumps(putQueueBody))
    req.add_header("Authorization", "Basic %s" % dest_base64string)
    req.add_header("Content-Type", "application/json")
    req.get_method = lambda : 'PUT'
    resp = urllib2.urlopen(req)


for x in queuesToMigrate:
    print "Creating Shovel for queue %s " % (x)

    shovelConfig = {
        'value' : {
            'src-uri' : "amqp://%s:%s@%s:%s/%s" % ( src_username, src_password, src_amqp_host, src_amqp_port, src_vhost ),
            'src-queue' : x,
            'dest-uri' : "amqp://%s:%s@%s:%s/%s" % ( dest_username, dest_password, dest_host, dest_amqp_port, dest_vhost ),
            'dest-queue' : x,
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
