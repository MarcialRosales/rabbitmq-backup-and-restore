.ONESHELL:# single shell invocation for all lines in the recipe
SHELL = bash# we depend on bash expansion for e.g. queue patterns

.DEFAULT_GOAL = help

# PORTS
MAIN_MGT_PORT := 15672
DR_MGT_PORT := 15673

# CREDENTIALS
ADMIN_CREDENTIALS := "admin:admin"
BR_CREDENTIALS := "br_user:br_user"
CONSUMER_CREDENTIALS := "consumer:consumer"
PRODUCER_CREDENTIALS := "producer:producer"

# MGT URLs
MAIN_MGT_URL_FOR_BR_USER := "http://$(BR_CREDENTIALS)@localhost:$(MAIN_MGT_PORT)"
DR_MGT_URL_FOR_BR_USER := "http://$(BR_CREDENTIALS)@localhost:$(DR_MGT_PORT)"

# AMQP URLS
MAIN_AMQP_URL_FOR_BR_USER := "amqp://$(BR_CREDENTIALS)@rmq-main-site-rabbitmq-ha.main-site:5672"
DR_AMQP_URL_FOR_BR_USER := "amqp://$(BR_CREDENTIALS)@rmq-dr-site-rabbitmq-ha.dr-site:5672"

MAIN_AMQP_URL_FOR_CONSUMER := "amqp://$(CONSUMER_CREDENTIALS)@rmq-main-site-rabbitmq-ha.main-site:5672"
MAIN_AMQP_URL_FOR_PRODUCER := "amqp://$(PRODUCER_CREDENTIALS)@rmq-main-site-rabbitmq-ha.main-site:5672"

DR_AMQP_URL_FOR_CONSUMER := "amqp://$(CONSUMER_CREDENTIALS)@rmq-dr-site-rabbitmq-ha.dr-site:5672"
DR_AMQP_URL_FOR_PRODUCER := "amqp://$(PRODUCER_CREDENTIALS)@rmq-dr-site-rabbitmq-ha.dr-site:5672"

# AMPQS URLS
TLS := cacertfile=/etc/cert/cacert.pem&certfile=/etc/cert/cert.pem&keyfile=/etc/cert/key.pem&verify=verify_none

MAIN_AMQPS_URL_FOR_BR_USER := "amqps://$(BR_CREDENTIALS)@rmq-main-site-rabbitmq-ha.main-site:5671?$(TLS)"
DR_AMQPS_URL_FOR_BR_USER := "amqps://$(BR_CREDENTIALS)@rmq-dr-site-rabbitmq-ha.dr-site:5671?$(TLS)"

### TARGETS ###

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

destroy-all: stop-apps stop-rabbitmq delete-sites ## Destroy entire topology

start-rabbitmq: start-main-rabbitmq start-dr-rabbitmq ## Start RabbitMQ cluster on both sites

stop-rabbitmq: stop-main-rabbitmq stop-dr-rabbitmq ## Stop RabbitMQ cluster on both sites

declare-app-users:
	@curl -u ${ADMIN_CREDENTIALS} -X POST -H "Content-Type: application/json" http://localhost:$(MAIN_MGT_PORT)/api/definitions -d "@topology/app_users.json"
	@curl -u ${ADMIN_CREDENTIALS} -X POST -H "Content-Type: application/json" http://localhost:$(DR_MGT_PORT)/api/definitions -d "@topology/app_users.json"

start-main-rabbitmq: ## Start rabbitmq cluster in main site
	@bin/switch-ns main-site
	@bin/start-rabbitmq
	@echo "Run make enable-mgt-to-main-rabbitmq on a separate terminal to enable access to mgt interface on $(MAIN_MGT_PORT)"

check-main-rabbitmq: ## Check rabbitmq cluster status in main site
	@bin/check-rabbitmq main-site $(MAIN_MGT_PORT) $(ADMIN_CREDENTIALS)

stop-main-rabbitmq: ## Stop rabbitmq cluster in main site
	@bin/switch-ns main-site
	@bin/stop-rabbitmq

start-dr-rabbitmq: ## Start rabbitmq cluster in dr site
	@bin/switch-ns dr-site
	@bin/start-rabbitmq
	@echo "Run make enable-mgt-to-dr-rabbitmq on a separate terminal to enable access to mgt interface on $(DR_MGT_PORT)"

check-dr-rabbitmq: ## Check rabbitmq cluster status in dr site
	bin/check-rabbitmq dr-site $(DR_MGT_PORT) $(ADMIN_CREDENTIALS)

stop-dr-rabbitmq: ## Stop rabbitmq cluster in dr site
	@bin/switch-ns dr-site
	@bin/stop-rabbitmq

create-sites: ## Create k8s namespaces for each site: main & dr
	@kubectl apply -f topology/main-site-namespace.yml
	@kubectl apply -f topology/dr-site-namespace.yml
	@kubectl get namespaces --show-labels

delete-sites: ## Delete k8s namespaces for each site: main & dr
	@kubectl delete namespaces main-site
	@kubectl delete namespaces dr-site

enable-mgt-to-main-rabbitmq: ## Enable Access the RabbitMQ Management interface on local port $(MAIN_MGT_PORT)
	@kubectl port-forward --namespace main-site svc/rmq-main-site-rabbitmq-ha $(MAIN_MGT_PORT):15672

enable-mgt-to-dr-rabbitmq: ## Enable Access the RabbitMQ Management interface on local port $(DR_MGT_PORT)
	@kubectl port-forward --namespace dr-site svc/rmq-dr-site-rabbitmq-ha $(DR_MGT_PORT):15672

