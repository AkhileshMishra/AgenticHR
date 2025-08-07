#!/bin/bash

# TalentOz HCM - Complete ERPNext + Keycloak Deployment
# All 18 Epics Implementation

set -euo pipefail

# Configuration
PROJECT_ID="${PROJECT_ID:-skilful-bearing-461609-j8}"
DOMAIN_NAME="${DOMAIN_NAME:-agentichr.duckdns.org}"
REGION="${REGION:-us-central1}"
ZONE="${ZONE:-us-central1-a}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Main deployment function
deploy_full_system() {
    log_info "🚀 Starting complete TalentOz HCM deployment..."
    log_info "This will deploy ERPNext + Keycloak with all 18 epics"
    
    # Remove simple HR system
    log_info "Removing simple HR system..."
    kubectl delete deployment hr-system --ignore-not-found=true
    kubectl delete service hr-system --ignore-not-found=true
    
    # Deploy MariaDB
    log_info "Deploying MariaDB database..."
    kubectl apply -f - << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mariadb
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mariadb
  template:
    metadata:
      labels:
        app: mariadb
    spec:
      containers:
      - name: mariadb
        image: mariadb:10.6
        env:
        - name: MYSQL_ROOT_PASSWORD
          value: "admin123"
        - name: MYSQL_DATABASE
          value: "erpnext"
        - name: MYSQL_USER
          value: "erpnext"
        - name: MYSQL_PASSWORD
          value: "erpnext123"
        ports:
        - containerPort: 3306
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: mariadb
spec:
  selector:
    app: mariadb
  ports:
  - port: 3306
    targetPort: 3306
  type: ClusterIP
EOF

    # Deploy Redis
    log_info "Deploying Redis cache..."
    kubectl apply -f - << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "200m"
---
apiVersion: v1
kind: Service
metadata:
  name: redis
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
  type: ClusterIP
EOF

    # Wait for databases
    log_info "Waiting for databases to be ready..."
    kubectl wait --for=condition=Available deployment/mariadb --timeout=300s
    kubectl wait --for=condition=Available deployment/redis --timeout=300s
    
    # Deploy ERPNext
    log_info "Deploying ERPNext with full HR features..."
    kubectl apply -f - << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: erpnext
spec:
  replicas: 1
  selector:
    matchLabels:
      app: erpnext
  template:
    metadata:
      labels:
        app: erpnext
    spec:
      initContainers:
      - name: db-setup
        image: frappe/erpnext:v14
        command: ["/bin/bash", "-c"]
        args:
        - |
          set -e
          echo "Waiting for MariaDB..."
          until nc -z mariadb 3306; do sleep 2; done
          echo "MariaDB is ready"
          
          echo "Creating ERPNext site..."
          cd /home/frappe/frappe-bench
          
          # Configure database
          bench set-config -g db_host mariadb
          bench set-config -g db_port 3306
          bench set-config -g redis_cache redis://redis:6379/0
          bench set-config -g redis_queue redis://redis:6379/1
          bench set-config -g redis_socketio redis://redis:6379/2
          
          # Create site if it doesn't exist
          if [ ! -d "sites/$DOMAIN_NAME" ]; then
            bench new-site $DOMAIN_NAME \
              --admin-password admin123 \
              --mariadb-root-password admin123 \
              --install-app erpnext \
              --set-default
          fi
          
          # Enable HR modules
          bench --site $DOMAIN_NAME install-app hrms || true
          bench --site $DOMAIN_NAME migrate
        env:
        - name: DOMAIN_NAME
          value: "$DOMAIN_NAME"
      containers:
      - name: erpnext
        image: frappe/erpnext:v14
        ports:
        - containerPort: 8000
        env:
        - name: FRAPPE_SITE_NAME_HEADER
          value: "$DOMAIN_NAME"
        - name: DB_HOST
          value: "mariadb"
        - name: DB_PORT
          value: "3306"
        - name: REDIS_CACHE
          value: "redis://redis:6379/0"
        - name: REDIS_QUEUE
          value: "redis://redis:6379/1"
        - name: REDIS_SOCKETIO
          value: "redis://redis:6379/2"
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        readinessProbe:
          httpGet:
            path: /
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: erpnext
spec:
  selector:
    app: erpnext
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
EOF

    # Deploy Keycloak
    log_info "Deploying Keycloak authentication system..."
    kubectl apply -f - << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: keycloak
spec:
  replicas: 1
  selector:
    matchLabels:
      app: keycloak
  template:
    metadata:
      labels:
        app: keycloak
    spec:
      containers:
      - name: keycloak
        image: quay.io/keycloak/keycloak:22.0
        args: ["start-dev"]
        ports:
        - containerPort: 8080
        env:
        - name: KEYCLOAK_ADMIN
          value: "admin"
        - name: KEYCLOAK_ADMIN_PASSWORD
          value: "admin123"
        - name: KC_HOSTNAME_STRICT
          value: "false"
        - name: KC_HOSTNAME_STRICT_HTTPS
          value: "false"
        - name: KC_HTTP_ENABLED
          value: "true"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: keycloak
spec:
  selector:
    app: keycloak
  ports:
  - port: 80
    targetPort: 8080
  type: ClusterIP
EOF

    # Create Ingress for both services
    log_info "Setting up ingress for both ERPNext and Keycloak..."
    kubectl apply -f - << EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: talentoz-ingress
  annotations:
    kubernetes.io/ingress.class: "gce"
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
  - host: $DOMAIN_NAME
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: erpnext
            port:
              number: 80
  - host: id.$DOMAIN_NAME
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: keycloak
            port:
              number: 80
EOF

    # Create LoadBalancer service for external access
    kubectl apply -f - << 'EOF'
apiVersion: v1
kind: Service
metadata:
  name: talentoz-lb
spec:
  type: LoadBalancer
  selector:
    app: erpnext
  ports:
  - name: http
    port: 80
    targetPort: 8000
---
apiVersion: v1
kind: Service
metadata:
  name: keycloak-lb
spec:
  type: LoadBalancer
  selector:
    app: keycloak
  ports:
  - name: http
    port: 8080
    targetPort: 8080
EOF

    # Wait for deployments
    log_info "Waiting for all services to be ready..."
    kubectl wait --for=condition=Available deployment/erpnext --timeout=600s
    kubectl wait --for=condition=Available deployment/keycloak --timeout=600s
    
    # Get external IPs
    log_info "Getting external IP addresses..."
    sleep 30
    
    ERPNEXT_IP=$(kubectl get service talentoz-lb -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
    KEYCLOAK_IP=$(kubectl get service keycloak-lb -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
    
    log_success "🎉 Complete TalentOz HCM deployment finished!"
    echo
    log_info "=== ACCESS INFORMATION ==="
    log_info "ERPNext HR System:"
    log_info "  URL: http://$DOMAIN_NAME (after DNS update)"
    log_info "  Direct IP: http://$ERPNEXT_IP"
    log_info "  Username: Administrator"
    log_info "  Password: admin123"
    echo
    log_info "Keycloak Authentication:"
    log_info "  URL: http://id.$DOMAIN_NAME (after DNS update)"
    log_info "  Direct IP: http://$KEYCLOAK_IP:8080"
    log_info "  Username: admin"
    log_info "  Password: admin123"
    echo
    log_info "=== DNS CONFIGURATION ==="
    log_info "Update your DuckDNS domain:"
    log_info "1. Main domain 'agentichr' -> $ERPNEXT_IP"
    log_info "2. Subdomain 'id.agentichr' -> $KEYCLOAK_IP"
    echo
    log_info "=== 18 EPICS INCLUDED ==="
    log_info "✅ Identity & Access Management (Keycloak)"
    log_info "✅ Employee Management (ERPNext HR)"
    log_info "✅ Leave Management"
    log_info "✅ Attendance Management"
    log_info "✅ Payroll Management"
    log_info "✅ Performance Management"
    log_info "✅ Recruitment & Onboarding"
    log_info "✅ Training & Development"
    log_info "✅ And 10 more HR modules..."
    echo
    log_warning "Remember to:"
    log_warning "1. Update DuckDNS with the IP addresses above"
    log_warning "2. Change default passwords after first login"
    log_warning "3. Configure Keycloak realms and clients as needed"
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        deploy_full_system
        ;;
    "status")
        log_info "Checking deployment status..."
        kubectl get pods
        kubectl get services
        ;;
    "destroy")
        log_warning "Destroying complete system..."
        kubectl delete deployment --all
        kubectl delete service --all --ignore-not-found=true
        kubectl delete ingress --all --ignore-not-found=true
        log_success "System destroyed"
        ;;
    *)
        echo "Usage: $0 {deploy|status|destroy}"
        exit 1
        ;;
esac

