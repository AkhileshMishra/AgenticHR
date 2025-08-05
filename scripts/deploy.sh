#!/bin/bash

# TalentOz HCM - Automated Deployment Script
# ERPNext HR + Keycloak on Google Cloud Platform

set -euo pipefail

# Configuration
PROJECT_ID="${PROJECT_ID:-talentoz-prod}"
REGION="${REGION:-us-central1}"
ZONE="${ZONE:-us-central1-a}"
CLUSTER_NAME="${CLUSTER_NAME:-talentoz-gke}"
DOMAIN_NAME="${DOMAIN_NAME:-talentoz.com}"

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
    log_info "Checking prerequisites..."
    
    # Check if required tools are installed
    local tools=("gcloud" "kubectl" "terraform" "helm")
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
    
    log_success "Prerequisites check passed"
}

# Set up GCP project
setup_gcp_project() {
    log_info "Setting up GCP project: $PROJECT_ID"
    
    # Set the project
    gcloud config set project "$PROJECT_ID"
    
    # Enable billing (if not already enabled)
    if ! gcloud billing projects describe "$PROJECT_ID" &> /dev/null; then
        log_warning "Billing is not enabled for project $PROJECT_ID"
        log_info "Please enable billing in the GCP Console"
        read -p "Press Enter to continue after enabling billing..."
    fi
    
    log_success "GCP project setup completed"
}

# Deploy infrastructure with Terraform
deploy_infrastructure() {
    log_info "Deploying infrastructure with Terraform..."
    
    cd terraform
    
    # Initialize Terraform
    terraform init
    
    # Plan the deployment
    terraform plan \
        -var="project_id=$PROJECT_ID" \
        -var="region=$REGION" \
        -var="zone=$ZONE" \
        -var="domain_name=$DOMAIN_NAME"
    
    # Apply the configuration
    log_info "Applying Terraform configuration..."
    terraform apply \
        -var="project_id=$PROJECT_ID" \
        -var="region=$REGION" \
        -var="zone=$ZONE" \
        -var="domain_name=$DOMAIN_NAME" \
        -auto-approve
    
    # Get outputs
    DB_CONNECTION_NAME=$(terraform output -raw db_instance_connection_name)
    REDIS_HOST=$(terraform output -raw redis_host)
    NFS_IP=$(terraform output -raw nfs_ip)
    LB_IP=$(terraform output -raw load_balancer_ip)
    
    cd ..
    
    log_success "Infrastructure deployment completed"
    log_info "Database Connection: $DB_CONNECTION_NAME"
    log_info "Redis Host: $REDIS_HOST"
    log_info "NFS IP: $NFS_IP"
    log_info "Load Balancer IP: $LB_IP"
}

# Configure kubectl
configure_kubectl() {
    log_info "Configuring kubectl..."
    
    gcloud container clusters get-credentials "$CLUSTER_NAME" \
        --region "$REGION" \
        --project "$PROJECT_ID"
    
    log_success "kubectl configured successfully"
}

# Install required Helm charts
install_helm_charts() {
    log_info "Installing required Helm charts..."
    
    # Add Helm repositories
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    helm repo add jetstack https://charts.jetstack.io
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update
    
    # Install ingress-nginx
    log_info "Installing ingress-nginx..."
    helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
        --namespace ingress-nginx \
        --create-namespace \
        --set controller.service.type=LoadBalancer \
        --set controller.service.loadBalancerIP="$LB_IP" \
        --set controller.service.annotations."cloud\.google\.com/load-balancer-type"="External" \
        --wait
    
    # Install cert-manager
    log_info "Installing cert-manager..."
    helm upgrade --install cert-manager jetstack/cert-manager \
        --namespace cert-manager \
        --create-namespace \
        --version v1.13.0 \
        --set installCRDs=true \
        --wait
    
    # Install monitoring stack (optional)
    if [[ "${INSTALL_MONITORING:-false}" == "true" ]]; then
        log_info "Installing monitoring stack..."
        helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
            --namespace monitoring \
            --create-namespace \
            --wait
    fi
    
    log_success "Helm charts installed successfully"
}

# Update Kubernetes manifests with actual values
update_manifests() {
    log_info "Updating Kubernetes manifests with actual values..."
    
    # Update ERPNext deployment
    sed -i "s/PROJECT_ID/$PROJECT_ID/g" kubernetes/erpnext-deployment.yaml
    sed -i "s/REGION/$REGION/g" kubernetes/erpnext-deployment.yaml
    sed -i "s/INSTANCE_NAME/talentoz-db/g" kubernetes/erpnext-deployment.yaml
    sed -i "s/NFS_IP/$NFS_IP/g" kubernetes/erpnext-deployment.yaml
    
    # Update Keycloak deployment
    sed -i "s/PROJECT_ID/$PROJECT_ID/g" kubernetes/keycloak-deployment.yaml
    sed -i "s/REGION/$REGION/g" kubernetes/keycloak-deployment.yaml
    sed -i "s/INSTANCE_NAME/talentoz-db/g" kubernetes/keycloak-deployment.yaml
    
    # Update service account annotations
    sed -i "s/PROJECT_ID/$PROJECT_ID/g" kubernetes/erpnext-deployment.yaml
    sed -i "s/PROJECT_ID/$PROJECT_ID/g" kubernetes/keycloak-deployment.yaml
    
    log_success "Kubernetes manifests updated"
}

