#!/usr/bin/env sh
set -eu

NAMESPACE=${MONITORING_NAMESPACE:-monitoring}

kubectl get pods -n "$NAMESPACE" -o wide
kubectl get svc -n "$NAMESPACE"
kubectl get pvc -n "$NAMESPACE"
kubectl get servicemonitor,prometheusrule -A

echo "Проверка завершена. Убедитесь, что основные Pod имеют состояние Running и Ready."

