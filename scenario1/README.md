# Scenario 1 - Backup a vhost on RabbitMQ cluster onto another vhost on another RabbitMQ cluster running in GCP

## Deploy RabbitMQ clusters

1. We are going to RabbitMQ in Kubernetes. Check out [About Google Cloud Platform](#About-Google-Cloud-Platform) section for instructions on how to get started.

2. We are going to use this [Helm chart](https://github.com/helm/charts/blob/master/stable/rabbitmq) to deploy RabbitMQ. You can see what *stable* releases of this chart are available [here](https://console.cloud.google.com/storage/browser/kubernetes-charts?prefix=rabbitmq).

  Before deploying the helm chart we are going to update the helm repositories so that it deploys the latest:
  ```bash
  helm repo update
  ```
3. We are deploying 2 RabbitMQ Clusters, `rmq-main-site` as the **main** site and  `rmq-dr-site` as the **DR** site.

  Relevant [RabbitMQ configuration](/conf/rabbitmq-helm-values.yaml):
  - RabbitMQ docker image `bitnami/rabbitmq` version 3.7.10
  - 3 node cluster with *autoheal* cluster partition handling
  - federation plugin installed
  - Default credentials: admin/admin

  ```
  ./switch-ns main-site
  ./start-rabbitmq

  ./switch-ns dr-site
  ./start-rabbitmq

  ./switch-ns main-site
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
