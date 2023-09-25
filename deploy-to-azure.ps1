# Deploys a PowerProxy for Azure OpenAI to Azure

#  - either run this as complete script or use VS.Code PowerShell extension to run individual code
#    blocks (by selecting code and pressing F8)
#  - before running the script, make sure that you have a proper config file at
#    config/config.azure.yaml
#  - PowerShell version should be 7+.
#  - Will be migrated to Terraform in future.

$ErrorActionPreference = "Stop"

# register required namespaces in subscription if not done yet (required only once per subscription)
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights
# ensure that the Azure CLI has the required extensions installed (required only once per machine)
az extension add -n containerapp
az extension add -n monitor-control-service

# configuration
$CONFIG_STRING = (python config/to_json_string.py --yaml-file config/config.azure.yaml)
$CONFIG = $CONFIG_STRING | ConvertFrom-Json
$RESOURCE_GROUP = $CONFIG.resource_group
$REGION = $CONFIG.region
$UNIQUE_PREFIX = $CONFIG.unique_prefix
$ACR_REGISTRY_NAME = "${UNIQUE_PREFIX}powerproxyaoai"
$ACR_SKU = "Basic"
$ACR_ADMIN_ENABLED = $True
$CONTAINER_NAME = "powerproxyaoai"
$CONTAINER_TAG = "latest"
$CONTAINER_APP_NAME = "powerproxyaoai"
$CONTAINER_APP_ENVIRONMENT = "powerproxyaoai"
$IMAGE = "$ACR_REGISTRY_NAME.azurecr.io/${CONTAINER_NAME}:$CONTAINER_TAG"
$LOG_ANALYTICS_WORKSPACE_NAME = "powerproxyaoai"
$LOG_ANALYTICS_USAGE_TABLE_NAME = "AzureOpenAIUsage_CL"  # note: Log Analytics requires custom table names to end with "_CL"
$DATA_COLLECTION_ENDPOINT_NAME = "powerproxyaoai"

# create resource group
Write-Host "Creating resource group..."
az group create --name $RESOURCE_GROUP --location $REGION

# create container registry
Write-Host "Creating container registry..."
az acr create `
  --name $ACR_REGISTRY_NAME `
  --resource-group $RESOURCE_GROUP `
  --sku $ACR_SKU `
  --admin-enabled $ACR_ADMIN_ENABLED

# build container (in Azure)
Write-Host "Building container..."
az acr build `
  -t $IMAGE `
  -r $ACR_REGISTRY_NAME .

# create log analytics workspace, tables, data collection endpoint and rules
# workspace
# notes: uses default retention time of workspace, change retention time if needed
Write-Host "Creating Log Analytics workspace..."
az monitor log-analytics workspace create `
  --resource-group $RESOURCE_GROUP `
  --workspace-name $LOG_ANALYTICS_WORKSPACE_NAME
