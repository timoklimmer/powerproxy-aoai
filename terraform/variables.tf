variable "resource_prefix" {
  description = "Prefix to apply on all resources created"

  validation {
    condition     = can(regex("^[a-z][a-z0-9]{2,}$", var.resource_prefix))
    error_message = "Resource prefix must be at least 3 characters long and start with a letter."
  }
}

variable "sources_branch_name" {
  default     = "main"
  description = "Branch from which to build the application"
}

variable "region_id" {
  description = "Region name to deploy all resources"
}

variable "github_token" {
  description = "Personal Access Token (PAT) to pull sources code from GitHub"
  sensitive   = true
}

variable "config_yaml_path" {
  description = "Path to the YAML PowerProxy configuration file"
  default     = "config.yaml"
}

variable "application_insights_resource_group_name" {
  description = "Resource group name of the existing Application Insights instance"
}

variable "application_insights_name" {
  description = "Name of the existing Application Insights instance"
}