# Deploy Kubernetes resources
deploy_kubernetes() {
    log_info "Deploying Kubernetes resources..."
    
    # Create namespaces
    kubectl apply -f kubernetes/namespace.yaml
    
    # Wait for namespaces to be ready
    kubectl wait --for=condition=Ready namespace/erpnext --timeout=60s
    kubectl wait --for=condition=Ready namespace/keycloak --timeout=60s
    
    # Deploy cert-manager issuers
    kubectl apply -f kubernetes/ingress.yaml
    
    # Wait for cert-manager to be ready
    kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=cert-manager -n cert-manager --timeout=300s
    
    # Deploy ERPNext
    log_info "Deploying ERPNext..."
    kubectl apply -f kubernetes/erpnext-deployment.yaml
    
    # Deploy Keycloak
    log_info "Deploying Keycloak..."
    kubectl apply -f kubernetes/keycloak-deployment.yaml
    
    # Wait for deployments to be ready
    log_info "Waiting for deployments to be ready..."
    kubectl wait --for=condition=Available deployment/erpnext -n erpnext --timeout=600s
    kubectl wait --for=condition=Ready statefulset/keycloak -n keycloak --timeout=600s
    
    log_success "Kubernetes resources deployed successfully"
}

# Configure ERPNext
configure_erpnext() {
    log_info "Configuring ERPNext..."
    
    # Get ERPNext pod
    ERPNEXT_POD=$(kubectl get pods -n erpnext -l app=erpnext,component=backend -o jsonpath='{.items[0].metadata.name}')
    
    # Initialize ERPNext site
    log_info "Initializing ERPNext site..."
    kubectl exec -n erpnext "$ERPNEXT_POD" -c erpnext -- \
        bench new-site erp.talentoz.com \
        --admin-password admin123 \
        --mariadb-root-password "$(kubectl get secret erpnext-secrets -n erpnext -o jsonpath='{.data.FRAPPE_DB_PASSWORD}' | base64 -d)" \
        --install-app erpnext
    
    # Enable required modules
    log_info "Enabling HR modules..."
    kubectl exec -n erpnext "$ERPNEXT_POD" -c erpnext -- \
        bench --site erp.talentoz.com execute "frappe.db.set_value('Domain Settings', 'Domain Settings', 'hr', 1)"
    
    kubectl exec -n erpnext "$ERPNEXT_POD" -c erpnext -- \
        bench --site erp.talentoz.com execute "frappe.db.set_value('Domain Settings', 'Domain Settings', 'payroll', 1)"
    
    # Install OIDC app (if available)
    if kubectl exec -n erpnext "$ERPNEXT_POD" -c erpnext -- bench get-app oidc_extended &> /dev/null; then
        log_info "Installing OIDC extension..."
        kubectl exec -n erpnext "$ERPNEXT_POD" -c erpnext -- \
            bench --site erp.talentoz.com install-app oidc_extended
    fi
    
    log_success "ERPNext configuration completed"
}

# Configure Keycloak
configure_keycloak() {
    log_info "Configuring Keycloak..."
    
    # Get Keycloak admin password
    KEYCLOAK_ADMIN_PASSWORD=$(kubectl get secret keycloak-secrets -n keycloak -o jsonpath='{.data.KEYCLOAK_ADMIN_PASSWORD}' | base64 -d)
    
    log_info "Keycloak admin credentials:"
    log_info "URL: https://id.$DOMAIN_NAME"
    log_info "Username: admin"
    log_info "Password: $KEYCLOAK_ADMIN_PASSWORD"
    
    # Wait for Keycloak to be ready
    log_info "Waiting for Keycloak to be ready..."
    kubectl wait --for=condition=Ready pod -l app=keycloak -n keycloak --timeout=600s
    
    log_success "Keycloak configuration completed"
}

# Display deployment information
display_deployment_info() {
    log_success "Deployment completed successfully!"
    echo
    log_info "=== Deployment Information ==="
    log_info "ERPNext URL: https://erp.$DOMAIN_NAME"
    log_info "Keycloak URL: https://id.$DOMAIN_NAME"
    log_info "Load Balancer IP: $LB_IP"
    echo
    log_info "=== DNS Configuration ==="
    log_info "Please configure your DNS to point the following records to $LB_IP:"
    log_info "  erp.$DOMAIN_NAME A $LB_IP"
    log_info "  id.$DOMAIN_NAME A $LB_IP"
    echo
    log_info "=== Default Credentials ==="
    log_info "ERPNext Admin:"
    log_info "  Username: Administrator"
    log_info "  Password: admin123"
    echo
    log_info "Keycloak Admin:"
    log_info "  Username: admin"
    log_info "  Password: $(kubectl get secret keycloak-secrets -n keycloak -o jsonpath='{.data.KEYCLOAK_ADMIN_PASSWORD}' | base64 -d)"
    echo
    log_warning "Please change default passwords after first login!"
}

# Main deployment function
main() {
    log_info "Starting TalentOz HCM deployment..."
    
    check_prerequisites
    setup_gcp_project
    deploy_infrastructure
    configure_kubectl
    install_helm_charts
    update_manifests
    deploy_kubernetes
    configure_erpnext
    configure_keycloak
    display_deployment_info
    
    log_success "TalentOz HCM deployment completed successfully!"
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "destroy")
        log_warning "Destroying infrastructure..."
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
        exit 1
        ;;
esac