$LOG_ANALYTICS_WORKSPACE_ID = ( `
  az monitor log-analytics workspace show `
    --name $LOG_ANALYTICS_WORKSPACE_NAME `
    --resource-group $RESOURCE_GROUP `
    --query id `
    -o tsv `
)
$LOG_ANALYTICS_WORKSPACE_CUSTOMER_ID = ( `
  az monitor log-analytics workspace show `
    --name $LOG_ANALYTICS_WORKSPACE_NAME `
    --resource-group $RESOURCE_GROUP `
    --query customerId `
    -o tsv `
)
$LOG_ANALYTICS_WORKSPACE_KEY = ( `
  az monitor log-analytics workspace get-shared-keys `
    --resource-group $RESOURCE_GROUP `
    --workspace-name $LOG_ANALYTICS_WORKSPACE_NAME `
    --query primarySharedKey `
    -o tsv
)

# tables
# TODO: complete, deployment via Azure CLI is not working properly at the moment. therefore, a
# manual configuration is required for now
# see: https://learn.microsoft.com/en-us/azure/azure-monitor/logs/tutorial-logs-ingestion-portal
Write-Host "Creating components required to log usage data in Log Analytics..."
Write-Host "Please create a Data Collection Endpoint (DCE), Custom Log Analytics table '$LOG_ANALYTICS_USAGE_TABLE_NAME' and a Data Collection Rule (DCR) manually with the infos given in the contained readme."
Read-Host "Press ENTER to confirm the completion"

# az monitor log-analytics workspace table create `
#   --resource-group $RESOURCE_GROUP `
#   --workspace-name $LOG_ANALYTICS_WORKSPACE_NAME `
#   --name $LOG_ANALYTICS_USAGE_TABLE_NAME `
#   --columns `
#     TimeGenerated=datetime `
#     RequestStartMinute=string `
#     Client=string `
#     IsStreaming=boolean `
#     PromptTokens=int `
#     CompletionTokens=int `
#     TotalTokens=int `
#     OpenAIProcessingMS=real `
#     OpenAIRegion=string
# # data collection endpoint
# $DATA_COLLECTION_ENDPOINT_ID = (az monitor data-collection endpoint create `
#   --name $DATA_COLLECTION_ENDPOINT_NAME `
#   --resource-group $RESOURCE_GROUP `
#   --location $REGION `
#   --public-network-access "enabled" `
#   --query immutableId `
#   --output tsv `
# )
# $LOGS_INGESTION_ENDPOINT = (az monitor data-collection endpoint show `
#   --id $DATA_COLLECTION_ENDPOINT_ID `
#   --query logsIngestion.endpoint `
#   --output tsv `
# )
# # data collection rule
# $rule_file_path = "rule-file.json"
# Try {
#   Copy-Item -Path "rule-file.template.json" -Destination $rule_file_path
#   ((Get-Content $rule_file_path) -replace "##tableName##", $LOG_ANALYTICS_USAGE_TABLE_NAME) `
#     | Set-Content -Path $rule_file_path
#   ((Get-Content $rule_file_path) -replace "##workspaceResourceId##", $LOG_ANALYTICS_WORKSPACE_ID) `
#     | Set-Content -Path $rule_file_path
#   ((Get-Content $rule_file_path) -replace "##dataCollectionEndpointId##", $DATA_COLLECTION_ENDPOINT_ID) `
#     | Set-Content -Path $rule_file_path
#   $DCR_IMMUTABLE_ID = (az monitor data-collection rule create `
#     --name $LOG_ANALYTICS_USAGE_TABLE_NAME `
#     --resource-group $RESOURCE_GROUP `
#     --location $REGION `
#     --rule-file $rule_file_path `
#     --query immutableId `
#     --output tsv
#   )
# }
# Finally {
#   if (Test-Path $rule_file_path) {
#     Remove-Item $rule_file_path
#   }
# }
# # give permissions
# # TODO: complete

# deploy container to Azure Container Apps
# environment
az containerapp env create `
  --name $CONTAINER_APP_ENVIRONMENT `
  --resource-group $RESOURCE_GROUP `
  --location $REGION `
  --logs-destination log-analytics `
  --logs-workspace-id $LOG_ANALYTICS_WORKSPACE_CUSTOMER_ID `
  --logs-workspace-key $LOG_ANALYTICS_WORKSPACE_KEY
# app incl. secrets and env vars
# TODO: move config to Azure Key Vault
az containerapp up `
  --name $CONTAINER_APP_NAME `
  --resource-group $RESOURCE_GROUP `
  --location $REGION `
  --environment $CONTAINER_APP_ENVIRONMENT `
  --image $IMAGE `
  --target-port 8000 `
  --ingress external `
  --query properties.configuration.ingress.fqdn `
  --logs-workspace-id $LOG_ANALYTICS_WORKSPACE_CUSTOMER_ID `
  --logs-workspace-key $LOG_ANALYTICS_WORKSPACE_KEY
# secrets and env vars
az containerapp secret set `
  --name $CONTAINER_APP_NAME `
  --resource-group $RESOURCE_GROUP `
  --secrets `
    "config-string=(not set)"
az containerapp update `
  --name $CONTAINER_APP_NAME `
  --resource-group $RESOURCE_GROUP `
  --set-env-vars `
    "POWERPROXY_CONFIG_STRING=secretref:config-string"

# set env variable POWERPROXY_CONFIG_STRING manually to content of $CONFIG_STRING
# notes: - this needs to be done manually as there is an issue with the Azure CLI currently
#        - don't forget to restart to bring config changes into effect
Write-Host "Please update the config-string secret in the Container App manually to contain '$CONFIG_STRING'."
Write-Host "Note: this will be automated in future but needs an issue with the Azure CLI fixed first."
Read-Host "Press ENTER to confirm the completion."
# restart active revisions to bring secrects and env vars into effect
Write-Host "Restarting Container App to bring new secret value into effect..."
az containerapp revision list `
  --name $CONTAINER_APP_NAME `
  --resource-group $RESOURCE_GROUP `
  --query "[?properties.active].name" -o tsv | ForEach-Object {
  az containerapp revision restart `
    --name $CONTAINER_APP_NAME `
    --resource-group $RESOURCE_GROUP `
    --revision $_
}

# # cleanup
# # explictly delete the Log Analytics workspace to delete contained data
# az monitor log-analytics workspace delete `
#   --resource-group $RESOURCE_GROUP `
#   --workspace-name $LOG_ANALYTICS_WORKSPACE_NAME `
#   --force `
#   -y
# # then delete the entire resource group containing all the rest
# az group delete -n $RESOURCE_GROUP -y