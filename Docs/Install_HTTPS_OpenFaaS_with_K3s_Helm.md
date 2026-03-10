## Hướng dẫn triển khai OpenFaaS & Monitoring với HTTPS trên K3s

Tài liệu này hướng dẫn cách thiết lập cụm K3s, cài đặt OpenFaaS cho Serverless, Prometheus/Grafana cho Monitoring và sử dụng Tailscale Operator để expose dịch vụ an toàn mà không cần mở Port/Ingress hay setup HTTPS phức tạp.

### 1. Cài đặt môi trường cơ sở

Cài đặt K3s

```bash
curl -sfL https://get.k3s.io | sh -
# Kiểm tra trạng thái
sudo systemctl status k3s
```

Cài đặt Helm (Package Manager)

```bash
curl -sSL https://get.helm.sh/helm-v3.12.0-linux-amd64.tar.gz | tar xz
sudo mv linux-amd64/helm /usr/local/bin/helm
# Kiểm tra phiên bản
helm version
```

### 2. Chuẩn bị Cluster

Thiết lập biến môi trường để kubectl nhận diện cụm và tạo các Namespace riêng biệt để quản lý

```bash
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

kubectl create namespace openfaas
kubectl create namespace monitoring
kubectl create namespace tailscale
```

### 3. Thêm Helm Repositories

Đăng ký các nguồn chứa Charts cho các dịch vụ

```bash
helm repo add openfaas https://openfaas.github.io/faas-netes/
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add tailscale https://pkgs.tailscale.com/helmcharts

helm repo update
```

### 4. Triển khai các thành phần chính

```bash
# Triển khai OpenFaaS (Serverless)
helm install openfaas openfaas/openfaas \
  --namespace openfaas \
  --set gateway.replicas=1 \
  --set faasnetes.imagePullPolicy=IfNotPresent

# Cài đặt Grafana với mật khẩu admin mặc định
helm install grafana grafana/grafana \
 --namespace monitoring \
 --set adminPassword=admin

# Cài đặt Prometheus
helm install prometheus prometheus-community/prometheus \
 --namespace monitoring
```

Thêm các dòng này vào _~/.bashrc_

```bash
# Serverless Controller
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
alias faas-up='sudo systemctl start k3s && echo "OpenFaaS cluster have started"'
alias faas-down='sudo systemctl stop k3s && echo "K3s Serverless cluster stopped!"'
alias faas-status='kubectl get pods -n openfaas && kubectl get pods -n monitoring'
```

### 5. Cấu hình Tailscale Operator (MagicDNS)

Đây là bước quan trọng để biến các Service thành "máy ảo" trên mạng Tailscale cá nhân

- Vào **Tailscale Admin Console**, **Access Control > JSON Editor**

```json
// Thêm 2 dòng này vào cuối object tagOwners
"tagOwners": {
  "tag:k8s-operator": [],
  "tag:k8s": ["tag:k8s-operator"],
}

```

- Tiếp tục vào **Settings > Trust Credentials > + Credential**, tạo 1 **OAuth** Client với Devices Core, Auth Keys, Services là **write** scopes, và **tag:k8s-operator**. Lưu lại ClientID và Client Secret ở nơi an toàn.

- Thay Tailscale-clientID và Tailscale-clientSecret bằng thông tin lưu lại ở trên

```bash
helm upgrade --install tailscale-operator tailscale/tailscale-operator \
 --namespace=tailscale \
 --set-string oauth.clientId="YOUR_CLIENT_ID" \
 --set-string oauth.clientSecret="YOUR_CLIENT_SECRET" \
 --wait
```

- Tạo file tailscale-ingress.yaml để Tailscale Operator tạo ra 1 Ingress Controller xử lý TLS/HTTPS cho các traffic vào ứng dụng:

```yaml
# tailscale-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: grafana-ingress
  namespace: monitoring
spec:
  ingressClassName: tailscale
  rules:
    - http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: grafana
                port:
                  number: 80
  tls:
    - hosts:
        # Tên này sẽ biến thành faaschart.[tailnet-của-bạn].ts.net
        - faaschart
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: gateway-ingress
  namespace: openfaas
spec:
  ingressClassName: tailscale
  rules:
    - http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: gateway
                port:
                  number: 9999
  tls:
    - hosts:
        - faasportal
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: prometheus-ingress
  namespace: monitoring
spec:
  ingressClassName: tailscale
  rules:
    - http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                # Nhớ kỹ tên service này là prometheus-server nhé
                name: prometheus-server
                port:
                  number: 80
  tls:
    - hosts:
        # Tên này sẽ biến thành faasmetrics.[tailnet-của-bạn].ts.net
        - faasmetrics
```

- Áp dụng cấu hình: Tạo 1 file update-cluster.sh

```bash
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
```

```bash
chmod +x update-cluster.sh
```

- Sau này, mỗi khi thay đổi gì (thêm HTTPS, đổi hostname, tăng replica), ta chỉ cần sửa file .yaml tương ứng rồi gõ ./update-cluster.sh là xong.

```
~/cluster_setup/
├── tailscale-ingress.yaml
└── update-cluster.sh
```

### 6. Kết nối Prometheus với Grafana

- Truy cập vào: [Grafana URL](https://faaschart.[tailnet-của-bạn].ts.net)

- Đăng nhập vào Grafana với account admin/admin. Đổi mật khẩu nếu Grafana yêu cầu.

- Thêm **Prometheus** làm Data Source: Connection > Add new connection > Prometheus

- Trong ô **URL**, dán: http://prometheus-server.monitoring.svc.cluster.local:80.

- Ấn **Test & Save**. Nếu bạn thấy một thông báo màu xanh lá cây báo hiệu "Data source is working" thì chúc mừng, Prometheus và Grafana đã thông nhau!

- Ấn dấu cộng (bên phải) -> Import -> Trong ô _Import via grafana.com_, nhập số ID: 15661 (Đây là cái dashboard "K8s Cluster Summary" cực kỳ nổi tiếng) > Load

- Data Source > chọn Prometheus.

Bạn sẽ thấy một bảng điều khiển hiện ra với đủ các chỉ số CPU, RAM, và số lượng Pod đang chạy trên máy!
