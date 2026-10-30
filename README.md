# Шаблон для лабораторной работы № 5

Шаблон дает минимальный маршрут:


`клиент -> Nginx API Gateway -> REST-фасад -> gRPC-сервис`


В каркасе уже есть deadline, retry для безопасного RPC чтения, correlation ID, преобразование gRPC status в HTTP, rate limiting, Dockerfile и Kubernetes-манифесты. Cтудент адаптирует контракт, бизнес-операцию и параметры по своему варианту.

## Состав

```
proto/domain.proto                 исходный gRPC-контракт
grpc_service/                      gRPC-сервер и репозиторий
rest_facade/                       FastAPI-фасад и gRPC-клиент
gateway/                           конфигурация Nginx
k8s/                               Deployment, Service и ConfigMap
tests/                             минимальные автотесты
scripts/                           генерация кода и smoke-проверка
compose.yaml                       локальный запуск трех компонентов
```

## 1. Локальная подготовка

Требуются Python 3.11+ и venv.

```
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r grpc_service/requirements.txt
python -m pip install -r rest_facade/requirements.txt
python -m pip install -r requirements-dev.txt
./scripts/generate_proto.sh
pytest -q
```

Сгенерированные domain_pb2.py и domain_pb2_grpc.py не редактируются вручную.

## 2. Быстрый запуск через Docker Compose

```
cp .env.example .env
docker compose up --build -d
docker compose ps
./scripts/smoke_test.sh
```

Ручные запросы:

```
curl -i http://localhost:8080/health
curl -i -H 'X-Request-ID: lab5-read-01' \
  http://localhost:8080/api/v1/entities/demo-1
curl -i -X POST -H 'Content-Type: application/json' \
  -H 'X-Request-ID: lab5-command-01' \
  -d '{"command":"publish"}' \
  http://localhost:8080/api/v1/entities/demo-1/state
docker compose logs grpc-service rest-facade gateway
```

Остановка:

```
docker compose down
```

## 3. Запуск компонентов без Compose

Терминал 1:

```
PYTHONPATH=grpc_service/generated \
  python -m grpc_service.server
```

Терминал 2:

```
GRPC_TARGET=127.0.0.1:50051 \
PYTHONPATH=rest_facade/generated \
  uvicorn rest_facade.main:app --host 0.0.0.0 --port 8000
```

В локальном режиме можно вызвать REST-фасад напряму по адресу `http://localhost:8000`.

## 4. Прямая проверка gRPC

Если установлен grpcurl:

```
grpcurl -plaintext localhost:50051 list
grpcurl -plaintext -d '{"id":"demo-1"}' \
  localhost:50051 domain.v1.DomainService/GetEntity
```

## 5. Зададния по вариантам

| № | Сущность | RPC чтения | RPC команды | Deadline | Rate |
|---:|---|---|---|---:|---:|
| 1 | Product | GetProduct | PublishProduct | 350 ms | 8 r/s |
| 2 | Appointment | GetAppointment | ConfirmAppointment | 450 ms | 6 r/s |
| 3 | Notice | GetNotice | AcknowledgeNotice | 300 ms | 10 r/s |
| 4 | Procedure | GetProcedure | StartProcedure | 500 ms | 5 r/s |
| 5 | Shipment | GetShipment | DispatchShipment | 400 ms | 7 r/s |
| 6 | Application | GetApplication | SubmitApplication | 600 ms | 4 r/s |
| 7 | Session | GetSession | CloseSession | 300 ms | 10 r/s |
| 8 | Batch | GetBatch | ReleaseBatch | 450 ms | 6 r/s |
| 9 | Booking | GetBooking | ConfirmBooking | 350 ms | 8 r/s |
| 10 | Request | GetRequest | ApproveRequest | 500 ms | 5 r/s |

Обязательно измените:

1. `proto/domain.proto`: имена сервиса, сообщений и RPC.
2. `grpc_service/server.py`: реализацию двух RPC.
3. `grpc_service/repository.py`: подключение к таблицам PostgreSQL из ЛР № 3–4.
4. `rest_facade/grpc_client.py`: полное имя RPC в retry policy и deadline.
5. `rest_facade/main.py`: REST-маршруты и модель команды.
6. `gateway/nginx.conf` и `k8s/gateway-config.yaml`: значение `rate`.
7. `.env` и `k8s/rest-facade.yaml`: `GRPC_DEADLINE_SECONDS`.

После изменения .proto повторите:

```
./scripts/generate_proto.sh
pytest -q
```

## 6. Подключение к сквозному проекту

По умолчанию в repository.py используется учебное in-memory хранилище. Оно нужно только для первого запуска. В итоговом проекте замените его адаптером к существующей PostgreSQL. Не создавайте отдельную базу данных ради gRPC.

DATABASE_URL предусмотрен в .env.example и Kubernetes-манифесте. Пароль нельзя хранить в Git или отчете; в Kubernetes он должен поступать из Secret.

## 7. Сборка образов

Контекстом сборки является корень шаблона:

```
docker build -f grpc_service/Dockerfile -t <registry>/<project>-grpc:1.0.0 .
docker build -f rest_facade/Dockerfile -t <registry>/<project>-facade:1.0.0 .
docker build -f gateway/Dockerfile -t <registry>/<project>-gateway:1.0.0 .
```

## 8. Развертывание в Kubernetes

1. Замените YOUR_DOCKERHUB_USER в k8s/*.yaml.
2. При необходимости измените namespace командой -n.
3. Примените манифесты.

```
NS=lab5-<фамилия>
kubectl create namespace "$NS"
kubectl apply -n "$NS" -k k8s/
kubectl rollout status -n "$NS" deployment/domain-grpc --timeout=180s
kubectl rollout status -n "$NS" deployment/rest-facade --timeout=180s
kubectl get pods,svc,endpointslices -n "$NS"
kubectl port-forward -n "$NS" svc/api-gateway 8080:80
```

После port-forward маршрут доступен по http://localhost:8080. Для итогового HTTPS подключите сертификат и TLS-настройки из ЛР № 2. Закрытый ключ в шаблон не включен.

## 9. Эксперименты

Deadline:

```
kubectl set env -n "$NS" deployment/domain-grpc TEST_DELAY_MS=1000
kubectl rollout status -n "$NS" deployment/domain-grpc
curl -i http://localhost:8080/api/v1/entities/demo-1
kubectl set env -n "$NS" deployment/domain-grpc TEST_DELAY_MS=0
```

Временная недоступность:

```
kubectl scale -n "$NS" deployment/domain-grpc --replicas=0
curl -i http://localhost:8080/api/v1/entities/demo-1
kubectl scale -n "$NS" deployment/domain-grpc --replicas=2
```

Rate limiting:

```
seq 1 20 | xargs -P10 -I{} \
  curl -s -o /dev/null -w '%{http_code}\n' \
  http://localhost:8080/api/v1/entities/demo-1 | sort | uniq -c
```

## Важно!

- TLS-ключи, kubeconfig, registry credentials и Kubernetes Secret не включены.
- PostgreSQL-схема не дублируется; используется база из предыдущих работ.
- Streaming, Istio, mTLS и OpenTelemetry оставлены за рамками основной части.

