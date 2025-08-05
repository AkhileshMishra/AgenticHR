# TalentOz HCM - GCP Infrastructure
# ERPNext HR + Keycloak on Google Cloud Platform

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }
}

# Variables
variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "talentoz-prod"
}

variable "region" {
  description = "GCP Region"
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
  default     = "talentoz.com"
}

# Provider configuration
provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "container.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "compute.googleapis.com",
    "dns.googleapis.com",
    "redis.googleapis.com",
    "file.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com"
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

# Cloud NAT for private nodes
resource "google_compute_router" "router" {
  name    = "talentoz-router"
  region  = var.region
  network = google_compute_network.vpc.id
}

resource "google_compute_router_nat" "nat" {
  name                               = "talentoz-nat"
  router                             = google_compute_router.router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# Service Accounts
resource "google_service_account" "erpnext_sa" {
  account_id   = "erpnext-sa"
  display_name = "ERPNext Service Account"
  depends_on   = [google_project_service.required_apis]
}

resource "google_service_account" "keycloak_sa" {
  account_id   = "keycloak-sa"
  display_name = "Keycloak Service Account"
  depends_on   = [google_project_service.required_apis]
}

# IAM bindings for service accounts
resource "google_project_iam_member" "erpnext_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.erpnext_sa.email}"
}

resource "google_project_iam_member" "erpnext_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.erpnext_sa.email}"
}

resource "google_project_iam_member" "keycloak_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.keycloak_sa.email}"
}

# GKE Autopilot Cluster
resource "google_container_cluster" "primary" {
  name     = "talentoz-gke"
  location = var.region

  # Autopilot cluster
  enable_autopilot = true

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

  # Private cluster configuration
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }

  # Network policy
  network_policy {
    enabled = true
  }

  depends_on = [
    google_project_service.required_apis,
    google_compute_subnetwork.gke_subnet
  ]
}

# Cloud SQL Instance
resource "google_sql_database_instance" "main" {
  name             = "talentoz-db"
  database_version = "MYSQL_8_0"
  region           = var.region

  settings {
    tier              = "db-n1-standard-2"
    availability_type = "REGIONAL"
    disk_size         = 100
    disk_type         = "PD_SSD"

    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = true
      backup_retention_settings {
        retained_backups = 30
      }
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.id
      require_ssl     = true
    }

    database_flags {
      name  = "innodb_buffer_pool_size"
      value = "1073741824"  # 1GB
    }
  }

  deletion_protection = false

  depends_on = [
    google_project_service.required_apis,
    google_service_networking_connection.private_vpc_connection
  ]
}

# Private VPC connection for Cloud SQL
resource "google_compute_global_address" "private_ip_address" {
  name          = "private-ip-address"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
}

# Cloud SQL Databases
resource "google_sql_database" "erpnext_db" {
  name     = "erpnext"
  instance = google_sql_database_instance.main.name
}

resource "google_sql_database" "keycloak_db" {
  name     = "keycloak"
  instance = google_sql_database_instance.main.name
}

# Cloud SQL Users
resource "google_sql_user" "erpnext_user" {
  name     = "erpnext"
  instance = google_sql_database_instance.main.name
  password = random_password.erpnext_db_password.result
}

resource "google_sql_user" "keycloak_user" {
  name     = "keycloak"
  instance = google_sql_database_instance.main.name
  password = random_password.keycloak_db_password.result
}

# Random passwords
resource "random_password" "erpnext_db_password" {
  length  = 32
  special = true
}

resource "random_password" "keycloak_db_password" {
  length  = 32
  special = true
}

resource "random_password" "keycloak_admin_password" {
  length  = 32
  special = true
}

resource "random_password" "erpnext_secret_key" {
  length  = 64
  special = true
}

resource "random_password" "redis_password" {
  length  = 32
  special = true
}

# Memorystore Redis
resource "google_redis_instance" "cache" {
  name           = "talentoz-redis"
  tier           = "BASIC"
  memory_size_gb = 5
  region         = var.region

  authorized_network = google_compute_network.vpc.id
  auth_enabled       = true
  auth_string        = random_password.redis_password.result

  depends_on = [google_project_service.required_apis]
}

# Cloud Filestore
resource "google_filestore_instance" "nfs" {
  name     = "talentoz-nfs"
  location = var.zone
  tier     = "BASIC_HDD"

  file_shares {
    capacity_gb = 1024
    name        = "erpnext_assets"
  }

  networks {
    network = google_compute_network.vpc.name
    modes   = ["MODE_IPV4"]
  }

  depends_on = [google_project_service.required_apis]
}

# Secret Manager secrets
resource "google_secret_manager_secret" "secrets" {
  for_each = toset([
    "keycloak-db-password",
    "keycloak-admin-password",
    "erpnext-db-password",
    "erpnext-secret-key",
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

resource "google_secret_manager_secret_version" "erpnext_secret_key" {
  secret      = google_secret_manager_secret.secrets["erpnext-secret-key"].id
  secret_data = random_password.erpnext_secret_key.result
}

resource "google_secret_manager_secret_version" "redis_password" {
  secret      = google_secret_manager_secret.secrets["redis-password"].id
  secret_data = random_password.redis_password.result
}

# Artifact Registry
resource "google_artifact_registry_repository" "erpnext" {
  location      = var.region
  repository_id = "erpnext"
  description   = "ERPNext Docker images"
  format        = "DOCKER"

  depends_on = [google_project_service.required_apis]
}

# Cloud DNS Zone
resource "google_dns_managed_zone" "main" {
  name     = "talentoz-zone"
  dns_name = "${var.domain_name}."

  depends_on = [google_project_service.required_apis]
}

# Static IP for Load Balancer
resource "google_compute_global_address" "lb_ip" {
  name = "talentoz-lb-ip"
}

# DNS Records
resource "google_dns_record_set" "erp" {
  name = "erp.${google_dns_managed_zone.main.dns_name}"
  type = "A"
  ttl  = 300

  managed_zone = google_dns_managed_zone.main.name

  rrdatas = [google_compute_global_address.lb_ip.address]
}

resource "google_dns_record_set" "id" {
  name = "id.${google_dns_managed_zone.main.dns_name}"
  type = "A"
  ttl  = 300

  managed_zone = google_dns_managed_zone.main.name

  rrdatas = [google_compute_global_address.lb_ip.address]
}

# Outputs
output "cluster_name" {
  value = google_container_cluster.primary.name
}

output "cluster_location" {
  value = google_container_cluster.primary.location
}

output "db_instance_connection_name" {
  value = google_sql_database_instance.main.connection_name
}

output "redis_host" {
  value = google_redis_instance.cache.host
}

output "nfs_ip" {
  value = google_filestore_instance.nfs.networks[0].ip_addresses[0]
}

output "load_balancer_ip" {
  value = google_compute_global_address.lb_ip.address
}

output "dns_name_servers" {
  value = google_dns_managed_zone.main.name_servers
}

