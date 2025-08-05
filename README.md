# TalentOz HCM - Production-Ready HR Management System

A comprehensive Human Capital Management (HCM) system built on ERPNext HR with Keycloak authentication, deployed on Google Cloud Platform with full automation.

## 🚀 Features

### Phase 1: Core HR Features (Production Ready)
- **Identity & Access Management**: Keycloak with Google/Microsoft SSO and MFA
- **Employee Management**: Complete employee lifecycle management
- **Leave Management**: Advanced leave policies and approval workflows
- **Attendance Management**: Biometric integration and geo-tagged check-ins
- **Payroll Management**: Automated payroll processing with statutory compliance

### Phase 2: Extended HR Features
- **Talent Acquisition**: End-to-end recruitment workflow
- **Onboarding**: Structured employee onboarding process
- **Performance Management**: Goal setting and appraisal systems
- **Claims & Travel**: Expense management and travel workflows

### Phase 3: Enterprise Features
- **Competency Management**: Skills tracking and certification
- **Learning & Development**: Training programs and evaluation
- **Business Intelligence**: Self-service reporting and analytics
- **Advanced Integrations**: API connectors and workflow automation

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│  Internet (HTTPS, 443)                 │
└──────────────┬──────────────────────────┘
               │
┌──────────────┴──────────────┐
│  Cloud Load-Balancer (GCLB) │
└──────────────┬──────────────┘
               │
 ┌─────────────┴─────────────┐
 │  GKE Autopilot Cluster    │
 │  • namespace: erpnext     │
 │  • namespace: keycloak    │
 │  • cert-manager (TLS)     │
 │  • nginx-ingress          │
 └─┬────────┬────────────────┘
   │        │
   │        │
┌─┴────────┴─┐            ┌────────────┐
│ ERPNext    │──MariaDB──►│ Cloud SQL  │
│ Pods       │──Redis────►│ Memorystore│
└─┬──────────┘            └────────────┘
  │
  │ OIDC / OAuth2
  │
┌─┴────────────────────────────────┐
│ Keycloak StatefulSet              │
│ • Realm: erpnext                 │
│ • Google IdP & Azure IdP         │
│ • TOTP / Push MFA flows          │
│ • SCIM 2.0 → ERPNext (optional) │
└──────────────────────────────────┘
```

## 🛠️ Technology Stack

- **Frontend**: ERPNext Web UI (Frappe Framework)
- **Backend**: ERPNext v14 (Python/Frappe)
- **Authentication**: Keycloak 22 with OIDC
- **Database**: Cloud SQL (MySQL 8.0)
- **Cache**: Memorystore Redis
- **Storage**: Cloud Filestore (NFS)
- **Container Orchestration**: GKE Autopilot
- **Infrastructure**: Google Cloud Platform
- **IaC**: Terraform
- **CI/CD**: GitHub Actions

## 📋 Prerequisites

- Google Cloud Platform account with billing enabled
- Domain name for SSL certificates
- Google OAuth 2.0 credentials (optional)
- Microsoft Azure AD credentials (optional)

### Required Tools
- `gcloud` CLI
- `kubectl`
- `terraform` >= 1.0
- `helm` >= 3.0
- `git`

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/AkhileshMishra/AgenticHR.git
cd AgenticHR
```

### 2. Configure Environment
```bash
# Set your GCP project ID
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export DOMAIN_NAME="your-domain.com"

# Optional: Set OAuth credentials
export GOOGLE_CLIENT_ID="your-google-client-id"
export GOOGLE_CLIENT_SECRET="your-google-client-secret"
export MICROSOFT_CLIENT_ID="your-microsoft-client-id"
export MICROSOFT_CLIENT_SECRET="your-microsoft-client-secret"
```

### 3. Deploy Infrastructure
```bash
# Make deployment script executable
chmod +x scripts/deploy.sh

# Run deployment
./scripts/deploy.sh deploy
```

### 4. Configure DNS
Point your domain to the load balancer IP:
```
erp.your-domain.com    A    <LOAD_BALANCER_IP>
id.your-domain.com     A    <LOAD_BALANCER_IP>
```

### 5. Access Applications
- **ERPNext**: https://erp.your-domain.com
- **Keycloak**: https://id.your-domain.com

## 📁 Project Structure

