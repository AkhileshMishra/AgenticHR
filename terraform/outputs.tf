# TalentOz HCM - Terraform Outputs

output "project_id" {
  description = "The GCP project ID"
  value       = var.project_id
}

output "region" {
  description = "The GCP region"
  value       = var.region
}

output "zone" {
  description = "The GCP zone"
  value       = var.zone
}

# Network outputs
output "vpc_name" {
  description = "The name of the VPC network"
  value       = google_compute_network.vpc.name
}

output "vpc_id" {
  description = "The ID of the VPC network"
  value       = google_compute_network.vpc.id
}

output "subnet_name" {
  description = "The name of the GKE subnet"
  value       = google_compute_subnetwork.gke_subnet.name
}

output "subnet_cidr" {
  description = "The CIDR range of the GKE subnet"
  value       = google_compute_subnetwork.gke_subnet.ip_cidr_range
}

# GKE outputs
output "cluster_name" {
  description = "The name of the GKE cluster"
  value       = google_container_cluster.primary.name
}

output "cluster_location" {
  description = "The location of the GKE cluster"
  value       = google_container_cluster.primary.location
}

output "cluster_endpoint" {
  description = "The endpoint of the GKE cluster"
  value       = google_container_cluster.primary.endpoint
  sensitive   = true
}

output "cluster_ca_certificate" {
  description = "The CA certificate of the GKE cluster"
  value       = google_container_cluster.primary.master_auth[0].cluster_ca_certificate
  sensitive   = true
}

# Database outputs
output "db_instance_name" {
  description = "The name of the Cloud SQL instance"
  value       = google_sql_database_instance.main.name
}

output "db_instance_connection_name" {
  description = "The connection name of the Cloud SQL instance"
  value       = google_sql_database_instance.main.connection_name
}

output "db_instance_private_ip" {
  description = "The private IP address of the Cloud SQL instance"
  value       = google_sql_database_instance.main.private_ip_address
}

output "erpnext_db_name" {
  description = "The name of the ERPNext database"
  value       = google_sql_database.erpnext_db.name
}

output "keycloak_db_name" {
  description = "The name of the Keycloak database"
  value       = google_sql_database.keycloak_db.name
}

# Redis outputs
output "redis_instance_name" {
  description = "The name of the Redis instance"
  value       = google_redis_instance.cache.name
}

output "redis_host" {
  description = "The host of the Redis instance"
  value       = google_redis_instance.cache.host
}

output "redis_port" {
  description = "The port of the Redis instance"
  value       = google_redis_instance.cache.port
}

# NFS outputs
output "nfs_instance_name" {
  description = "The name of the NFS instance"
  value       = google_filestore_instance.nfs.name
}

output "nfs_ip" {
  description = "The IP address of the NFS instance"
  value       = google_filestore_instance.nfs.networks[0].ip_addresses[0]
}

output "nfs_share_name" {
  description = "The name of the NFS share"
  value       = google_filestore_instance.nfs.file_shares[0].name
}

# Service Account outputs
output "erpnext_service_account_email" {
  description = "The email of the ERPNext service account"
  value       = google_service_account.erpnext_sa.email
}

output "keycloak_service_account_email" {
  description = "The email of the Keycloak service account"
  value       = google_service_account.keycloak_sa.email
}

# DNS outputs
output "dns_zone_name" {
  description = "The name of the DNS zone"
  value       = google_dns_managed_zone.main.name
}

output "dns_zone_dns_name" {
  description = "The DNS name of the zone"
  value       = google_dns_managed_zone.main.dns_name
}

output "dns_name_servers" {
  description = "The name servers for the DNS zone"
  value       = google_dns_managed_zone.main.name_servers
}

# Load Balancer outputs
output "load_balancer_ip" {
  description = "The IP address of the load balancer"
  value       = google_compute_global_address.lb_ip.address
}

output "erp_url" {
  description = "The URL for ERPNext"
  value       = "https://erp.${var.domain_name}"
}

output "keycloak_url" {
  description = "The URL for Keycloak"
  value       = "https://id.${var.domain_name}"
}

# Artifact Registry outputs
output "artifact_registry_repository" {
  description = "The name of the Artifact Registry repository"
  value       = google_artifact_registry_repository.erpnext.name
}

output "artifact_registry_location" {
  description = "The location of the Artifact Registry repository"
  value       = google_artifact_registry_repository.erpnext.location
}

# Secret Manager outputs
output "secret_names" {
  description = "The names of the secrets in Secret Manager"
  value = [
    for secret in google_secret_manager_secret.secrets : secret.secret_id
  ]
}

# Connection information for kubectl
output "kubectl_config_command" {
  description = "Command to configure kubectl"
  value       = "gcloud container clusters get-credentials ${google_container_cluster.primary.name} --region ${google_container_cluster.primary.location} --project ${var.project_id}"
}

# Docker registry configuration
output "docker_registry_hostname" {
  description = "Docker registry hostname for pushing images"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.erpnext.repository_id}"
}

# Database connection strings (for reference)
output "erpnext_db_connection_info" {
  description = "ERPNext database connection information"
  value = {
    host     = google_sql_database_instance.main.private_ip_address
    database = google_sql_database.erpnext_db.name
    username = google_sql_user.erpnext_user.name
  }
  sensitive = true
}

output "keycloak_db_connection_info" {
  description = "Keycloak database connection information"
  value = {
    host     = google_sql_database_instance.main.private_ip_address
    database = google_sql_database.keycloak_db.name
    username = google_sql_user.keycloak_user.name
  }
  sensitive = true
}

# Deployment information
output "deployment_info" {
  description = "Key deployment information"
  value = {
    cluster_name     = google_container_cluster.primary.name
    cluster_location = google_container_cluster.primary.location
    erp_url         = "https://erp.${var.domain_name}"
    keycloak_url    = "https://id.${var.domain_name}"
    load_balancer_ip = google_compute_global_address.lb_ip.address
  }
}

