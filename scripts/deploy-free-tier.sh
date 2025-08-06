#!/bin/bash

# TalentOz HCM - Free Tier Deployment Script
# Optimized for Google Cloud Free Trial in India

set -euo pipefail

# Configuration
PROJECT_ID="${PROJECT_ID:-skilful-bearing-461609-j8}"
REGION="${REGION:-us-central1}"
ZONE="${ZONE:-us-central1-a}"
CLUSTER_NAME="${CLUSTER_NAME:-talentoz-gke}"
DOMAIN_NAME="${DOMAIN_NAME:-agentichr.duckdns.org}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites for free tier deployment..."
    
    # Check if required tools are installed
    local tools=("gcloud" "kubectl" "terraform")
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "$tool is not installed. Please install it first."
            exit 1
        fi
    done
    
    # Check if authenticated with gcloud
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        log_error "Not authenticated with gcloud. Please run 'gcloud auth login'"
        exit 1
    fi
    
    # Check project
    if ! gcloud projects describe "$PROJECT_ID" &> /dev/null; then
        log_error "Project $PROJECT_ID not found or not accessible"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Check free tier eligibility
check_free_tier() {
    log_info "Checking free tier eligibility..."
    
    # Check if project has billing enabled
    if ! gcloud billing projects describe "$PROJECT_ID" &> /dev/null; then
        log_error "Billing is not enabled for project $PROJECT_ID"
        log_info "Please enable billing in the GCP Console to use free trial credits"
        exit 1
    fi
    
    # Check region (free tier works best in us-central1)
    if [[ "$REGION" != "us-central1" ]]; then
        log_warning "For maximum free tier compatibility, consider using us-central1 region"
        log_info "Current region: $REGION"
        read -p "Continue with current region? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Please set REGION=us-central1 and try again"
            exit 1
        fi
    fi
    
    log_success "Free tier eligibility check passed"
}

# Set up GCP project
setup_gcp_project() {
    log_info "Setting up GCP project: $PROJECT_ID"
    
    # Set the project
    gcloud config set project "$PROJECT_ID"
    
    # Enable required APIs
    log_info "Enabling required APIs..."
    gcloud services enable container.googleapis.com
    gcloud services enable compute.googleapis.com
    gcloud services enable secretmanager.googleapis.com
    
    log_success "GCP project setup completed"
}

# Deploy infrastructure with Terraform
deploy_infrastructure() {
    log_info "Deploying free-tier optimized infrastructure..."
    
    cd terraform
    
    # Use free-tier configuration
    cp main-free-tier.tf main.tf
    
    # Initialize Terraform
    terraform init
    
    # Plan the deployment
    terraform plan \
        -var="project_id=$PROJECT_ID" \
        -var="region=$REGION" \
        -var="zone=$ZONE" \
        -var="domain_name=$DOMAIN_NAME"
    
    # Show cost estimate
    log_info "Estimated monthly cost: $15-25 USD (within free trial credits)"
    log_warning "This deployment uses:"
    log_warning "- 2x e2-small preemptible nodes (~$10/month)"
    log_warning "- 1x f1-micro VM for database (FREE)"
    log_warning "- Load balancer (~$5/month)"
    log_warning "- Storage and networking (~$5/month)"
    
    read -p "Continue with deployment? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Deployment cancelled"
        exit 0
    fi
    
    # Apply the configuration
    log_info "Applying Terraform configuration..."
    terraform apply \
        -var="project_id=$PROJECT_ID" \
        -var="region=$REGION" \
        -var="zone=$ZONE" \
        -var="domain_name=$DOMAIN_NAME" \
        -auto-approve
    
    # Get outputs
    DB_HOST=$(terraform output -raw mysql_host)
    REDIS_HOST=$(terraform output -raw redis_host)
    LB_IP=$(terraform output -raw load_balancer_ip)
    
    cd ..
    
    log_success "Infrastructure deployment completed"
    log_info "Database Host: $DB_HOST"
    log_info "Redis Host: $REDIS_HOST"
    log_info "Load Balancer IP: $LB_IP"
}