```
AgenticHR/
├── terraform/                 # Infrastructure as Code
│   ├── main.tf               # Main Terraform configuration
│   ├── variables.tf          # Variable definitions
│   └── outputs.tf            # Output values
├── kubernetes/               # Kubernetes manifests
│   ├── namespace.yaml        # Namespace definitions
│   ├── erpnext-deployment.yaml
│   ├── keycloak-deployment.yaml
│   └── ingress.yaml          # Ingress and SSL configuration
├── configs/                  # Configuration files
│   ├── erpnext-hr-config.json
│   └── keycloak-realm-config.json
├── scripts/                  # Automation scripts
│   ├── deploy.sh             # Main deployment script
│   ├── configure-erpnext-phase1.py
│   └── configure-keycloak.py
├── docs/                     # Documentation
└── README.md
```

## 🔧 Configuration

### ERPNext Configuration
The system comes pre-configured with:
- HR and Payroll modules enabled
- Standard leave types and salary components
- Workflow configurations for approvals
- OIDC integration with Keycloak

### Keycloak Configuration
- ERPNext realm with OIDC client
- Google and Microsoft identity providers
- Multi-factor authentication (TOTP + WebAuthn)
- Role-based access control
- Security policies and brute force protection

## 👥 Default Users

### ERPNext
- **Administrator**: admin123 (change after first login)

### Keycloak
- **Admin**: admin / (generated password)
- **HR Manager**: hr.manager / TalentOz@2024
- **Employee**: john.doe / Employee@2024

## 🔐 Security Features

- **Multi-Factor Authentication**: TOTP, WebAuthn, Push notifications
- **Single Sign-On**: Google OAuth 2.0, Microsoft Azure AD
- **Role-Based Access Control**: Granular permissions
- **Encryption**: TLS 1.3, encrypted storage
- **Compliance**: GDPR, SOC 2 Type II ready
- **Network Security**: Private clusters, network policies
- **Secrets Management**: Google Secret Manager

## 📊 Monitoring & Observability

- **Health Checks**: Kubernetes liveness and readiness probes
- **Logging**: Centralized logging with Cloud Logging
- **Metrics**: Prometheus metrics collection
- **Alerting**: Cloud Monitoring alerts
- **Backup**: Automated database and file backups

## 🔄 CI/CD Pipeline

The project includes GitHub Actions workflows for:
- Infrastructure deployment
- Application updates
- Security scanning
- Automated testing

## 📈 Scaling

The system is designed for horizontal scaling:
- **ERPNext**: Multiple replicas with load balancing
- **Keycloak**: StatefulSet with clustering
- **Database**: Cloud SQL with read replicas
- **Storage**: Shared NFS for file storage

## 🛡️ Backup & Recovery

- **Database**: Daily automated backups with 30-day retention
- **Files**: Filestore snapshots every 6 hours
- **Cluster**: Velero backup to GCS bucket
- **Secrets**: Encrypted backup in Secret Manager

## 🚨 Troubleshooting

### Common Issues

1. **Pod not starting**: Check resource limits and node capacity
2. **Database connection**: Verify Cloud SQL proxy configuration
3. **SSL certificate**: Ensure DNS is properly configured
4. **Authentication**: Check Keycloak realm and client configuration

### Useful Commands

```bash
# Check deployment status
./scripts/deploy.sh status

# View logs
kubectl logs -n erpnext deployment/erpnext
kubectl logs -n keycloak statefulset/keycloak

# Access ERPNext shell
kubectl exec -it -n erpnext deployment/erpnext -c erpnext -- bash

# Port forward for debugging
kubectl port-forward -n erpnext svc/erpnext-service 8000:80
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the documentation in the `docs/` folder
- Review the troubleshooting section

## 🗺️ Roadmap

### Phase 1 (Current)
- ✅ Core HR features
- ✅ Authentication and security
- ✅ Automated deployment

### Phase 2 (Next)
- 🔄 Extended HR modules
- 🔄 Advanced workflows
- 🔄 Mobile application

### Phase 3 (Future)
- 📋 AI-powered features
- 📋 Advanced analytics
- 📋 Third-party integrations

## 📞 Contact

For enterprise support and customization:
- Email: support@talentoz.com
- Website: https://talentoz.com

---

**TalentOz HCM** - Empowering organizations with intelligent HR management.

