# TalentOz HCM - Quick Start Guide

Get your production-ready HR system up and running in 30 minutes!

## 🚀 One-Command Deployment

```bash
# Clone and deploy
git clone https://github.com/AkhileshMishra/AgenticHR.git
cd AgenticHR
export PROJECT_ID="your-gcp-project-id"
export DOMAIN_NAME="your-domain.com"
./scripts/deploy.sh deploy
```

## 📋 Prerequisites Checklist

- [ ] GCP account with billing enabled
- [ ] Domain name for SSL certificates
- [ ] `gcloud`, `kubectl`, `terraform`, `helm` installed
- [ ] GCP project with sufficient quotas

## ⚡ Quick Setup Steps

### 1. Environment Setup (2 minutes)
```bash
export PROJECT_ID="talentoz-prod"
export DOMAIN_NAME="talentoz.com"
gcloud auth login
gcloud config set project $PROJECT_ID
```

### 2. Deploy Infrastructure (15 minutes)
```bash
./scripts/deploy.sh deploy
```

### 3. Configure DNS (5 minutes)
```bash
# Get load balancer IP
LB_IP=$(cd terraform && terraform output -raw load_balancer_ip)

# Add DNS records:
# erp.your-domain.com    A    $LB_IP
# id.your-domain.com     A    $LB_IP
```

### 4. Access Applications (2 minutes)
- **ERPNext**: https://erp.your-domain.com
  - Username: Administrator
  - Password: admin123

- **Keycloak**: https://id.your-domain.com/admin
  - Username: admin
  - Password: (check deployment output)

## 🎯 What You Get

### ✅ Phase 1 Features (Production Ready)
- **Employee Management**: Complete employee lifecycle
- **Leave Management**: Advanced leave policies and workflows
- **Attendance Tracking**: Biometric and geo-tagged check-ins
- **Payroll Processing**: Automated payroll with compliance
- **SSO Authentication**: Google/Microsoft login with MFA

### 🔐 Security Features
- Multi-factor authentication (TOTP + WebAuthn)
- Role-based access control
- SSL/TLS encryption
- Network security policies
- Audit logging

### 🏗️ Infrastructure
- GKE Autopilot cluster
- Cloud SQL (MySQL) with HA
- Memorystore Redis
- Cloud Filestore (NFS)
- Automated backups
- Load balancing

## 🔧 Post-Deployment Tasks

### 1. Change Default Passwords
```bash
# ERPNext: Login and change Administrator password
# Keycloak: Login to admin console and change admin password
```

### 2. Configure OAuth (Optional)
```bash
# Set environment variables for OAuth providers
export GOOGLE_CLIENT_ID="your-google-client-id"
export GOOGLE_CLIENT_SECRET="your-google-client-secret"
export MICROSOFT_CLIENT_ID="your-microsoft-client-id"
export MICROSOFT_CLIENT_SECRET="your-microsoft-client-secret"

# Reconfigure Keycloak
python3 scripts/configure-keycloak.py \
  "https://id.$DOMAIN_NAME" \
  "admin" \
  "$KEYCLOAK_ADMIN_PASSWORD"
```

### 3. Create Test Users
```bash
# In Keycloak admin console:
# 1. Go to Users → Add User
# 2. Set username, email, first/last name
# 3. Go to Credentials → Set password
# 4. Go to Groups → Join appropriate group
```

## 🎯 Next Steps

### Phase 2 Deployment (Optional)
```bash
# Deploy additional HR modules
python3 scripts/configure-erpnext-phase2.py

# Features added:
# - Talent Acquisition
# - Performance Management
# - Training & Development
```

### Phase 3 Deployment (Optional)
```bash
# Deploy advanced features
python3 scripts/configure-erpnext-phase3.py

# Features added:
# - Business Intelligence
# - Advanced Analytics
# - API Integrations
```

## 🔍 Health Check

```bash
# Check deployment status
./scripts/deploy.sh status

# Test endpoints
curl -f https://erp.$DOMAIN_NAME/api/method/ping
curl -f https://id.$DOMAIN_NAME/realms/erpnext
```

## 🆘 Troubleshooting

### Common Issues

**DNS not resolving?**
```bash
nslookup erp.$DOMAIN_NAME
# Wait for DNS propagation (up to 24 hours)
```

**SSL certificate pending?**
```bash
kubectl describe certificate erpnext-tls -n erpnext
# Check cert-manager logs if issues persist
```

**Pods not starting?**
```bash
kubectl get pods -A
kubectl describe pod <pod-name> -n <namespace>
```

## 📞 Support

- 📖 Full documentation: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- 🐛 Issues: [GitHub Issues](https://github.com/AkhileshMishra/AgenticHR/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/AkhileshMishra/AgenticHR/discussions)

## 🗑️ Cleanup

```bash
# Remove everything
./scripts/deploy.sh destroy
```

---

**Ready to transform your HR operations? Start your deployment now!** 🚀

