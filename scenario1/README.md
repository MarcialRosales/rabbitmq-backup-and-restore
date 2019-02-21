# Scenario 1 - Backup a vhost onto another vhost on another RabbitMQ cluster running in GCP

**Table of Content**

- [Introduction](#Introduction)  
- [What we are going to](#what-we-are-going-to-do)  
- [Roles and responsibilities](#roles-and-responsibilities)
- [Getting started](#Getting-started)  
  - [Get Kubernetes ready](#Get-Kubernetes-ready)  
  - [Get helm ready](#Get-helm-ready)
- [Deploy RabbitMQ cluster et al.](#deploy-rabbitmq-cluster-et-al)
- [Let's transfer messages from main to dr site](#lets-transfer-messages-from-main-to-dr-site)
- [Let's simulate a typical blue/green deployment](#lets-simulate-a-typical-bluegreen-deployment)
- [Appendix](#appendix)
  - [Using the scripts outside of this repository](#using-the-scripts-outside-of-this-repository)
  - [Getting started with Google Cloud Platform](#getting-started-with-google-cloud-platform)

**TODO**
- Declare users via the helm chart configuration.
- Add failures we could encounter with Shovel

## Introduction
We want to move all the messages from a vhost on RabbitMQ cluster onto another another RabbitMQ cluster. The reasons why we need to do that are not important but imagine that we are upgrading a RabbitMQ cluster and we do not want to take any chances with the messages should the upgrade failed. Therefore, the first thing we do is to move all the messages to a **backup** RabbitMQ cluster until we complete the upgrade and then we move back all the messages from the **backup** RabbitMQ cluster to the former cluster.

We want to move messages in a secure way therefore we need to use TLS in all the communications.

## What we are going to do
In this scenario, we are going to:
1. Issue CA certificate, and PrivateKey+Certificate for both RabbitMQ Clusters
2. Deploy 2 RabbitMQ clusters on Kubernetes configured with TLS. Each cluster will be deployed on a separate namespace representing an hypothetical site. The sites/namespaces are `main-site` and `dr-site`
3. Deploy a consumer and producer application so that we produce and consume messages to/from any site
4. Produce a backlog of messages
5. Transfer all messages (over AMQPS) on a *vhost* -regardless on which queue they are- from `main site` to the `dr site`

This scenario will use the [Shovel plugin](https://www.rabbitmq.com/shovel.html) to move messages between clusters. To use this plugin we need to set [Per-vhost parameters](https://www.rabbitmq.com/parameters.html#parameter-management).

```
  ----main-site k8s namespace-------------    ----dr-site k8s namespace-------------

    [svc:rmq-main-site-rabbitmq]<------shovel------>[svc:rmq-dr-site-rabbitmq]
        /\     /\                                             /\     /\
         |      |                                             |      |
         |  [deploy:tx-prducer]                               |  [deploy:tx-prducer]
         |                                                    |
    [deploy:tx-consumer]                                  [deploy:tx-consumer]

  ---------------------------------------    ---------------------------------------

```
**Note**: All communications represented in the diagram with arrows are within the k8s cluster. We are not representing the communication from our localhost to the management port via *port forwarding*.

## Roles and responsibilities

In terms of roles and/or permissions we need:

A **RabbitMQ user**, that from on we are going to name it `br_user`:
  - with the *user tag* [policymaker](https://www.rabbitmq.com/management.html#permissions). This *user tag* allows the user to set [Per-vhost parameters](https://www.rabbitmq.com/parameters.html#parameter-management) required to set up shovel
  - with access to the *vhost* in the RabbitMQ Cluster where we are going to set the shovel
    > We can set the shovel in either cluster, the source or the target. In this scenario, we have chosen to set the shovel in the source cluster.
  - with *user tag* [monitoring](https://www.rabbitmq.com/management.html#permissions) so that this user can check the shovels' status  
  - with [configure](https://www.rabbitmq.com/access-control.html) and [write](https://www.rabbitmq.com/access-control.html) permissions to any queue in the target *vhost* / RabbitMQ Cluster.


We will automatically create this `br_user` user with the above requirements in both clusters. Therefore, both RabbitMQ Clusters will have at least the `admin`:`admin` user with `administrator` *user tag* and `br-user` with the `policymaker` and `monitoring` *user tag*.

Additionally, we have created separate users for the consumer (`consumer:consumer`) and producer (`producer:producer`) applications.

## Getting started

### Get Kubernetes ready
We are going to deploy RabbitMQ and the applications on kubernetes. Check out the section [Getting started with Google Cloud Platform](#Getting-started-with-Google-Cloud-Platform) to get your local environment ready to operate with GCP tools.

### Get helm ready
We are going to use this [Helm chart](https://github.com/helm/charts/blob/master/stable/rabbitmq-ha) to deploy RabbitMQ. You can see what *stable* releases of this chart are available [here](https://console.cloud.google.com/storage/browser/kubernetes-charts?prefix=rabbitmq).

  Before deploying the helm chart we are going to update the helm repositories so that it deploys the latest:
  ```bash
  helm repo update
  ```

## Deploy scenario

### 1. Deploy RabbitMQ cluster et al.
Run the following command to deploy both sites and the RabbitMQ Cluster on each site:
```bash
make create-sites
make generate-ca-certificate
make start-rabbitmq
```

It takes some time to get the cluster ready. Once it is ready we can see it by running:
```bash
helm list
```
```
NAME     	REVISION	UPDATED                 	STATUS  	CHART         	NAMESPACE
rmq-main-site	1       	Wed Feb 20 11:54:42 2019	DEPLOYED	rabbitmq-ha-1.19.0	3.7.8      	main-site
rmq-dr-site	1       	Wed Feb 20 11:54:42 2019	DEPLOYED	rabbitmq-ha-1.19.0	3.7.8      	dr-site
```  

If you want to use `kubectl` to see services, deployments and pods, we have facilitated 2 scripts to conveniently switch between sites/namespaces. See below:

```bash
$ bin/current-ns
dr-site
```

```bash
$ bin/switch-ns
Switching to main-site
Context "gke_cf-rabbitmq_europe-west1-c_cluster-1" modified.
```

```bash
$ bin/current-ns
main-site
```


Let's find out what we have deployed so far:
```bash
$ bin/switch-ns main-site
$ kubectl get services
```
```
NAME                              TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)                                          AGE
rmq-main-site-rabbitmq-ha             ClusterIP   None         <none>        15672/TCP,5672/TCP,4369/TCP,5671/TCP   4m
rmq-main-site-rabbitmq-ha-discovery   ClusterIP   None         <none>        15672/TCP,5672/TCP,4369/TCP,5671/TCP   4m
```

### 2. Deploy consumer and producer application  

First of all we need to create the users for both applications. We could have done that when we deployed the Rabbitmq chart; but we preferred to separate user creation from the RabbitMQ cluster deployment.

We are going to create users via the Management API. And we want to operate from outside of the kubernetes cluster, hence we need to expose that management port. Run the following each command on a separate terminal:
```
make enable-mgt-to-main-rabbitmq
```
```
make enable-mgt-to-dr-rabbitmq
```

Now, we can the following commands to deploy both applications in the `main-site`:
```
make declare-app-users
make start-main-producer
make start-main-consumer
```

### 3. Let's transfer messages from main to dr site
If we want to see in action how to transfer messages we need to produce a message backlog. For that, we stop the consumer app and then producer app. The lag between stopping both will produce enough messages to demonstrate how to transfer those messages.

> We use RabbitMQ PerfTest to deploy the consumer and producer applications. They have been configured to publish/consume to/from 10 queues. The producer will publish a message every second.

  **Important note about Shovel**: We are using [Shovel plugin](https://www.rabbitmq.com/shovel.html) to transfer messages. We need to create a **shovel** per queue and a unique name within the **vhost** where we create it. The tool we have created assumes there are no shovels in the vhost.

  **Important note about securing Shovel connections with TLS**: To secure the connection between the two sites, we are going to use [AMQPS protocol with Shovel](https://www.rabbitmq.com/shovel.html#tls-connections). Both clusters have been already configured. The following command allows us to check if AMPQS (`5671`) port is ready:
  ```
  kubectl exec -it rmq-main-site-rabbitmq-ha-0 rabbitmq-diagnostics check_port_listener 5671
  ```


1. Stop the consumer application
 ```
 make stop-main-consumer
 ```
2. Stop the producer application
 ```
 make stop-main-producer
 ```
3. Transfer messages
 ```bash
 make start-main-transfer
 ```
 It should print out something like this:
 ```
 Transfer messages [vhost %2F at amqp://] -> [vhost %2F at amqps://br_user:br_user@rmq-dr-site-rabbitmq-ha.dr-site:5671?cacertfile=/etc/cert/cacert.pem&certfile=/etc/cert/cert.pem&keyfile=/etc/cert/key.pem&verify=verify_none]
  Setting up shovel at [vhost %2F at http://br_user:br_user@localhost:15672]
  Detected following non-empty queues:
   - perf-test-001 (925)
   - perf-test-002 (925)
   - perf-test-003 (925)
   - perf-test-004 (925)
   - perf-test-005 (924)
   - perf-test-006 (924)
   - perf-test-007 (924)
   - perf-test-008 (924)
   - perf-test-009 (924)
   - perf-test-010 (924)
  Creating Shovel for queue perf-test-001
  Creating Shovel for queue perf-test-002
  Creating Shovel for queue perf-test-003
  Creating Shovel for queue perf-test-004
  Creating Shovel for queue perf-test-005
  Creating Shovel for queue perf-test-006
  Creating Shovel for queue perf-test-007
  Creating Shovel for queue perf-test-008
  Creating Shovel for queue perf-test-009
  Creating Shovel for queue perf-test-010
  ```
  We can monitor the shovels in the management ui too:

  ![shovel status](assets/shovel-status.png)

4. Check how the transfer is going
 ```bash
 make check-main-transfer
 ```
 If the queues are empty, this command will  print out:
 ```
 Check Transfer messages from [vhost %2F at http://admin:admin@localhost:15672]
 The following shovels are still running. Stop them to complete the transfer
 - perf-test-001
 - perf-test-002
 - perf-test-003
 - perf-test-004
 - perf-test-005
 - perf-test-006
 - perf-test-007
 - perf-test-008
 - perf-test-009
 - perf-test-010
 ```
5. Terminate the transfer when there are no messages left
 ```bash
 make stop-main-transfer
 ```
 It should print out:
 ```
 Stop Transfer messages from [vhost %2F at http://admin:admin@localhost:15672]
Deleted shovel perf-test-001
Deleted shovel perf-test-002
Deleted shovel perf-test-003
Deleted shovel perf-test-004
Deleted shovel perf-test-005
Deleted shovel perf-test-006
Deleted shovel perf-test-007
Deleted shovel perf-test-008
Deleted shovel perf-test-009
Deleted shovel perf-test-010
```

At this point, we can proceed with the upgrade of the main site without being worried about the messages.

**NOTE about backing up definitions**: We are not backing up all the definitions, we are only transferring messages !!! You are wondering if we need to declare the queue(s) in the target cluster (e.g. `dr-site` cluster) before moving the messages. The answer is that shovel will take care of that. It will create a queue in the target cluster with the same definition as the source queue. This will not happen with federated queues though.

Once the main site is ready, we can move the messages back to the main site.
1. Transfer messages from `dr-site`
  ```
  make start-dr-transfer
  ```
2. Check the transfer has completed and stop it afterwards
  ```
  make check-dr-transfer
  make stop-dr-transfer
  ```

### 4. Let's simulate a typical blue/green deployment
To transfer messages from one cluster to another we used [Shovel plugin](https://www.rabbitmq.com/shovel.html). We can configure the **shovel plugin** to delete itself when it empties the source queue. This is pretty convenient because we don't need to delete them however we have to be certain there wont be further messages coming in.

Imagine a blue/green deployment where we prefer to move consumer applications and then producers. In this scenario, producers will be until the last minute publishing messages. Furthermore, we do not want to wait until publisher applications are moved to start transferring messages. So the sequence is as follows:

1. Let's bring up the "blue" deployment on the main site. Start the producer and consumer apps in the main site:
  ```
  make start-main-consumer
  make start-main-producer
  ```
  Check in the [management ui](http://localhost:15672/#/login/admin/admin) of the main site that there are messages being published and consumed.

2. Let's initiate blue/green deployment. Stop the consumer in the main site and start it in the dr site:
  ```
  make stop-main-consumer
  make start-dr-consumer
  ```
  Check in the [management ui](http://localhost:15673/#/login/admin/admin) of the dr site that we have a consumer

3. Start transfer from main site to dr site
  ```
  make start-main-transfer
  ```
  Check messages are being consumed from main site

4. Stop producer in the main site and start it on the dr site
  ```
  make stop-main-producer
  make start-dr-producer
  ```

5. Check the transfer has been completed and if so, stop it.
  ```
  make check-main-transfer
  make stop-main-transfer
  ```

If we wanted to move the messages back from dr to main site we use the corresponding commands `make start-dr-transfer`, `make check-dr-transfer`, `make stop-dr-transfer`.


### 5. To delete everything when ready
Once you are done with this scenario you can delete everything with the following command:
```bash
make destroy-all
```

To know all the available actions/commands simply run:
```
make
```

## Appendix

### Using the scripts outside of this repository

To transfer messages from cluster **A** to cluster **B**, first of all you need all the python files (`shovel.py`, `start-transfer.py`, `check-transfer.py` and `stop-transfer.py`).

To start transferring messages you invoke the following command:
```
MAIN_MGT_URL= <put here the mgt uri of the source cluster in the form  http[s]://username:password@hostname:port >
DR_AMQP_URL = <put here the amqp uri of the target cluster >
SOURCE_VHOST = <by default it is %2F >
TARGET_VHOST = <by default it is %2F >

start-transfer.py --source-http $(MAIN_MGT_URL) --target-amqp $(DR_AMQP_URL)
                [--source-vhost $(SOURCE_VHOST)] [--target-vhost $(TARGET_VHOST)]
```



### Getting started with Google Cloud Platform

#### Get the tools
We are going to operate via command-line, not via the UI. For this reason, we need to install `gcloud`, `kubectl` and `helm`.

To install gcloud and kubectl, perform the following steps:

[] [Install the Google Cloud SDK](https://cloud.google.com/sdk/docs/quickstarts), which includes the gcloud command-line tool.
[] After installing Cloud SDK, install the kubectl command-line tool by running the following command:
  ```
  gcloud components install kubectl
  ```
[] Install Helm following the [instructions](https://docs.helm.sh/using_helm/#install-helm).

#### Connect to gcloud to your project
At this point, you must have an account in GCP and a default project.

```bash
$ gcloud config set project [your PROJECT_ID]
$ gcloud config set compute/zone [your COMPUTE_ZONE or region such as us-west1-a]
```

To see the current configuration run this command:
```bash
$ gcloud config list
```
```
[compute]
region = europe-west1
zone = europe-west1-b
[core]
account = mrosales@pivotal.io
disable_usage_reporting = True
project = cf-rabbitmq

Your active configuration is: [cf-rabbitmq]
```

> Optionally, you can manage your cluster via the GCP console, e.g. https://console.cloud.google.com/kubernetes/clusters

#### Create a cluster if you dont have one yet

```bash
$ gcloud container clusters create [CLUSTER_NAME]
```

```bash
gcloud container clusters list
```
```
NAME       LOCATION        MASTER_VERSION  MASTER_IP      MACHINE_TYPE   NODE_VERSION  NUM_NODES  STATUS
cluster-1  europe-west1-c  1.11.5-gke.5    35.205.181.90  n1-standard-1  1.11.5-gke.5  3          RUNNING
```

After creating your cluster, you need to get authentication credentials to interact with the cluster. It automatically generates `kubeconfig` so that we can interact with the cluster with `kubectl`.
```bash
$ gcloud container clusters get-credentials --region=[COMPUTE_ZONE] [CLUSTER_NAME]
```

Check what deployments are currently available:
```bash
$ kubectl kubectl get deployments
```
```
No resources found.
```

Check what services are currently available:
```bash
$ kubectl get services
```
```
NAME         TYPE        CLUSTER-IP    EXTERNAL-IP   PORT(S)                       AGE
kubernetes   ClusterIP   10.47.240.1   <none>        443/TCP                       38d
rabbitmq     ClusterIP   None          <none>        4369/TCP,5672/TCP,25672/TCP   10d
```

It looks like there is one rabbitmq service currently deployed.

#### Delete our cluster

```
gcloud container clusters delete [CLUSTER_NAME]
```
