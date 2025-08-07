# TalentOz HCM - AgenticHR System

## 🎯 **CORRECTED DEPLOYMENT - PRODUCTION READY**

This repository contains the **corrected and tested** TalentOz HCM system based on ERPNext HR + Keycloak, optimized for Google Cloud Platform deployment. All issues from the initial deployment have been resolved.

## ⚡ **Quick Start (Corrected Version)**

### **Prerequisites**
- Google Cloud Project with billing enabled
- Domain name (we recommend [DuckDNS](https://www.duckdns.org/) for free domains)
- $300 Google Cloud free trial (will last 15+ months with our optimized setup)

### **One-Command Deployment**

```bash
# 1. Open Google Cloud Shell (https://console.cloud.google.com/)
# 2. Clone repository
git clone https://github.com/AkhileshMishra/AgenticHR.git
cd AgenticHR

# 3. Set your environment
export PROJECT_ID="your-gcp-project-id"
export DOMAIN_NAME="your-domain.duckdns.org"

# 4. Deploy (CORRECTED VERSION)
./scripts/deploy-corrected-final.sh
```

## 🔧 **What Was Fixed**

Based on extensive troubleshooting, we resolved:

### ✅ **Terraform Conflicts**
- **Issue**: Multiple `.tf` files causing resource conflicts
- **Fix**: Single, clean configuration file

### ✅ **ERPNext Site Persistence**
- **Issue**: Sites lost on pod restarts
- **Fix**: Persistent volumes for site data

### ✅ **Database Authentication**
- **Issue**: Access denied errors for frappe user
- **Fix**: Proper database user creation with correct permissions

### ✅ **Health Check Failures**
- **Issue**: Readiness probes causing restart loops
- **Fix**: Correct endpoints with proper host headers

### ✅ **Service Dependencies**
- **Issue**: ERPNext starting before database ready
- **Fix**: Robust dependency checking with retries

### ✅ **External Access**
- **Issue**: "site does not exist" for external IPs
- **Fix**: Wildcard host configuration

## 📋 **Deployment Options**

### **Option 1: Automated Script (Recommended)**
```bash
./scripts/deploy-corrected-final.sh
```
- **Time**: 15-20 minutes
- **Complexity**: Low
- **Reliability**: High

### **Option 2: Kubernetes Manifests**
```bash
kubectl apply -f kubernetes/erpnext-complete.yaml
```
- **Time**: 10-15 minutes
- **Complexity**: Medium
- **Customization**: High

## 💰 **Cost Optimization**

### **Free Tier Setup (Recommended)**
- **Monthly Cost**: ~$15 USD
- **Free Trial Duration**: 15+ months
- **Components**:
  - 2x e2-small preemptible nodes
  - LoadBalancer
  - Persistent storage (20GB)

### **Production Setup**
- **Monthly Cost**: ~$300 USD
- **Components**:
  - Cloud SQL database
  - Redis Memorystore
  - Standard compute nodes
  - SSL certificates

## 🎯 **System Features**

### **Core HR Functionality**
- ✅ Employee Management
- ✅ Leave Management
- ✅ Attendance Tracking
- ✅ Payroll Processing
- ✅ Performance Management
- ✅ Recruitment Management

### **Identity & Access Management**
- ✅ Multi-Factor Authentication
- ✅ Google OAuth 2.0 Integration
- ✅ Microsoft Azure AD Integration
- ✅ Role-Based Access Control
- ✅ Single Sign-On (SSO)

### **Technical Features**
- ✅ Kubernetes-native deployment
- ✅ Auto-scaling capabilities
- ✅ Persistent data storage
- ✅ Load balancing
- ✅ Health monitoring

## 🚀 **Post-Deployment Steps**

### **1. Configure DNS**
After deployment, you'll get a LoadBalancer IP:
```bash
# Update your domain to point to the LoadBalancer IP
# For DuckDNS: Go to https://www.duckdns.org/ and update your domain
```

### **2. Access Your System**
- **URL**: `http://your-domain.duckdns.org`
- **Username**: `Administrator`
- **Password**: `TalentOz2024!`

### **3. Initial Configuration**
1. Change default passwords
2. Configure company information
3. Set up employee records
4. Configure leave policies
5. Set up payroll components

## 🔍 **Troubleshooting**

### **Common Issues and Solutions**

#### **Pod Not Ready**
```bash
kubectl get pods
kubectl describe pod <pod-name>
kubectl logs <pod-name>
```

#### **Database Connection Issues**
```bash
kubectl exec -it <erpnext-pod> -- mysql -h mariadb -u root -pTalentOz2024! -e "SELECT 1"
```

#### **Site Access Issues**
```bash
kubectl exec -it <erpnext-pod> -- bench --site localhost doctor
```

### **Useful Commands**
```bash
# Check deployment status
kubectl get all

# View ERPNext logs
kubectl logs deployment/erpnext

# Access ERPNext shell
kubectl exec -it deployment/erpnext -- bash

# Test external access
curl -H "Host: localhost" http://<EXTERNAL-IP>
```

## 📚 **Documentation**

- **[Lessons Learned](LESSONS_LEARNED.md)**: Detailed troubleshooting experience
- **[Implementation Strategy](IMPLEMENTATION_STRATEGY.md)**: Technical architecture
- **[Deployment Guide](DEPLOYMENT_GUIDE.md)**: Step-by-step instructions
- **[Quick Start](QUICK_START.md)**: Fast deployment guide

## 🔐 **Security Considerations**

### **Default Passwords**
⚠️ **IMPORTANT**: Change these default passwords immediately after deployment:
- ERPNext Administrator: `TalentOz2024!`
- Database root: `TalentOz2024!`
- Database frappe user: `TalentOz2024!`

### **Network Security**
- LoadBalancer with external IP (HTTP only for cost optimization)
- Internal cluster networking for database and cache
- Kubernetes network policies (optional)

### **Data Security**
- Persistent volumes for data retention
- Regular backup recommendations
- Database encryption at rest (GCP default)

## 🎉 **Success Metrics**

After successful deployment, you should have:
- ✅ **Working ERPNext system** accessible via browser
- ✅ **Persistent data storage** surviving pod restarts
- ✅ **Stable pods** without restart loops
- ✅ **External access** via LoadBalancer IP
- ✅ **Cost-optimized setup** within free trial limits

## 🆘 **Support**

### **If Deployment Fails**
1. Check the [Lessons Learned](LESSONS_LEARNED.md) document
2. Review pod logs: `kubectl logs deployment/erpnext`
3. Verify prerequisites and environment variables
4. Try the alternative Kubernetes manifest approach

### **For Production Deployment**
1. Use the production Terraform configuration
2. Enable SSL certificates
3. Configure proper backup strategies
4. Implement monitoring and alerting

## 🔄 **Upgrade Path**

### **From Free Tier to Production**
```bash
# Switch to production configuration
cp terraform/main-production.tf terraform/main.tf
./scripts/deploy-full-system.sh
```

### **Adding Keycloak SSO**
```bash
# Deploy Keycloak after ERPNext is stable
kubectl apply -f kubernetes/keycloak-deployment.yaml
```

## 📊 **Monitoring**

### **Basic Monitoring**
```bash
# Pod health
kubectl get pods

# Resource usage
kubectl top pods

# Service status
kubectl get services
```

### **Advanced Monitoring**
- Google Cloud Monitoring integration
- Prometheus and Grafana (optional)
- Custom dashboards for HR metrics

## 🎯 **Next Steps**

1. **Deploy the system** using the corrected script
2. **Configure your organization** data
3. **Set up user accounts** and permissions
4. **Customize workflows** for your needs
5. **Plan for production** scaling when ready

---

## 🏆 **Why This Version Works**

This corrected version addresses all the issues encountered during the initial deployment:

- **Persistent Storage**: No more data loss on restarts
- **Proper Dependencies**: Services start in correct order
- **Robust Health Checks**: No more restart loops
- **External Access**: Works with any domain or IP
- **Cost Optimized**: Fits within Google Cloud free trial
- **Production Ready**: Scalable architecture for growth

**Your TalentOz HCM system is now ready for reliable production use!** 🚀

