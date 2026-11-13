# Базовый шаблон для лабораторной работы № 6

Шаблон добавляет наблюдаемость в сквозной проект из предыдущих работ. В кластере k3s развертываются:

- Prometheus Operator, Prometheus, Alertmanager, Grafana, kube-state-metrics и node-exporter из `kube-prometheus-stack`;
- Loki в монолитном режиме для одноузлового учебного кластера;
- Grafana Alloy для сбора логов Pod через Kubernetes API;
- ServiceMonitor, PrometheusRule и дашборд предметного сервиса.

Шаблон не содержит паролей, токенов и kubeconfig. Версии Helm chart нужно зафиксировать перед занятием после проверки в учебной среде.

## Структура

```text
helm/
  kube-prometheus-stack-values.yaml
  loki-values.yaml
  alloy-values.yaml
app/
  observability.py
  requirements-monitoring.txt
k8s/
  service-monitor.yaml
  prometheus-rule.yaml
  dashboard-configmap.yaml
scripts/
  check-stack.sh
  generate-load.sh
```

## 1. Предварительная проверка

```bash
kubectl cluster-info
kubectl get nodes -o wide
kubectl get storageclass
kubectl get pods -A
kubectl top nodes || true
```

Для учебного стека нужны Helm 3.22+ или Helm 4.x, доступ к registry образов и не менее 4 ГБ свободной оперативной памяти на одноузловом кластере. Если нода испытывает давление по памяти, сначала уменьшите retention и лимиты, а не отключайте probes.

## 2. Репозитории Helm

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana-community https://grafana-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

helm search repo prometheus-community/kube-prometheus-stack --versions | head
helm search repo grafana-community/loki --versions | head
helm search repo grafana/alloy --versions | head
```

После тестовой установки добавьте к каждой команде `helm upgrade --install` параметр `--version <проверенная-версия>`. В отчете укажите фактические версии.

## 3. Установка Prometheus и Grafana

```bash
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -

helm upgrade --install monitoring \
  prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --values helm/kube-prometheus-stack-values.yaml \
  --wait --timeout 10m
```

## 4. Установка Loki и Alloy

```bash
helm upgrade --install loki \
  grafana-community/loki \
  --namespace monitoring \
  --values helm/loki-values.yaml \
  --wait --timeout 10m

helm upgrade --install alloy \
  grafana/alloy \
  --namespace monitoring \
  --values helm/alloy-values.yaml \
  --wait --timeout 10m
```

```bash
./scripts/check-stack.sh
```

## 5. Доступ к Grafana

```bash
kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80
```

Логин: `admin`. Пароль извлекается из Secret, который создал chart:

```bash
kubectl get secret -n monitoring monitoring-grafana \
  -o jsonpath='{.data.admin-password}' | base64 --decode
printf '\n'
```

Не помещайте пароль в Git, отчет или снимок экрана.

## 6. Инструментирование FastAPI

1. Добавьте `prometheus-client` из `app/requirements-monitoring.txt` в зависимости backend.
2. Скопируйте `app/observability.py` в свой сервис.
3. Вызовите `configure_observability(app, service_name="<имя-сервиса>")` после создания FastAPI.
4. Пересоберите образ и обновите Deployment.

В Deployment добавьте метку и аннотацию Pod:

```yaml
template:
  metadata:
    labels:
      app.kubernetes.io/name: catalog-service
    annotations:
      observability.example/enabled: "true"
```

В Service порт HTTP должен иметь имя `http`, поскольку ServiceMonitor ссылается на порт по имени.

## 7. Подключение метрик, алерта и дашборда

Замените в файлах `k8s/service-monitor.yaml` и `k8s/prometheus-rule.yaml`:

- `STUDENT_NAMESPACE` на namespace своего проекта;
- `APP_SERVICE_NAME` на имя Kubernetes Service;
- `APP_LABEL_VALUE` на значение метки `app.kubernetes.io/name`;
- `ERROR_RATIO_THRESHOLD` на долю, например `0.05` для 5%;
- `LATENCY_THRESHOLD_SECONDS` на порог p95 из своего варианта.

```bash
kubectl apply -f k8s/service-monitor.yaml
kubectl apply -f k8s/prometheus-rule.yaml
kubectl apply -f k8s/dashboard-configmap.yaml
```

## 8. Проверка и нагрузка

```bash
kubectl get servicemonitor,prometheusrule -A
kubectl get --raw /apis/monitoring.coreos.com/v1 | head

BASE_URL=https://<адрес-сервиса> \
REQUEST_PATH=/api/v1/entities/demo-1 \
./scripts/generate-load.sh
```

В Grafana откройте:

- **Explore > Prometheus** и выполните `sum(rate(http_requests_total[5m]))`;
- **Explore > Loki** и выполните `{namespace="<namespace>", service="<service>"} | json`;
- **Dashboards > Microservice Observability** и выерите namespace и service.

## 9. Границы кардинальности

В метках Prometheus и Loki нельзя использовать `request_id`, полный URL, имя пользователя или другие почти уникальные значения. `request_id` остается полем JSON-лога, по которому можно выполнить точечный поиск:

```logql
{namespace="<namespace>", service="<service>"}
  | json
  | request_id="lab6-test-01"
```

## 10. Очистка

Объекты приложения можно удалить отдельно:

```bash
kubectl delete -f k8s/prometheus-rule.yaml --ignore-not-found
kubectl delete -f k8s/service-monitor.yaml --ignore-not-found
kubectl delete -f k8s/dashboard-configmap.yaml --ignore-not-found
```

Полное удаление стека выполняйте только по указанию преподавателя:

```bash
helm uninstall alloy -n monitoring
helm uninstall loki -n monitoring
helm uninstall monitoring -n monitoring
```

Удалениие PVC приводит к потере собранных метрик, логов и дашбордов. В шаблон не включена команда удаления PVC.

