# TalentOz HCM - Deployment Guide

This guide provides step-by-step instructions for deploying the TalentOz HCM system on Google Cloud Platform.

## 📋 Prerequisites

### 1. Google Cloud Platform Setup
- GCP account with billing enabled
- Project with sufficient quotas for:
  - GKE Autopilot cluster
  - Cloud SQL instance
  - Memorystore Redis
  - Cloud Filestore
  - Load Balancer

### 2. Domain Configuration
- Domain name for SSL certificates
- Access to DNS management

### 3. OAuth Providers (Optional)
- Google OAuth 2.0 credentials
- Microsoft Azure AD credentials

### 4. Local Tools
```bash
# Install required tools
curl https://sdk.cloud.google.com | bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
curl https://get.helm.sh/helm-v3.12.0-linux-amd64.tar.gz | tar xz
```

## 🚀 Deployment Steps

### Step 1: Clone Repository
```bash
git clone https://github.com/AkhileshMishra/AgenticHR.git
cd AgenticHR
```

### Step 2: Configure Environment
```bash
# Set required environment variables
export PROJECT_ID="your-gcp-project-id"
export REGION="us-central1"
export ZONE="us-central1-a"
export DOMAIN_NAME="your-domain.com"

# Optional OAuth credentials
export GOOGLE_CLIENT_ID="your-google-client-id"
export GOOGLE_CLIENT_SECRET="your-google-client-secret"
export MICROSOFT_CLIENT_ID="your-microsoft-client-id"
export MICROSOFT_CLIENT_SECRET="your-microsoft-client-secret"
```

### Step 3: Authenticate with GCP
```bash
# Login to GCP
gcloud auth login

# Set project
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable container.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable compute.googleapis.com
gcloud services enable dns.googleapis.com
gcloud services enable redis.googleapis.com
gcloud services enable file.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### Step 4: Deploy Infrastructure
```bash
# Navigate to terraform directory
cd terraform

# Initialize Terraform
terraform init

# Plan deployment
terraform plan \
  -var="project_id=$PROJECT_ID" \
  -var="region=$REGION" \
  -var="zone=$ZONE" \
  -var="domain_name=$DOMAIN_NAME"

# Apply configuration
terraform apply \
  -var="project_id=$PROJECT_ID" \
  -var="region=$REGION" \
  -var="zone=$ZONE" \
  -var="domain_name=$DOMAIN_NAME"

# Get outputs
terraform output
```

### Step 5: Configure kubectl
```bash
# Get cluster credentials
gcloud container clusters get-credentials talentoz-gke \
  --region $REGION \
  --project $PROJECT_ID

# Verify connection
kubectl cluster-info
```

### Step 6: Install Helm Charts
```bash
# Add Helm repositories
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo add jetstack https://charts.jetstack.io
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Get load balancer IP from Terraform output
LB_IP=$(terraform output -raw load_balancer_ip)

# Install ingress-nginx
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.type=LoadBalancer \
  --set controller.service.loadBalancerIP="$LB_IP" \
  --wait

# Install cert-manager
helm upgrade --install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.13.0 \
  --set installCRDs=true \
  --wait
```

### Step 7: Update Kubernetes Manifests
```bash
cd ../

# Get infrastructure details
DB_CONNECTION_NAME=$(cd terraform && terraform output -raw db_instance_connection_name)
NFS_IP=$(cd terraform && terraform output -raw nfs_ip)

# Update manifests with actual values
sed -i "s/PROJECT_ID/$PROJECT_ID/g" kubernetes/erpnext-deployment.yaml
sed -i "s/REGION/$REGION/g" kubernetes/erpnext-deployment.yaml
sed -i "s/INSTANCE_NAME/talentoz-db/g" kubernetes/erpnext-deployment.yaml
sed -i "s/NFS_IP/$NFS_IP/g" kubernetes/erpnext-deployment.yaml

sed -i "s/PROJECT_ID/$PROJECT_ID/g" kubernetes/keycloak-deployment.yaml
sed -i "s/REGION/$REGION/g" kubernetes/keycloak-deployment.yaml
sed -i "s/INSTANCE_NAME/talentoz-db/g" kubernetes/keycloak-deployment.yaml
```

### Step 8: Deploy Applications
```bash
# Create namespaces
kubectl apply -f kubernetes/namespace.yaml

# Wait for cert-manager to be ready
kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=cert-manager -n cert-manager --timeout=300s

# Deploy cert-manager issuers and ingress
kubectl apply -f kubernetes/ingress.yaml

# Deploy ERPNext
kubectl apply -f kubernetes/erpnext-deployment.yaml

# Deploy Keycloak
kubectl apply -f kubernetes/keycloak-deployment.yaml

# Wait for deployments to be ready
kubectl wait --for=condition=Available deployment/erpnext -n erpnext --timeout=600s
kubectl wait --for=condition=Ready statefulset/keycloak -n keycloak --timeout=600s
```

### Step 9: Configure DNS
```bash
# Get load balancer IP
LB_IP=$(cd terraform && terraform output -raw load_balancer_ip)

echo "Configure your DNS with the following records:"
echo "erp.$DOMAIN_NAME    A    $LB_IP"
echo "id.$DOMAIN_NAME     A    $LB_IP"
```

### Step 10: Configure ERPNext
```bash
# Wait for ERPNext to be fully ready
sleep 60

