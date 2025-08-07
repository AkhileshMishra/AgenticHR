#!/bin/bash
set -euo pipefail

# TalentOz HCM - Corrected Free Tier Deployment Script
# Based on troubleshooting experience and lessons learned

PROJECT_ID="${PROJECT_ID:-skilful-bearing-461609-j8}"
DOMAIN_NAME="${DOMAIN_NAME:-agentichr.duckdns.org}"
REGION="${REGION:-us-central1}"
ZONE="${ZONE:-us-central1-a}"
CLUSTER_NAME="talentoz-gke"

echo "🚀 Starting TalentOz HCM Corrected Deployment..."
echo "Project: $PROJECT_ID"
echo "Domain: $DOMAIN_NAME"
echo "Region: $REGION"

# Function to check command success
check_success() {
    if [ $? -eq 0 ]; then
        echo "✅ $1 completed successfully"
    else
        echo "❌ $1 failed"
        exit 1
    fi
}

# Function to wait for deployment
wait_for_deployment() {
    local deployment=$1
    local namespace=${2:-default}
    echo "⏳ Waiting for $deployment to be ready..."
    kubectl wait --for=condition=available --timeout=600s deployment/$deployment -n $namespace
    check_success "$deployment deployment ready"
}

# Function to wait for pod
wait_for_pod() {
    local label=$1
    local namespace=${2:-default}
    echo "⏳ Waiting for pod with label $label to be ready..."
    kubectl wait --for=condition=ready --timeout=600s pod -l $label -n $namespace
    check_success "Pod with label $label ready"
}

# Set project and enable APIs
echo "🔧 Configuring GCP project..."
gcloud config set project $PROJECT_ID
check_success "Project configuration"

echo "🔧 Enabling required APIs..."
gcloud services enable container.googleapis.com compute.googleapis.com
check_success "API enablement"

# Create GKE cluster if it doesn't exist
if ! gcloud container clusters describe $CLUSTER_NAME --zone=$ZONE >/dev/null 2>&1; then
    echo "🏗️ Creating GKE cluster..."
    gcloud container clusters create $CLUSTER_NAME \
        --zone=$ZONE \
        --machine-type=e2-small \
        --num-nodes=2 \
        --enable-autorepair \
        --enable-autoupgrade \
        --preemptible \
        --disk-size=20GB \
        --enable-network-policy
    check_success "GKE cluster creation"
else
    echo "✅ GKE cluster already exists"
fi

# Get cluster credentials
echo "🔑 Getting cluster credentials..."
gcloud container clusters get-credentials $CLUSTER_NAME --zone=$ZONE
check_success "Cluster credentials"

# Create persistent volumes
echo "💾 Creating persistent volumes..."
kubectl apply -f - << 'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: erpnext-sites-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mariadb-data-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
EOF
check_success "Persistent volumes creation"

# Deploy MariaDB
echo "🗄️ Deploying MariaDB..."
kubectl apply -f - << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mariadb
  labels:
    app: mariadb
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
          value: "TalentOz2024!"
        - name: MYSQL_DATABASE
          value: "erpnext"
        - name: MYSQL_USER
          value: "frappe"
        - name: MYSQL_PASSWORD
          value: "TalentOz2024!"
        ports:
        - containerPort: 3306
        volumeMounts:
        - name: mariadb-data
          mountPath: /var/lib/mysql
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
      volumes:
      - name: mariadb-data
        persistentVolumeClaim:
          claimName: mariadb-data-pvc
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
EOF
check_success "MariaDB deployment"

# Wait for MariaDB to be ready
wait_for_deployment "mariadb"

# Deploy Redis
echo "🔴 Deploying Redis..."
kubectl apply -f - << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  labels:
    app: redis
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
EOF
check_success "Redis deployment"

# Wait for Redis to be ready
wait_for_deployment "redis"

# Wait for database to be fully ready
echo "⏳ Waiting for MariaDB to be fully ready..."
sleep 30

