#!/bin/bash

echo "Bắt đầu quá trình nâng cấp cho Cluster..."

# Nâng cấp OpenFaaS
echo "--- Đang nâng cấp OpenFaaS ---"
helm upgrade openfaas openfaas/openfaas --namespace openfaas --reuse-values

# Nâng cấp Grafana
echo "--- Đang nâng cấp Grafana ---"
helm upgrade grafana grafana/grafana --namespace monitoring --reuse-values

# Nâng cấp Prometheus
echo "--- Đang nâng cấp Prometheus ---"
helm upgrade prometheus prometheus-community/prometheus --namespace monitoring --reuse-values

# Triển khai Ingress
echo "--- Đang cấu hình HTTPS qua Tailscale Ingress ---"
kubectl apply -f tailscale-ingress.yaml

echo "Hoàn tất! Cluster đã sẵn sàng."