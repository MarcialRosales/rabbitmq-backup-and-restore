# Scenario 1 - Backup a vhost onto another vhost on another RabbitMQ cluster running in GCP

## Introduction
We want to move all the messages from a vhost on RabbitMQ cluster onto another another RabbitMQ cluster. The reasons why we need to do that are not important but imagine that we are upgrading a RabbitMQ cluster and we do not want to take any chances with the messages should the upgrade failed. Therefore, the first thing we do is to move all the messages to a **backup** RabbitMQ cluster until we complete the upgrade and then we move back all the messages from the **backup** RabbitMQ cluster to the former cluster.

## What we are going to
In this scenario, we are going to:
1. Deploy 2 RabbitMQ clusters on Kubernetes. Each cluster will be deployed on a separate namespace representing an hypothetical site. The sites/namespaces are `main-site` and `dr-site`
2. Deploy a consumer and producer application so that we produce and consume messages to/from any site
3. Produce a backlog of messages
4. Transfer all messages -regardless on which queue they are- from main site to the dr site

## Get started

### Get Kubernetes ready
We are going to deploy RabbitMQ and the applications on kubernetes. Check out the section [About Google Cloud Platform](#About-Google-Cloud-Platform) to get your local environment ready to operate with GCP tools.

### Get helm ready
We are going to use this [Helm chart](https://github.com/helm/charts/blob/master/stable/rabbitmq) to deploy RabbitMQ. You can see what *stable* releases of this chart are available [here](https://console.cloud.google.com/storage/browser/kubernetes-charts?prefix=rabbitmq).

  Before deploying the helm chart we are going to update the helm repositories so that it deploys the latest:
  ```bash
  helm repo update
  ```

### Deploy RabbitMQ cluster et al.
To deploy the scenario run the command
```bash
make deploy-all
```

It takes some time to get the cluster ready. Once it is ready we can see it by running:
```bash
helm list
```
```
NAME     	REVISION	UPDATED                 	STATUS  	CHART         	NAMESPACE
rmq-dr-site  	1       	Fri Jan 25 15:40:27 2019	DEPLOYED	rabbitmq-4.1.0	dr-site
rmq-main-site	1       	Fri Jan 25 15:40:11 2019	DEPLOYED	rabbitmq-4.1.0	main-site
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


This will deploy the 2 sites, with a RabbitMQ cluster on each site. See below:
```bash
$ bin/switch-ns main-site
$ kubectl get services
```
```
NAME                              TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)                                          AGE
rmq-main-site-rabbitmq            ClusterIP   10.47.242.116   <none>        4369/TCP,5672/TCP,25672/TCP,15672/TCP,9090/TCP   2d
rmq-main-site-rabbitmq-headless   ClusterIP   None            <none>        4369/TCP,5672/TCP,25672/TCP,15672/TCP            2d
```


And one producer and one consumer application connected to the `main` site's RabbitMQ cluster only.
```bash
$ kubectl get deployments
```
```
NAME          DESIRED   CURRENT   UP-TO-DATE   AVAILABLE   AGE
tx-producer   1         1         1            1           2d
tx-consumer   1         1         1            1           2d
```

There are no applications connected to the `dr` site just yet.
```bash
$ bin/switch-ns dr-site
$ kubectl get deployments
```
```
No resources found.
```


### To delete everything when ready
Once you are done with this scenario you can delete everything with the following command:
```bash
make destroy-all
```

To know all the available actions/commands simply run:
```
make
```

## Let's transfer messages from main to dr site
If we want to see in action how to transfer messages we need to produce a message backlog. For that, we stop the consumer app and then producer app. The lag between stopping both will produce enough messages to demonstrate how to transfer those messages.

1. Stop the consumer application
 ```
 make stop-main-consumer
 ```
2. Stop the producer application
 ```
 make stop-main-producer
 ```
3. Transfer messages
 ```
 make start-main-transfer
 ```
4. Check how the transfer is going
 ```
 make check-main-transfer
 ```
5. Terminate the transfer when there are no messages left
 ```
 make stop-main-transfer
 ```

At this point, we can proceed with the upgrade of the main site without being worried about the messages.

**NOTE**: We are not backing up all the definitions, we are only transferring messages !!!

Once the main site is ready, we can move the messages back to the main site.
1. Transfer messages from dr
  ```
  make start-dr-transfer
  ```
2. Check the transfer has completed and stop it afterwards
  ```
  make check-dr-transfer
  make stop-dr-transfer
  ```

## Let's simulate a typical blue/green deployment
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


## About Google Cloud Platform

### Get the tools
We are going to operate via command-line, not via the UI. For this reason, we need to install `gcloud`, `kubectl` and `helm`.

To install gcloud and kubectl, perform the following steps:

[] [Install the Google Cloud SDK](https://cloud.google.com/sdk/docs/quickstarts), which includes the gcloud command-line tool.
[] After installing Cloud SDK, install the kubectl command-line tool by running the following command:
  ```
  gcloud components install kubectl
  ```
[] Install Helm following the [instructions](https://docs.helm.sh/using_helm/#install-helm).

### Connect to gcloud to your project
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

### Create a cluster if you dont have one yet

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

### Delete our cluster

```
gcloud container clusters delete [CLUSTER_NAME]
```