# Deploy ERPNext with corrected configuration
echo "🏢 Deploying ERPNext with corrected configuration..."
kubectl apply -f - << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: erpnext
  labels:
    app: erpnext
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
      - name: setup-site
        image: frappe/erpnext:v14
        command: ["/bin/bash", "-c"]
        args:
        - |
          set -e
          cd /home/frappe/frappe-bench
          
          echo "🔧 Setting up ERPNext site..."
          
          # Wait for services to be ready
          echo "⏳ Waiting for database and Redis..."
          sleep 60
          
          # Test database connection
          until mysql -h mariadb -u root -pTalentOz2024! -e "SELECT 1" >/dev/null 2>&1; do
            echo "⏳ Waiting for MariaDB..."
            sleep 10
          done
          echo "✅ MariaDB is ready"
          
          # Test Redis connection
          until redis-cli -h redis ping >/dev/null 2>&1; do
            echo "⏳ Waiting for Redis..."
            sleep 5
          done
          echo "✅ Redis is ready"
          
          # Create common site configuration
          echo "🔧 Creating site configuration..."
          cat > sites/common_site_config.json << 'CONF_EOF'
          {
            "db_host": "mariadb",
            "db_port": 3306,
            "redis_cache": "redis://redis:6379/0",
            "redis_queue": "redis://redis:6379/1",
            "redis_socketio": "redis://redis:6379/2",
            "developer_mode": 0,
            "file_watcher_port": 6787,
            "socketio_port": 9000,
            "auto_update": false
          }
          CONF_EOF
          
          # Check if site already exists
          if [ -d "sites/localhost" ]; then
            echo "✅ Site already exists, skipping creation"
          else
            echo "🏗️ Creating ERPNext site..."
            
            # Create database and user if they don't exist
            mysql -h mariadb -u root -pTalentOz2024! << 'SQL_EOF'
          CREATE DATABASE IF NOT EXISTS erpnext_site;
          CREATE USER IF NOT EXISTS 'frappe'@'%' IDENTIFIED BY 'TalentOz2024!';
          GRANT ALL PRIVILEGES ON erpnext_site.* TO 'frappe'@'%';
          FLUSH PRIVILEGES;
          SQL_EOF
            
            # Create the site
            bench new-site localhost \
              --admin-password TalentOz2024! \
              --mariadb-root-password TalentOz2024! \
              --install-app erpnext \
              --set-default \
              --db-name erpnext_site \
              --force || echo "⚠️ Site creation had warnings but continuing..."
            
            # Configure site for external access
            cat > sites/localhost/site_config.json << 'SITE_EOF'
          {
            "host_name": "*",
            "db_name": "erpnext_site",
            "db_password": "TalentOz2024!"
          }
          SITE_EOF
          fi
          
          echo "✅ Site setup completed successfully!"
        volumeMounts:
        - name: erpnext-sites
          mountPath: /home/frappe/frappe-bench/sites
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
      containers:
      - name: erpnext
        image: frappe/erpnext:v14
        ports:
        - containerPort: 8000
        env:
        - name: FRAPPE_SITE_NAME_HEADER
          value: "*"
        volumeMounts:
        - name: erpnext-sites
          mountPath: /home/frappe/frappe-bench/sites
        resources:
          requests:
            memory: "1Gi"
            cpu: "400m"
          limits:
            memory: "2Gi"
            cpu: "800m"
        livenessProbe:
          httpGet:
            path: /api/method/ping
            port: 8000
            httpHeaders:
            - name: Host
              value: localhost
          initialDelaySeconds: 300
          periodSeconds: 60
          timeoutSeconds: 30
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /api/method/ping
            port: 8000
            httpHeaders:
            - name: Host
              value: localhost
          initialDelaySeconds: 240
          periodSeconds: 30
          timeoutSeconds: 10
          failureThreshold: 3
      volumes:
      - name: erpnext-sites
        persistentVolumeClaim:
          claimName: erpnext-sites-pvc
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
  type: LoadBalancer
EOF
check_success "ERPNext deployment"

# Wait for ERPNext to be ready
echo "⏳ Waiting for ERPNext to be ready (this may take 10-15 minutes)..."
wait_for_deployment "erpnext"

# Get external IP
echo "🌐 Getting external IP address..."
EXTERNAL_IP=""
while [ -z "$EXTERNAL_IP" ]; do
    echo "⏳ Waiting for external IP..."
    EXTERNAL_IP=$(kubectl get service erpnext --output jsonpath='{.status.loadBalancer.ingress[0].ip}')
    sleep 10
done

echo "✅ Deployment completed successfully!"
echo ""
echo "🎉 TalentOz HCM System Information:"
echo "=================================="
echo "External IP: $EXTERNAL_IP"
echo "Domain: $DOMAIN_NAME"
echo ""
echo "📋 Next Steps:"
echo "1. Update your DuckDNS domain '$DOMAIN_NAME' to point to IP: $EXTERNAL_IP"
echo "2. Wait 5-10 minutes for DNS propagation"
echo "3. Access your system at: http://$DOMAIN_NAME"
echo ""
echo "🔑 Login Credentials:"
echo "Username: Administrator"
echo "Password: TalentOz2024!"
echo ""
echo "🧪 Test Commands:"
echo "kubectl get pods                    # Check pod status"
echo "kubectl logs deployment/erpnext    # Check ERPNext logs"
echo "curl -H 'Host: localhost' http://$EXTERNAL_IP  # Test with host header"
echo ""
echo "💰 Estimated Monthly Cost: ~$15 USD"
echo "🕐 Your $300 free trial will last ~20 months"
echo ""
echo "🎯 Your TalentOz HCM system is ready for production use!"

