.ONESHELL:# single shell invocation for all lines in the recipe
SHELL = bash# we depend on bash expansion for e.g. queue patterns

.DEFAULT_GOAL = help

MAIN_MGT_PORT := 15672
DR_MGT_PORT := 15673
MGT_CREDENTIALS := 'admin:admin'

MAIN_MGT_URL := http://$(MGT_CREDENTIALS)@localhost:$(MAIN_MGT_PORT)
DR_MGT_URL := http://$(MGT_CREDENTIALS)@localhost:$(DR_MGT_PORT)


### TARGETS ###

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

deploy-all: create-sites start-rabbitmq start-main-consumer start-main-producer ## Deploy entire topology

destroy-all: stop-apps stop-rabbitmq delete-sites ## Destroy entire topology

start-rabbitmq: start-main-rabbitmq start-dr-rabbitmq ## Start RabbitMQ cluster on both sites

stop-rabbitmq: stop-main-rabbitmq stop-dr-rabbitmq ## Stop RabbitMQ cluster on both sites

start-main-rabbitmq: ## Start rabbitmq cluster in main site
	@bin/switch-ns main
	@bin/start-rabbitmq
	@echo "Run make enable-mgt-to-main-rabbitmq on a separate terminal to enable access to mgt interface on $(MAIN_MGT_PORT)"

check-main-rabbitmq: ## Check rabbitmq cluster status in main site
	@bin/check-rabbitmq main $(MAIN_MGT_PORT) $(MGT_CREDENTIALS)

stop-main-rabbitmq: ## Stop rabbitmq cluster in main site
	@bin/switch-ns main
	@bin/stop-rabbitmq

start-dr-rabbitmq: ## Start rabbitmq cluster in dr site
	@bin/switch-ns dr
	@bin/start-rabbitmq
	@echo "Run make enable-mgt-to-dr-rabbitmq on a separate terminal to enable access to mgt interface on $(DR_MGT_PORT)"

check-dr-rabbitmq: ## Check rabbitmq cluster status in dr site
	bin/check-rabbitmq dr $(DR_MGT_PORT) $(MGT_CREDENTIALS)

stop-dr-rabbitmq: ## Stop rabbitmq cluster in dr site
	@bin/switch-ns dr
	@bin/stop-rabbitmq

create-sites: ## Create k8s namespaces for each site: main & dr
	@kubectl apply -f topology/main-site-namespace.yml
	@kubectl apply -f topology/dr-site-namespace.yml
	@kubectl get namespaces --show-labels

delete-sites: ## Delete k8s namespaces for each site: main & dr
	@kubectl delete namespaces main-site
	@kubectl delete namespaces dr-site

enable-mgt-to-main-rabbitmq: ## Enable Access the RabbitMQ Management interface on local port $(MAIN_MGT_PORT)
	@kubectl port-forward --namespace main svc/rmq-main-rabbitmq $(MAIN_MGT_PORT):15672

enable-mgt-to-dr-rabbitmq: ## Enable Access the RabbitMQ Management interface on local port $(DR_MGT_PORT)
	@kubectl port-forward --namespace main svc/rmq-main-rabbitmq $(DR_MGT_PORT):15672

stop-apps: stop-main-producer stop-main-consumer ## Stop all applications, producer & consumer in both sites

start-main-producer: ## Start producer on main site
	@bin/switch-ns main
	@kubectl apply -f topology/tx-producer.yml

stop-main-producer: ## Stop producer on main site
	kubectl delete -f topology/tx-producer.yml --ignore-not-found=true

start-main-consumer: ## Start consumer on main site
	@bin/switch-ns main
	@kubectl apply -f topology/tx-consumer.yml

stop-main-consumer: ## Stop consumer on main site
	kubectl delete -f topology/tx-consumer.yml --ignore-not-found=true

transfer: ## Transfer messages on default vhost from main site to dr site on any queue
	@bin/transfer.py --source $(MAIN_MGT_URL) --target $(DR_MGT_URL)