# Get ERPNext pod
ERPNEXT_POD=$(kubectl get pods -n erpnext -l app=erpnext,component=backend -o jsonpath='{.items[0].metadata.name}')

# Initialize ERPNext site (if not already done)
kubectl exec -n erpnext $ERPNEXT_POD -c erpnext -- \
  bench new-site erp.$DOMAIN_NAME \
  --admin-password admin123 \
  --install-app erpnext

# Configure ERPNext Phase 1 features
python3 scripts/configure-erpnext-phase1.py \
  "https://erp.$DOMAIN_NAME" \
  "Administrator" \
  "admin123"
```

### Step 11: Configure Keycloak
```bash
# Get Keycloak admin password
KEYCLOAK_ADMIN_PASSWORD=$(kubectl get secret keycloak-secrets -n keycloak -o jsonpath='{.data.KEYCLOAK_ADMIN_PASSWORD}' | base64 -d)

# Configure Keycloak
python3 scripts/configure-keycloak.py \
  "https://id.$DOMAIN_NAME" \
  "admin" \
  "$KEYCLOAK_ADMIN_PASSWORD"
```

## ✅ Verification

### 1. Check Application Status
```bash
# Check pods
kubectl get pods -n erpnext
kubectl get pods -n keycloak

# Check ingress
kubectl get ingress -A

# Check certificates
kubectl get certificates -A
```

### 2. Test Applications
```bash
# Test ERPNext
curl -f https://erp.$DOMAIN_NAME/api/method/ping

# Test Keycloak
curl -f https://id.$DOMAIN_NAME/realms/erpnext
```

### 3. Access Applications
- **ERPNext**: https://erp.your-domain.com
  - Username: Administrator
  - Password: admin123

- **Keycloak Admin**: https://id.your-domain.com/admin
  - Username: admin
  - Password: (from secret)

## 🔧 Post-Deployment Configuration

### 1. Change Default Passwords
```bash
# ERPNext Administrator password
# Login to ERPNext and change password in User settings

# Keycloak admin password
# Login to Keycloak admin console and change password
```

### 2. Configure OAuth Providers
```bash
# In Keycloak admin console:
# 1. Go to Identity Providers
# 2. Configure Google OAuth
# 3. Configure Microsoft Azure AD
# 4. Set client IDs and secrets
```

### 3. Create Users and Roles
```bash
# In Keycloak:
# 1. Create users in appropriate groups
# 2. Assign roles based on job functions
# 3. Test SSO login flow

# In ERPNext:
# 1. Create employee records
# 2. Set up departments and designations
# 3. Configure leave policies
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Pods Not Starting
```bash
# Check pod status
kubectl describe pod <pod-name> -n <namespace>

# Check logs
kubectl logs <pod-name> -n <namespace>

# Check resource limits
kubectl top pods -n <namespace>
```

#### 2. Database Connection Issues
```bash
# Check Cloud SQL proxy
kubectl logs <pod-name> -c cloud-sql-proxy -n <namespace>

# Verify database connectivity
kubectl exec -it <pod-name> -n <namespace> -- nc -zv 127.0.0.1 3306
```

#### 3. SSL Certificate Issues
```bash
# Check certificate status
kubectl describe certificate <cert-name> -n <namespace>

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager

# Verify DNS propagation
nslookup erp.$DOMAIN_NAME
```

#### 4. Ingress Issues
```bash
# Check ingress status
kubectl describe ingress <ingress-name> -n <namespace>

# Check nginx-ingress logs
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller
```

### Useful Commands

```bash
# Port forward for debugging
kubectl port-forward -n erpnext svc/erpnext-service 8000:80
kubectl port-forward -n keycloak svc/keycloak-service 8080:80

# Access ERPNext shell
kubectl exec -it -n erpnext deployment/erpnext -c erpnext -- bash

# View all resources
kubectl get all -A

# Check resource usage
kubectl top nodes
kubectl top pods -A
```

## 🗑️ Cleanup

### Remove Applications
```bash
# Delete Kubernetes resources
kubectl delete -f kubernetes/

# Delete Helm releases
helm uninstall ingress-nginx -n ingress-nginx
helm uninstall cert-manager -n cert-manager

# Delete namespaces
kubectl delete namespace erpnext keycloak ingress-nginx cert-manager
```

### Remove Infrastructure
```bash
cd terraform
terraform destroy \
  -var="project_id=$PROJECT_ID" \
  -var="region=$REGION" \
  -var="zone=$ZONE" \
  -var="domain_name=$DOMAIN_NAME"
```

## 📞 Support

For deployment issues:
1. Check the troubleshooting section
2. Review logs for error messages
3. Verify all prerequisites are met
4. Create an issue in the GitHub repository

## 🔄 Updates

To update the deployment:
1. Pull latest changes from repository
2. Review changelog for breaking changes
3. Update Terraform configuration if needed
4. Apply Kubernetes manifest updates
5. Test functionality after updates

---

This deployment guide provides comprehensive instructions for setting up TalentOz HCM in production. Follow each step carefully and refer to the troubleshooting section if you encounter any issues.