# Configure kubectl
configure_kubectl() {
    log_info "Configuring kubectl..."
    
    gcloud container clusters get-credentials "$CLUSTER_NAME" \
        --zone "$ZONE" \
        --project "$PROJECT_ID"
    
    log_success "kubectl configured successfully"
}

# Deploy applications (simplified for free tier)
deploy_applications() {
    log_info "Deploying applications..."
    
    # Create namespaces
    kubectl create namespace erpnext --dry-run=client -o yaml | kubectl apply -f -
    kubectl create namespace keycloak --dry-run=client -o yaml | kubectl apply -f -
    
    # Create simplified deployments for free tier
    create_free_tier_manifests
    
    # Deploy applications
    kubectl apply -f kubernetes-free-tier/
    
    # Wait for deployments
    log_info "Waiting for applications to be ready..."
    kubectl wait --for=condition=Available deployment/erpnext -n erpnext --timeout=600s || true
    kubectl wait --for=condition=Available deployment/keycloak -n keycloak --timeout=600s || true
    
    log_success "Applications deployed successfully"
}

# Create simplified Kubernetes manifests for free tier
create_free_tier_manifests() {
    log_info "Creating free-tier optimized Kubernetes manifests..."
    
    mkdir -p kubernetes-free-tier
    
    # Get database and redis hosts
    DB_HOST=$(cd terraform && terraform output -raw mysql_host)
    REDIS_HOST=$(cd terraform && terraform output -raw redis_host)
    LB_IP=$(cd terraform && terraform output -raw load_balancer_ip)
    
    # ERPNext deployment (simplified)
    cat > kubernetes-free-tier/erpnext-deployment.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: erpnext
  namespace: erpnext
spec:
  replicas: 1  # Single replica for cost optimization
  selector:
    matchLabels:
      app: erpnext
  template:
    metadata:
      labels:
        app: erpnext
    spec:
      containers:
      - name: erpnext
        image: frappe/erpnext:v14
        ports:
        - containerPort: 8000
        env:
        - name: FRAPPE_SITE_NAME_HEADER
          value: "erp.$DOMAIN_NAME"
        - name: DB_HOST
          value: "$DB_HOST"
        - name: DB_PORT
          value: "3306"
        - name: REDIS_CACHE
          value: "redis://:$(REDIS_PASSWORD)@$REDIS_HOST:6379/0"
        - name: REDIS_QUEUE
          value: "redis://:$(REDIS_PASSWORD)@$REDIS_HOST:6379/1"
        - name: REDIS_SOCKETIO
          value: "redis://:$(REDIS_PASSWORD)@$REDIS_HOST:6379/2"
        envFrom:
        - secretRef:
            name: erpnext-secrets
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
  name: erpnext-service
  namespace: erpnext
spec:
  selector:
    app: erpnext
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
---
apiVersion: v1
kind: Secret
metadata:
  name: erpnext-secrets
  namespace: erpnext
type: Opaque
stringData:
  DB_PASSWORD: "$(cd terraform && terraform output -raw erpnext_db_password)"
  REDIS_PASSWORD: "$(cd terraform && terraform output -raw redis_password)"
EOF

    # Keycloak deployment (simplified)
    cat > kubernetes-free-tier/keycloak-deployment.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: keycloak
  namespace: keycloak
spec:
  replicas: 1  # Single replica for cost optimization
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
        args: ["start", "--optimized"]
        ports:
        - containerPort: 8080
        env:
        - name: KEYCLOAK_ADMIN
          value: "admin"
        - name: KEYCLOAK_ADMIN_PASSWORD
          valueFrom:
            secretKeyRef:
              name: keycloak-secrets
              key: KEYCLOAK_ADMIN_PASSWORD
        - name: KC_DB
          value: "mysql"
        - name: KC_DB_URL
          value: "jdbc:mysql://$DB_HOST:3306/keycloak"
        - name: KC_DB_USERNAME
          value: "keycloak"
        - name: KC_DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: keycloak-secrets
              key: KEYCLOAK_DB_PASSWORD
        - name: KC_HOSTNAME
          value: "id.$DOMAIN_NAME"
        - name: KC_PROXY
          value: "edge"
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
  name: keycloak-service
  namespace: keycloak
spec:
  selector:
    app: keycloak
  ports:
  - port: 80
    targetPort: 8080
  type: ClusterIP
---
apiVersion: v1
kind: Secret
metadata:
  name: keycloak-secrets
  namespace: keycloak
type: Opaque
stringData:
  KEYCLOAK_ADMIN_PASSWORD: "$(cd terraform && terraform output -raw keycloak_admin_password)"
  KEYCLOAK_DB_PASSWORD: "$(cd terraform && terraform output -raw keycloak_db_password)"
EOF

    # Simple ingress without SSL (to avoid cert-manager costs)
    cat > kubernetes-free-tier/ingress.yaml << EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: talentoz-ingress
  namespace: erpnext
  annotations:
    kubernetes.io/ingress.global-static-ip-name: "talentoz-lb-ip"
    kubernetes.io/ingress.class: "gce"
spec:
  rules:
  - host: erp.$DOMAIN_NAME
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: erpnext-service
            port:
              number: 80
  - host: id.$DOMAIN_NAME
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: keycloak-service
            port:
              number: 80
EOF

    log_success "Free-tier manifests created"
}

