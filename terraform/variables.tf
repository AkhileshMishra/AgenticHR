# TalentOz HCM - Terraform Variables

variable "project_id" {
  description = "The GCP project ID"
  type        = string
  default     = "talentoz-prod"
}

variable "region" {
  description = "The GCP region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "The GCP zone"
  type        = string
  default     = "us-central1-a"
}

variable "domain_name" {
  description = "The domain name for the application"
  type        = string
  default     = "talentoz.com"
}

variable "cluster_name" {
  description = "The name of the GKE cluster"
  type        = string
  default     = "talentoz-gke"
}

variable "db_tier" {
  description = "The machine type for Cloud SQL instance"
  type        = string
  default     = "db-n1-standard-2"
}

variable "db_disk_size" {
  description = "The disk size for Cloud SQL instance in GB"
  type        = number
  default     = 100
}

variable "redis_memory_size" {
  description = "The memory size for Redis instance in GB"
  type        = number
  default     = 5
}

variable "nfs_capacity" {
  description = "The capacity for NFS instance in GB"
  type        = number
  default     = 1024
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "enable_backup" {
  description = "Enable automated backups"
  type        = bool
  default     = true
}

variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 30
}

variable "ssl_policy" {
  description = "SSL policy for load balancer"
  type        = string
  default     = "MODERN"
}

variable "network_tier" {
  description = "Network tier for external IP addresses"
  type        = string
  default     = "PREMIUM"
}

variable "enable_private_nodes" {
  description = "Enable private nodes in GKE cluster"
  type        = bool
  default     = true
}

variable "enable_network_policy" {
  description = "Enable network policy in GKE cluster"
  type        = bool
  default     = true
}

variable "enable_workload_identity" {
  description = "Enable workload identity in GKE cluster"
  type        = bool
  default     = true
}

variable "master_ipv4_cidr_block" {
  description = "The IP range in CIDR notation for the master network"
  type        = string
  default     = "172.16.0.0/28"
}

variable "pods_ipv4_cidr_block" {
  description = "The IP range in CIDR notation for pods"
  type        = string
  default     = "10.1.0.0/16"
}

variable "services_ipv4_cidr_block" {
  description = "The IP range in CIDR notation for services"
  type        = string
  default     = "10.2.0.0/16"
}

variable "node_ipv4_cidr_block" {
  description = "The IP range in CIDR notation for nodes"
  type        = string
  default     = "10.0.0.0/16"
}

variable "authorized_networks" {
  description = "List of authorized networks for master access"
  type = list(object({
    cidr_block   = string
    display_name = string
  }))
  default = []
}

variable "labels" {
  description = "Labels to apply to resources"
  type        = map(string)
  default = {
    project     = "talentoz"
    environment = "prod"
    managed_by  = "terraform"
  }
}

variable "enable_monitoring" {
  description = "Enable monitoring and logging"
  type        = bool
  default     = true
}

variable "enable_binary_authorization" {
  description = "Enable binary authorization"
  type        = bool
  default     = false
}

variable "enable_pod_security_policy" {
  description = "Enable pod security policy"
  type        = bool
  default     = true
}

variable "maintenance_window_start_time" {
  description = "Start time for maintenance window (HH:MM format)"
  type        = string
  default     = "03:00"
}

variable "maintenance_window_duration" {
  description = "Duration of maintenance window in hours"
  type        = string
  default     = "4h"
}

variable "backup_start_time" {
  description = "Start time for database backups (HH:MM format)"
  type        = string
  default     = "03:00"
}

variable "enable_deletion_protection" {
  description = "Enable deletion protection for critical resources"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "Number of days to retain logs"
  type        = number
  default     = 30
}

variable "monitoring_notification_channels" {
  description = "List of notification channels for monitoring alerts"
  type        = list(string)
  default     = []
}

