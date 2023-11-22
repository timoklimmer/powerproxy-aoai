variable "resource_prefix" {
  description = "Prefix to apply on all resources created"

  validation {
    condition     = can(regex("^[a-z][a-z0-9]{2,}$", var.resource_prefix))
    error_message = "Resource prefix must be at least 3 characters long and start with a letter."
  }
}

variable "github_branch_name" {
  default     = "main"
  description = "Branch from which to build the application"
}

variable "region_id" {
  description = "Region name to deploy all resources"
}

variable "github_clone_url" {
  default     = "https://github.com/timoklimmer/powerproxy-aoai.git"
  description = "Git URL to pull sources code from GitHub"

  validation {
    condition     = can(regex("^https://.*\\.git$", var.github_clone_url))
    error_message = "Git URL must be a valid HTTPS URL ending with \".git\"."
  }
}

variable "config_yaml_path" {
  default     = "config.yaml"
  description = "Path to the YAML PowerProxy configuration file"
}
