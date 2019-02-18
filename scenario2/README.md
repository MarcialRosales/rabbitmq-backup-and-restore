# Backup a RabbitMQ Cluster onto another RabbitMQ cluster running in GCP

**Table of Content**

- [Introduction](#Introduction)  

## Introduction
As a continuation of [previous scenario](../scenario1/README.md), we are going to backup all vhosts from a local RabbitMQ cluster onto another cluster including its definitions (users, vhosts, queues, exchanges, etc). Essentially, we are cloning a RabbitMQ cluster. Although the word clone could lead to misinterpretation because we are moving messages, not copying. Once we complete the backup, the *backup* RabbitMQ Cluster has all the definitions of the original RabbitMQ Cluster plus its messages. Whereas the original cluster is left without messages, only with its definitions.

## What we are going to do
In this scenario, we are going to:
1. Deploy 2 RabbitMQ clusters on Kubernetes. Each cluster will be deployed on a separate namespace representing an hypothetical site. The sites/namespaces are `main-site` and `dr-site`
2. Deploy a consumer and producer application so that we produce and consume messages to/from any site
3. Produce a backlog of messages
4. Clone the RabbitMQ cluster in main site onto the dr site

This scenario will use the [Shovel plugin](https://www.rabbitmq.com/shovel.html) to move messages between clusters. To use this plugin we need to set [Per-vhost parameters](https://www.rabbitmq.com/parameters.html#parameter-management).