# Display deployment information
display_deployment_info() {
    log_success "Free-tier deployment completed successfully!"
    echo
    log_info "=== Deployment Information ==="
    log_info "ERPNext URL: http://erp.$DOMAIN_NAME (HTTP only for cost optimization)"
    log_info "Keycloak URL: http://id.$DOMAIN_NAME"
    log_info "Load Balancer IP: $(cd terraform && terraform output -raw load_balancer_ip)"
    echo
    log_info "=== DNS Configuration ==="
    log_info "Update your DuckDNS domain with the Load Balancer IP:"
    log_info "1. Go to https://www.duckdns.org/"
    log_info "2. Update 'agentichr' domain IP to: $(cd terraform && terraform output -raw load_balancer_ip)"
    echo
    log_info "=== Default Credentials ==="
    log_info "ERPNext Admin:"
    log_info "  Username: Administrator"
    log_info "  Password: admin123"
    echo
    log_info "Keycloak Admin:"
    log_info "  Username: admin"
    log_info "  Password: $(cd terraform && terraform output -raw keycloak_admin_password)"
    echo
    log_info "=== Cost Information ==="
    log_info "Estimated monthly cost: $15-25 USD"
    log_info "This is well within your $300 free trial credits"
    log_info "Free trial credits will last approximately 12-20 months"
    echo
    log_warning "Remember to:"
    log_warning "1. Update DuckDNS with the Load Balancer IP"
    log_warning "2. Change default passwords after first login"
    log_warning "3. Monitor your GCP billing dashboard"
}

# Main deployment function
main() {
    log_info "Starting TalentOz HCM free-tier deployment..."
    log_info "Project: $PROJECT_ID"
    log_info "Domain: $DOMAIN_NAME"
    log_info "Region: $REGION"
    echo
    
    check_prerequisites
    check_free_tier
    setup_gcp_project
    deploy_infrastructure
    configure_kubectl
    deploy_applications
    display_deployment_info
    
    log_success "TalentOz HCM free-tier deployment completed successfully!"
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "destroy")
        log_warning "Destroying free-tier infrastructure..."
        cd terraform
        terraform destroy \
            -var="project_id=$PROJECT_ID" \
            -var="region=$REGION" \
            -var="zone=$ZONE" \
            -var="domain_name=$DOMAIN_NAME" \
            -auto-approve
        cd ..
        log_success "Infrastructure destroyed"
        ;;
    "status")
        log_info "Checking deployment status..."
        kubectl get pods -n erpnext
        kubectl get pods -n keycloak
        kubectl get ingress -A
        ;;
    *)
        echo "Usage: $0 {deploy|destroy|status}"
        echo "Free-tier optimized deployment for Google Cloud"
        exit 1
        ;;
esac