stop-apps: stop-main-producer stop-main-consumer stop-dr-producer stop-dr-consumer ## Stop all applications, producer & consumer in both sites

start-main-producer: ## Start producer on main site
	@bin/switch-ns main-site
	@kubectl delete configmap producer-config --ignore-not-found=true
	@kubectl create configmap producer-config --from-literal=RABBITMQ_AMQP_URI=$(MAIN_AMQP_URL_FOR_PRODUCER)
	@kubectl apply -f topology/tx-producer.yml

stop-main-producer: ## Stop producer on main site
	@bin/switch-ns main-site
	kubectl delete -f topology/tx-producer.yml --ignore-not-found=true

stop-main-consumer: ## Stop consumer on main site
	@bin/switch-ns main-site
	kubectl delete -f topology/tx-consumer.yml --ignore-not-found=true

start-main-consumer: ## Start consumer on main site
	@bin/switch-ns main-site
	@kubectl delete configmap consumer-config --ignore-not-found=true
	@kubectl create configmap consumer-config --from-literal=RABBITMQ_AMQP_URI=$(MAIN_AMQP_URL_FOR_CONSUMER)
	@kubectl apply -f topology/tx-consumer.yml

start-dr-producer: ## Start producer on dr site
	@bin/switch-ns dr-site
	@kubectl delete configmap producer-config --ignore-not-found=true
	@kubectl create configmap producer-config --from-literal=RABBITMQ_AMQP_URI=$(DR_AMQP_URL_FOR_PRODUCER)
	@kubectl apply -f topology/tx-producer.yml

stop-dr-producer: ## Stop producer on dr site
	@bin/switch-ns dr-site
	kubectl delete -f topology/tx-producer.yml --ignore-not-found=true

start-dr-consumer: ## Start consumer on dr site
	@bin/switch-ns dr-site
	@kubectl delete configmap consumer-config --ignore-not-found=true
	@kubectl create configmap consumer-config --from-literal=RABBITMQ_AMQP_URI=$(DR_AMQP_URL_FOR_CONSUMER)
	@kubectl apply -f topology/tx-consumer.yml

stop-dr-consumer: ## Stop consumer on main site
	@bin/switch-ns dr-site
	kubectl delete -f topology/tx-consumer.yml --ignore-not-found=true

declare-main-br-user:
	@curl -u $(ADMIN_CREDENTIALS) -X POST -H "Content-Type: application/json" http://localhost:$(MAIN_MGT_PORT)/api/definitions -d "@topology/br_user.json"

declare-dr-br-user:
	@curl -u $(ADMIN_CREDENTIALS) -X POST -H "Content-Type: application/json" http://localhost:$(DR_MGT_PORT)/api/definitions -d "@topology/br_user.json"

declare-br-user: declare-main-br-user declare-dr-br-user

start-main-transfer: declare-br-user ## Transfer messages (over AMQPS) on default vhost from main site to dr site on any queue
	@bin/start-transfer.py --source-http $(MAIN_MGT_URL_FOR_BR_USER) --target-amqp $(DR_AMQPS_URL_FOR_BR_USER)

start-main-transfer-insecure: declare-br-user ## Transfer messages (over AMQP) on default vhost from main site to dr site on any queue
	@bin/start-transfer.py --source-http $(MAIN_MGT_URL_FOR_BR_USER) --target-amqp $(DR_AMQP_URL_FOR_BR_USER)

stop-main-transfer: declare-br-user ## Stop transferring messages on default vhost from main site to dr site on any queue
	@bin/stop-transfer.py --source-http $(MAIN_MGT_URL_FOR_BR_USER)

check-main-transfer: declare-br-user ## Check status of transfer from main site to dr site on default vhost
	@bin/check-transfer.py --source-http $(MAIN_MGT_URL_FOR_BR_USER)

start-dr-transfer: declare-br-user ## Transfer messages (over AMQPS) on default vhost from dr site to main site on any queue
	@bin/start-transfer.py --source-http $(DR_MGT_URL_FOR_BR_USER) --target-amqp $(MAIN_AMQPS_URL_FOR_BR_USER)

start-dr-transfer-insecure: declare-br-user ## Transfer messages (over AMQP) on default vhost from dr site to main site on any queue
	@bin/start-transfer.py --source-http $(DR_MGT_URL_FOR_BR_USER) --target-amqp $(MAIN_AMQP_URL_FOR_BR_USER)

stop-dr-transfer: declare-br-user ## Stop transferring messages on default vhost from dr site to main site on any queue
	@bin/stop-transfer.py --source-http $(DR_MGT_URL_FOR_BR_USER)

check-dr-transfer: declare-br-user ## Check status of transfer from dr site to main site on default vhost
	@bin/check-transfer.py --source-http $(DR_MGT_URL_FOR_BR_USER)

clean-secrets:
	@rm -rf secrets

generate-ca-certificate: clean-secrets ## Generate CA certificate for AMQPS
	@mkdir -p secrets/private
	@mkdir -p secrets/certs
	@chmod 700 secrets/private
	@echo 01 > secrets/serial
	@touch secrets/index.txt
	@cp topology/openssl.cnf secrets
	@docker run -it -v $(shell pwd)/secrets:/export frapsoft/openssl req -x509 -config /export/openssl.cnf  -newkey rsa:2048 -days 365 -out /export/cacert.pem -outform PEM -subj /CN=MyTestCA/ -nodes
	@docker run -it -v $(shell pwd)/secrets:/export frapsoft/openssl x509 -in /export/cacert.pem -out /export/cacert.cer -outform DER
