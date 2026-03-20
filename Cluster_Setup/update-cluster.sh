#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENFAAS_USER="${OPENFAAS_USER:-admin}"
OPENFAAS_PASSWORD="${OPENFAAS_PASSWORD:-admindz}"
OPENFAAS_GATEWAY_URL="${OPENFAAS_GATEWAY_URL:-https://faasportal.tailf1e57.ts.net}"

# Parse cờ --debug từ command line
DEBUG=0
for arg in "$@"; do
    if [[ "$arg" == "--debug" ]]; then
        DEBUG=1
        break
    fi
done

# Hàm execute để ẩn output nếu không bật debug
execute() {
    if [[ "$DEBUG" == "1" ]]; then
        "$@"
    else
        "$@" >/dev/null 2>&1
    fi
}

echo "Bắt đầu quá trình nâng cấp cho Cluster..."

echo "--- Đang đồng bộ Helm repositories ---"
execute helm repo add openfaas https://openfaas.github.io/faas-netes/ --force-update
execute helm repo add grafana https://grafana.github.io/helm-charts --force-update
execute helm repo add prometheus-community https://prometheus-community.github.io/helm-charts --force-update
execute helm repo update
echo "[OK] Helm repositories da duoc dong bo."

# Nâng cấp OpenFaaS
echo "--- Đang nâng cấp OpenFaaS ---"
kubectl -n openfaas create secret generic basic-auth \
	--from-literal=basic-auth-user="$OPENFAAS_USER" \
	--from-literal=basic-auth-password="$OPENFAAS_PASSWORD" \
	--dry-run=client -o yaml | execute kubectl apply -f -
execute helm upgrade --install openfaas openfaas/openfaas --namespace openfaas --reuse-values --hide-notes \
	--set basic_auth=true \
	--set generateBasicAuth=false \
	--set-string basic_auth_user="$OPENFAAS_USER" \
	--set-string basic_auth_password="$OPENFAAS_PASSWORD"
echo "[OK] OpenFaaS da duoc nang cap."

# Nâng cấp Grafana
echo "--- Đang nâng cấp Grafana ---"
execute helm upgrade --install grafana grafana/grafana --namespace monitoring --reuse-values --hide-notes -f "$SCRIPT_DIR/grafana-values.yaml"
echo "[OK] Grafana da duoc nang cap."

# Nâng cấp Prometheus
echo "--- Đang nâng cấp Prometheus ---"
execute helm upgrade --install prometheus prometheus-community/prometheus --namespace monitoring --reuse-values --hide-notes -f "$SCRIPT_DIR/prometheus-values.yaml"
echo "[OK] Prometheus da duoc nang cap."

# Triển khai Ingress
echo "--- Đang cấu hình HTTPS qua Tailscale Ingress ---"
execute kubectl apply -f "$SCRIPT_DIR/tailscale-ingress.yaml"
echo "[OK] Tailscale ingress da duoc ap dung."

# Đợi một chút để các deployment khởi động lại
echo "--- Đang khởi động lại OpenFaaS Gateway ---"
execute kubectl -n openfaas rollout restart deployment gateway
execute kubectl -n openfaas rollout status deployment gateway
echo "[OK] Gateway da restart xong."

# Verify OpenFaaS auth
echo "--- Đang verify OpenFaaS auth ---"
CURRENT_USER="$(kubectl -n openfaas get secret basic-auth -o jsonpath='{.data.basic-auth-user}' | base64 --decode)"
CURRENT_PASSWORD="$(kubectl -n openfaas get secret basic-auth -o jsonpath='{.data.basic-auth-password}' | base64 --decode)"

if [[ "$CURRENT_USER" == "$OPENFAAS_USER" && "$CURRENT_PASSWORD" == "$OPENFAAS_PASSWORD" ]]; then
	echo "[PASS] Secret basic-auth da duoc cap nhat dung user/password."
else
	echo "[FAIL] Secret basic-auth KHONG khop voi OPENFAAS_USER/OPENFAAS_PASSWORD."
	echo "       Kiem tra lai bien moi truong hoac quyen truy cap namespace openfaas."
	exit 1
fi

if command -v curl >/dev/null 2>&1; then
	HTTP_CODE="$(curl -ksS -o /dev/null -w '%{http_code}' -u "$OPENFAAS_USER:$OPENFAAS_PASSWORD" "$OPENFAAS_GATEWAY_URL/system/functions" || true)"
	if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "202" ]]; then
		echo "[PASS] Gateway auth thanh cong: $OPENFAAS_GATEWAY_URL"
	else
		echo "[FAIL] Gateway auth that bai (HTTP $HTTP_CODE): $OPENFAAS_GATEWAY_URL"
		exit 1
	fi
else
	echo "[WARN] Khong tim thay curl, bo qua buoc verify gateway auth."
fi

echo "Hoàn tất! Cluster đã sẵn sàng."