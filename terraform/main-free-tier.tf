# TalentOz HCM - Free Tier Optimized
# ERPNext HR + Keycloak on Google Cloud Platform (Free Trial Compatible)

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Variables
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region (use us-central1 for free tier)"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP Zone"
  type        = string
  default     = "us-central1-a"
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
}

# Provider configuration
provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "container.googleapis.com",
    "compute.googleapis.com",
    "secretmanager.googleapis.com"
  ])

  service = each.value
  project = var.project_id

  disable_dependent_services = true
}

# VPC Network
resource "google_compute_network" "vpc" {
  name                    = "talentoz-vpc"
  auto_create_subnetworks = false
  depends_on              = [google_project_service.required_apis]
}

# Subnet for GKE
resource "google_compute_subnetwork" "gke_subnet" {
  name          = "talentoz-gke-subnet"
  ip_cidr_range = "10.0.0.0/16"
  region        = var.region
  network       = google_compute_network.vpc.id

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.1.0.0/16"
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.2.0.0/16"
  }
}

# Service Account for applications
resource "google_service_account" "app_sa" {
  account_id   = "talentoz-app-sa"
  display_name = "TalentOz Application Service Account"
  depends_on   = [google_project_service.required_apis]
}

# IAM bindings
resource "google_project_iam_member" "app_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.app_sa.email}"
}

# GKE Standard Cluster (Free tier compatible)
resource "google_container_cluster" "primary" {
  name     = "talentoz-gke"
  location = var.zone  # Zonal cluster for cost optimization

  # Remove default node pool
  remove_default_node_pool = true
  initial_node_count       = 1

  network    = google_compute_network.vpc.name
  subnetwork = google_compute_subnetwork.gke_subnet.name

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  # Workload Identity
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  # Network policy
  network_policy {
    enabled = true
  }

  # Cost optimization settings
  cluster_autoscaling {
    enabled = false
  }

  depends_on = [
    google_project_service.required_apis,
    google_compute_subnetwork.gke_subnet
  ]
}

# Node pool with free tier compatible settings
resource "google_container_node_pool" "primary_nodes" {
  name       = "primary-node-pool"
  location   = var.zone
  cluster    = google_container_cluster.primary.name
  node_count = 2  # Minimum for HA

  node_config {
    preemptible  = true  # 80% cost reduction
    machine_type = "e2-small"  # Smallest machine type

    # Disk settings
    disk_size_gb = 20  # Minimum disk size
    disk_type    = "pd-standard"  # Cheaper than SSD

    # Service account
    service_account = google_service_account.app_sa.email
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    # Workload Identity
    workload_metadata_config {
      mode = "GKE_METADATA"
    }

    # Resource limits for cost control
    metadata = {
      disable-legacy-endpoints = "true"
    }
  }

  # Autoscaling settings
  autoscaling {
    min_node_count = 1
    max_node_count = 3
  }

  # Node management
  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

# Compute Engine VM for database (free tier f1-micro)
resource "google_compute_instance" "database_vm" {
  name         = "talentoz-db-vm"
  machine_type = "f1-micro"  # Free tier eligible
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2004-lts"
      size  = 10  # 10GB free tier
      type  = "pd-standard"
    }
  }

  network_interface {
    network    = google_compute_network.vpc.name
    subnetwork = google_compute_subnetwork.gke_subnet.name
    
    # No external IP to save costs
    # access_config {}
  }

  # Startup script to install MySQL and Redis
  metadata_startup_script = <<-EOF
    #!/bin/bash
    apt-get update
    
    # Install MySQL
    export DEBIAN_FRONTEND=noninteractive
    apt-get install -y mysql-server redis-server
    
    # Configure MySQL
    mysql -e "CREATE DATABASE erpnext;"
    mysql -e "CREATE DATABASE keycloak;"
    mysql -e "CREATE USER 'erpnext'@'%' IDENTIFIED BY '${random_password.erpnext_db_password.result}';"
    mysql -e "CREATE USER 'keycloak'@'%' IDENTIFIED BY '${random_password.keycloak_db_password.result}';"
    mysql -e "GRANT ALL PRIVILEGES ON erpnext.* TO 'erpnext'@'%';"
    mysql -e "GRANT ALL PRIVILEGES ON keycloak.* TO 'keycloak'@'%';"
    mysql -e "FLUSH PRIVILEGES;"
    
    # Configure MySQL for remote connections
    sed -i 's/bind-address.*/bind-address = 0.0.0.0/' /etc/mysql/mysql.conf.d/mysqld.cnf
    systemctl restart mysql
    
    # Configure Redis
    sed -i 's/bind 127.0.0.1/bind 0.0.0.0/' /etc/redis/redis.conf
    echo "requirepass ${random_password.redis_password.result}" >> /etc/redis/redis.conf
    systemctl restart redis-server
    
    # Enable services
    systemctl enable mysql redis-server
  EOF

  service_account {
    email  = google_service_account.app_sa.email
    scopes = ["cloud-platform"]
  }

  tags = ["database-server"]

  depends_on = [google_project_service.required_apis]
}

