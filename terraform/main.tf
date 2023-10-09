locals {
  # Replace all non alpha numeric characters by dashes
  github_branch_name_sanitized = replace(var.github_branch_name, "/[^a-zA-Z0-9]/", "-")
  logs_table_name              = "AzureOpenAIUsage_CL"

  tags = {
    app        = "PowerProxy"
    managed_by = "Terraform"
    sources    = "https://github.com/timoklimmer/powerproxy-aoai"
    version    = var.github_branch_name
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

resource "azurerm_log_analytics_workspace" "this" {
  location            = azurerm_resource_group.this.location
  name                = var.resource_prefix
  resource_group_name = azurerm_resource_group.this.name

  retention_in_days = 30
  sku               = "PerGB2018"

  tags = local.tags
}

resource "azurerm_role_assignment" "log_analytics_workspace_metrics_publisher" {
  principal_id         = azurerm_user_assigned_identity.this.principal_id
  role_definition_name = "Monitoring Metrics Publisher"
  scope                = azurerm_log_analytics_workspace.this.id
}

resource "azurerm_application_insights" "this" {
  location            = azurerm_resource_group.this.location
  name                = var.resource_prefix
  resource_group_name = azurerm_resource_group.this.name

  application_type = "web"
  workspace_id     = azurerm_log_analytics_workspace.this.id

  tags = local.tags
}

resource "azurerm_role_assignment" "application_insights_metrics_publisher" {
  principal_id         = azurerm_user_assigned_identity.this.principal_id
  role_definition_name = "Monitoring Metrics Publisher"
  scope                = azurerm_application_insights.this.id
}

resource "azurerm_monitor_data_collection_endpoint" "logs" {
  location            = azurerm_resource_group.this.location
  name                = "${var.resource_prefix}-logs"
  resource_group_name = azurerm_resource_group.this.name

  tags = local.tags
}

// It is missing a Table (DCR mode) in the Log Analytics workspace. Feature is not yet implemented in the Terraform provider. See: https://github.com/hashicorp/terraform-provider-azurerm/issues/23359.
resource "null_resource" "logs_table" {
  triggers = {
    resource_group_name = azurerm_resource_group.this.name
    subscription_id     = data.azurerm_client_config.current.subscription_id
    table_name          = local.logs_table_name
    workspace_name      = azurerm_log_analytics_workspace.this.name
  }

  provisioner "local-exec" {
    command = "az monitor log-analytics workspace table create --yes --subscription ${self.triggers.subscription_id} --resource-group ${self.triggers.resource_group_name} --workspace-name ${self.triggers.workspace_name} --name ${self.triggers.table_name} --columns Client=string CompletionTokens=int IsStreaming=boolean OpenAIProcessingMS=real OpenAIRegion=string PromptTokens=int RequestStartMinute=string TimeGenerated=datetime TotalTokens=int"
    when    = create
  }

  provisioner "local-exec" {
    command = "az monitor log-analytics workspace table delete --yes --subscription ${self.triggers.subscription_id} --resource-group ${self.triggers.resource_group_name} --workspace-name ${self.triggers.workspace_name} --name ${self.triggers.table_name}"
    when    = destroy
  }

  depends_on = [
    azurerm_log_analytics_workspace.this,
    azurerm_resource_group.this,
    data.azurerm_client_config.current,
  ]
}

resource "azurerm_monitor_data_collection_rule" "logs" {
  location            = azurerm_resource_group.this.location
  name                = "${var.resource_prefix}-logs"
  resource_group_name = azurerm_resource_group.this.name

  data_collection_endpoint_id = azurerm_monitor_data_collection_endpoint.logs.id

  destinations {
    log_analytics {
      name                  = "Default"
      workspace_resource_id = azurerm_log_analytics_workspace.this.id
    }
  }

  data_flow {
    destinations  = ["Default"]
    output_stream = "Custom-*"
    streams       = ["Custom-${local.logs_table_name}"]
    transform_kql = "source | extend TimeGenerated = todatetime(RequestStartMinute)"
  }

  stream_declaration {
    stream_name = "Custom-${local.logs_table_name}"

    column {
      name = "Client"
      type = "string"
    }

    column {
      name = "CompletionTokens"
      type = "int"
    }

    column {
      name = "IsStreaming"
      type = "boolean"
    }

    column {
      name = "OpenAIProcessingMS"
      type = "real"
    }

    column {
      name = "OpenAIRegion"
      type = "string"
    }

    column {
      name = "PromptTokens"
      type = "int"
    }

    column {
      name = "RequestStartMinute"
      type = "string"
    }

    column {
      name = "TotalTokens"
      type = "int"
    }
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.this.id]
  }

  depends_on = [null_resource.logs_table]

  tags = local.tags
}

resource "azurerm_role_assignment" "monitor_data_collection_rule_metrics_publisher" {
  principal_id         = azurerm_user_assigned_identity.this.principal_id
  role_definition_name = "Monitoring Metrics Publisher"
  scope                = azurerm_monitor_data_collection_rule.logs.id
}

resource "azurerm_container_registry" "this" {
  location            = azurerm_resource_group.this.location
  name                = var.resource_prefix
  resource_group_name = azurerm_resource_group.this.name

  sku = "Basic"

  tags = local.tags
}

resource "azurerm_container_registry_task" "this" {
  name                  = "powerproxy-${local.github_branch_name_sanitized}"
  container_registry_id = azurerm_container_registry.this.id

  platform {
    architecture = "amd64"
    os           = "Linux"
  }

  docker_step {
    context_access_token = var.github_token
    context_path         = "${var.github_clone_url}#${var.github_branch_name}"
    dockerfile_path      = "Dockerfile"

    image_names = [
      "powerproxy:${local.github_branch_name_sanitized}",
      "powerproxy:sha-{{.Run.Commit}}",
    ]
  }

  source_trigger {
    branch         = local.github_branch_name_sanitized
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

  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id

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
      image  = "${azurerm_container_registry.this.login_server}/powerproxy:${local.github_branch_name_sanitized}"
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
    name = "config-json"
    value = jsonencode(merge(
      yamldecode(file(var.config_yaml_path)),
      {
        plugins = [
          {
            name                    = "LogUsageToLogAnalytics",
            data_collection_rule_id = azurerm_monitor_data_collection_rule.logs.name
            log_ingestion_endpoint  = azurerm_monitor_data_collection_endpoint.logs.logs_ingestion_endpoint
            stream_name             = [for i in azurerm_monitor_data_collection_rule.logs.stream_declaration : i][0].stream_name
          }
        ]
      },
    ))
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
    azurerm_role_assignment.monitor_data_collection_rule_metrics_publisher,
  ]

  tags = local.tags
}
