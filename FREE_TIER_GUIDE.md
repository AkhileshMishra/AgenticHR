# TalentOz HCM - Free Tier Deployment Guide

Deploy TalentOz HCM within Google Cloud's **$300 free trial credits** in India!

## 💰 **Cost Breakdown**

### **Monthly Costs (Optimized for Free Tier)**
- **GKE Cluster**: 2x e2-small preemptible nodes (~$10/month)
- **Database VM**: 1x f1-micro (FREE - Always Free Tier)
- **Load Balancer**: ~$5/month
- **Storage & Networking**: ~$5/month
- **Total**: ~$20/month (12+ months with $300 credits)

### **What's Different from Production Version**
- ✅ Uses f1-micro VM for database instead of Cloud SQL
- ✅ Uses preemptible nodes (80% cost reduction)
- ✅ Single replica deployments
- ✅ HTTP instead of HTTPS (no cert-manager costs)
- ✅ No Redis Memorystore (uses VM-based Redis)
- ✅ No Cloud Filestore (uses local storage)

## 🚀 **Quick Deployment**

### **Prerequisites**
- Google Cloud account with $300 free trial activated
- Project ID: `skilful-bearing-461609-j8` (your project)
- Domain: `agentichr.duckdns.org` (your DuckDNS domain)

### **One-Command Deployment**
```bash
# In Google Cloud Shell
git clone https://github.com/AkhileshMishra/AgenticHR.git
cd AgenticHR

# Set your configuration
export PROJECT_ID="skilful-bearing-461609-j8"
export DOMAIN_NAME="agentichr.duckdns.org"

# Deploy free-tier optimized version
./scripts/deploy-free-tier.sh deploy
```

## 📋 **Step-by-Step Instructions**

### **Step 1: Open Google Cloud Shell**
1. Go to https://console.cloud.google.com/
2. Select project: `skilful-bearing-461609-j8`
3. Click Cloud Shell icon (>_) in top toolbar

### **Step 2: Clone and Configure**
```bash
# Clone repository
git clone https://github.com/AkhileshMishra/AgenticHR.git
cd AgenticHR

# Set environment variables
export PROJECT_ID="skilful-bearing-461609-j8"
export DOMAIN_NAME="agentichr.duckdns.org"
export REGION="us-central1"  # Best for free tier
```

### **Step 3: Deploy Infrastructure**
```bash
# Run free-tier deployment
./scripts/deploy-free-tier.sh deploy
```

**What happens during deployment:**
- ✅ Enables required GCP APIs
- ✅ Creates VPC and subnets
- ✅ Deploys GKE cluster with cost-optimized settings
- ✅ Creates f1-micro VM with MySQL and Redis
- ✅ Deploys ERPNext and Keycloak applications
- ✅ Sets up load balancer

### **Step 4: Configure DuckDNS**
```bash
# Get your load balancer IP
cd terraform
LB_IP=$(terraform output -raw load_balancer_ip)
echo "Update DuckDNS with IP: $LB_IP"
```

**Update DuckDNS:**
1. Go to https://www.duckdns.org/
2. Find your domain: `agentichr`
3. Update IP address to your `$LB_IP`
4. Click "update ip"

### **Step 5: Access Your System**
After DNS propagation (5-10 minutes):
- **ERPNext**: http://erp.agentichr.duckdns.org
- **Keycloak**: http://id.agentichr.duckdns.org

## 🔐 **Default Credentials**

### **ERPNext**
- **URL**: http://erp.agentichr.duckdns.org
- **Username**: Administrator
- **Password**: admin123

### **Keycloak**
- **URL**: http://id.agentichr.duckdns.org/admin
- **Username**: admin
- **Password**: (shown in deployment output)

## 🎯 **Features Included**

### **Core HR Features**
- ✅ Employee Management
- ✅ Leave Management
- ✅ Attendance Tracking
- ✅ Basic Payroll
- ✅ User Authentication

### **Infrastructure**
- ✅ Kubernetes cluster (cost-optimized)
- ✅ MySQL database on f1-micro VM
- ✅ Redis cache
- ✅ Load balancer
- ✅ Automated deployment

## 📊 **Monitoring Your Costs**

### **Check Your Spending**
```bash
# View current costs
gcloud billing budgets list --billing-account=$(gcloud billing accounts list --format="value(name)")

# Check resource usage
gcloud compute instances list
gcloud container clusters list
```

### **Cost Optimization Tips**
1. **Use preemptible nodes** (already configured)
2. **Stop VMs when not needed**:
   ```bash
   gcloud compute instances stop talentoz-db-vm --zone=us-central1-a
   ```
3. **Monitor billing alerts** in GCP Console
4. **Delete unused resources** regularly

## 🔧 **Scaling Options**

### **Upgrade to Production Later**
```bash
# Switch to production configuration
cp terraform/main.tf terraform/main-free-tier.tf.backup
cp terraform/main-production.tf terraform/main.tf

# Redeploy with production settings
./scripts/deploy.sh deploy
```

### **Add More Features**
```bash
# Add SSL certificates
kubectl apply -f kubernetes/ssl-certificates.yaml

# Enable additional HR modules
python3 scripts/configure-erpnext-phase2.py
```

## 🆘 **Troubleshooting**

### **Common Issues**

**1. Deployment fails with quota errors**
```bash
# Check quotas
gcloud compute project-info describe --project=$PROJECT_ID

# Request quota increase if needed
```

**2. Pods not starting**
```bash
# Check pod status
kubectl get pods -A
kubectl describe pod <pod-name> -n <namespace>

# Check node resources
kubectl top nodes
```

**3. Database connection issues**
```bash
# Check database VM
gcloud compute instances list
gcloud compute ssh talentoz-db-vm --zone=us-central1-a

# Test database connectivity
mysql -u erpnext -p -h <VM_IP>
```

**4. DNS not resolving**
```bash
# Check DNS propagation
nslookup erp.agentichr.duckdns.org
nslookup id.agentichr.duckdns.org

# Update DuckDNS if needed
```

## 📈 **Free Trial Timeline**

### **Your $300 Credits Will Last:**
- **Month 1-3**: ~$20/month = $60 total
- **Month 4-6**: ~$20/month = $60 total  
- **Month 7-9**: ~$20/month = $60 total
- **Month 10-12**: ~$20/month = $60 total
- **Month 13-15**: ~$20/month = $60 total
- **Total**: ~15 months of usage

### **After Free Trial**
- **Always Free Tier**: f1-micro VM remains free
- **Paid Services**: GKE cluster (~$15/month)
- **Option**: Migrate to single VM deployment

## 🔄 **Cleanup**

### **Destroy Everything**
```bash
# Remove all resources
./scripts/deploy-free-tier.sh destroy

# Verify cleanup
gcloud compute instances list
gcloud container clusters list
```

## 📞 **Support**

### **Getting Help**
- 📖 Check logs: `kubectl logs <pod-name> -n <namespace>`
- 🔍 Debug: `kubectl describe pod <pod-name> -n <namespace>`
- 💬 Issues: [GitHub Issues](https://github.com/AkhileshMishra/AgenticHR/issues)

### **Useful Commands**
```bash
# Check deployment status
./scripts/deploy-free-tier.sh status

# View all resources
kubectl get all -A

# Check costs
gcloud billing budgets list
```

---

**Ready to deploy your free HR system? Start now with just one command!** 🚀

```bash
./scripts/deploy-free-tier.sh deploy
```