# Firewall rule for database access from GKE
resource "google_compute_firewall" "database_access" {
  name    = "allow-database-access"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["3306", "6379"]  # MySQL and Redis
  }

  source_ranges = ["10.0.0.0/16", "10.1.0.0/16"]  # GKE subnets
  target_tags   = ["database-server"]
}

# Random passwords
resource "random_password" "erpnext_db_password" {
  length  = 16
  special = false  # Avoid special chars for simplicity
}

resource "random_password" "keycloak_db_password" {
  length  = 16
  special = false
}

resource "random_password" "keycloak_admin_password" {
  length  = 16
  special = false
}

resource "random_password" "redis_password" {
  length  = 16
  special = false
}

# Secret Manager secrets (minimal set)
resource "google_secret_manager_secret" "secrets" {
  for_each = toset([
    "keycloak-db-password",
    "keycloak-admin-password", 
    "erpnext-db-password",
    "redis-password"
  ])

  secret_id = each.value

  replication {
    auto {}
  }

  depends_on = [google_project_service.required_apis]
}

# Secret versions
resource "google_secret_manager_secret_version" "keycloak_db_password" {
  secret      = google_secret_manager_secret.secrets["keycloak-db-password"].id
  secret_data = random_password.keycloak_db_password.result
}

resource "google_secret_manager_secret_version" "keycloak_admin_password" {
  secret      = google_secret_manager_secret.secrets["keycloak-admin-password"].id
  secret_data = random_password.keycloak_admin_password.result
}

resource "google_secret_manager_secret_version" "erpnext_db_password" {
  secret      = google_secret_manager_secret.secrets["erpnext-db-password"].id
  secret_data = random_password.erpnext_db_password.result
}

resource "google_secret_manager_secret_version" "redis_password" {
  secret      = google_secret_manager_secret.secrets["redis-password"].id
  secret_data = random_password.redis_password.result
}

# Static IP for Load Balancer
resource "google_compute_global_address" "lb_ip" {
  name = "talentoz-lb-ip"
}

# Outputs
output "cluster_name" {
  value = google_container_cluster.primary.name
}

output "cluster_location" {
  value = google_container_cluster.primary.location
}

output "database_vm_internal_ip" {
  value = google_compute_instance.database_vm.network_interface[0].network_ip
}

output "load_balancer_ip" {
  value = google_compute_global_address.lb_ip.address
}

output "mysql_host" {
  value = google_compute_instance.database_vm.network_interface[0].network_ip
}

output "redis_host" {
  value = google_compute_instance.database_vm.network_interface[0].network_ip
}

# Cost estimation output
output "estimated_monthly_cost" {
  value = "Approximately $15-25 USD/month (within free trial credits)"
}

