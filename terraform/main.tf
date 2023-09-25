locals {
  # Replace all non alpha numeric characters by dashes
  sources_branch_name_sanitized = replace(var.sources_branch_name, "/[^a-zA-Z0-9]/", "-")

  tags = {
    app        = "PowerProxy"
    managed_by = "Terraform"
    sources    = "https://github.com/timoklimmer/powerproxy-aoai"
    version    = var.sources_branch_name
  }
}

data "azurerm_client_config" "current" {}

resource "azurerm_user_assigned_identity" "this" {
  location            = azurerm_resource_group.this.location
  name                = var.resource_prefix
  resource_group_name = azurerm_resource_group.this.name

  tags = local.tags
}

resource "azurerm_resource_group" "this" {
  location = var.region_id
  name     = var.resource_prefix

  tags = local.tags
}

data "azurerm_application_insights" "this" {
  name                = var.application_insights_name
  resource_group_name = azurerm_resource_group.this.name
}

resource "azurerm_role_assignment" "application_insights_metrics_publisher" {
  principal_id         = azurerm_user_assigned_identity.this.principal_id
  role_definition_name = "Monitoring Metrics Publisher"
  scope                = data.azurerm_application_insights.this.id
}

resource "azurerm_role_assignment" "log_analytics_workspace_metrics_publisher" {
  principal_id         = azurerm_user_assigned_identity.this.principal_id
  role_definition_name = "Monitoring Metrics Publisher"
  scope                = data.azurerm_application_insights.this.workspace_id
}

resource "azurerm_container_registry" "this" {
  location            = azurerm_resource_group.this.location
  name                = var.resource_prefix
  resource_group_name = azurerm_resource_group.this.name

  sku = "Basic"

  tags = local.tags
}

resource "azurerm_container_registry_task" "this" {
  name                  = "powerproxy-${local.sources_branch_name_sanitized}"
  container_registry_id = azurerm_container_registry.this.id

  platform {
    architecture = "amd64"
    os           = "Linux"
  }

  docker_step {
    context_access_token = var.github_token
    context_path         = "https://github.com/timoklimmer/powerproxy-aoai.git#${var.sources_branch_name}"
    dockerfile_path      = "Dockerfile"

    image_names = [
      "powerproxy:${local.sources_branch_name_sanitized}",
      "powerproxy:sha-{{.Run.Commit}}",
    ]
  }

  source_trigger {
    branch         = local.sources_branch_name_sanitized
    events         = ["commit", "pullrequest"]
    name           = "sources"
    repository_url = "https://github.com/timoklimmer/powerproxy-aoai"
    source_type    = "Github"

    authentication {
      token      = var.github_token
      token_type = "PAT"
    }
  }

  base_image_trigger {
    name = "base-image"
    type = "All"
  }

  tags = local.tags
}

resource "azurerm_container_registry_task_schedule_run_now" "this" {
  container_registry_task_id = azurerm_container_registry_task.this.id

  depends_on = [azurerm_container_registry_task.this]
}

resource "azurerm_role_assignment" "container_registry_pull" {
  principal_id         = azurerm_user_assigned_identity.this.principal_id
  role_definition_name = "AcrPull"
  scope                = azurerm_container_registry.this.id
}

resource "azurerm_container_app_environment" "this" {
  location            = azurerm_resource_group.this.location
  name                = var.resource_prefix
  resource_group_name = azurerm_resource_group.this.name

  log_analytics_workspace_id = data.azurerm_application_insights.this.workspace_id

  tags = local.tags
}

// TODO: Add custom scaling rules based on CPU/RAM/requests, TDB. Feature is not yet available in the Terraform provider. See: https://github.com/hashicorp/terraform-provider-azurerm/issues/21207.
resource "azurerm_container_app" "this" {
  container_app_environment_id = azurerm_container_app_environment.this.id
  name                         = "powerproxy"
  resource_group_name          = azurerm_resource_group.this.name

  revision_mode = "Multiple"

  template {
    container {
      cpu    = 0.5
      image  = "${azurerm_container_registry.this.login_server}/powerproxy:${local.sources_branch_name_sanitized}"
      memory = "1Gi"
      name   = "powerproxy"

      liveness_probe {
        initial_delay    = 5
        interval_seconds = 5
        path             = "/health/liveness"
        port             = 8000
        transport        = "HTTP"
      }

      startup_probe {
        failure_count_threshold = 10
        interval_seconds        = 5
        port                    = 8000
        transport               = "TCP"
      }

      volume_mounts {
        name = "tmp"
        path = "/tmp"
      }

      env {
        name  = "TMPDIR"
        value = "/tmp"
      }

      env {
        name        = "POWERPROXY_CONFIG_JSON"
        secret_name = "config-json"
      }
    }

    volume {
      name         = "tmp"
      storage_type = "EmptyDir"
    }
  }

  // Store as secret because raw configuration contains secrets (OpenAI at minimum)
  secret {
    name  = "config-json"
    value = jsonencode(yamldecode(file(var.config_yaml_path)))
  }

  ingress {
    external_enabled = true
    target_port      = 8000

    traffic_weight {
      label           = "latest"
      latest_revision = true
      percentage      = 100
    }
  }

  registry {
    identity = azurerm_user_assigned_identity.this.id
    server   = azurerm_container_registry.this.login_server
  }

  identity {
    identity_ids = [azurerm_user_assigned_identity.this.id]
    type         = "UserAssigned"
  }

  depends_on = [
    azurerm_container_registry_task_schedule_run_now.this,
    azurerm_role_assignment.application_insights_metrics_publisher,
    azurerm_role_assignment.container_registry_pull,
    azurerm_role_assignment.log_analytics_workspace_metrics_publisher,
  ]

  tags = local.tags
}
