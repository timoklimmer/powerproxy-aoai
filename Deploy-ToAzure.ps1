<#
.SYNOPSIS
Deploys a PowerProxy for Azure OpenAI instance to Azure.

.DESCRIPTION
Creates several resources in an Azure resource group and deploys PowerProxy as a Container App,
based on the given configuration file.

.PARAMETER ConfigFile
Path to the config file to use.

.EXAMPLE
PS> .\Deploy-To-Azure.ps1 -ConfigFile config/config.azure.yaml

Deploys PowerProxy using the config file at "config/config.azure.yaml".

.LINK
GitHub repo: https://github.com/timoklimmer/powerproxy-aoai

.NOTES
There is an example config file at 'config/config.example.yaml'. You can use this file as starting
point for creating your own file.

If you want to run the deployment file step-by-step, you can use the PowerShell extension in VS.Code
and run individual code blocks by selecting them and pressing F8.

PowerShell version should be 7+. Also make sure your Azure CLI installation is up-to-date.
#>
param(
  [Parameter(mandatory=$true)]
  [string] $ConfigFile
)

#---------------------------------------[Initialisation]--------------------------------------------

$ErrorActionPreference = "Stop"

if(-Not (Test-Path $ConfigFile)) {
  throw "The given config file does not exist. Ensure that you pass a valid path to a valid config file."
}

Write-Host "--------------------------------" -ForegroundColor Blue
Write-Host "Deploying PowerProxy to Azure..." -ForegroundColor Blue
Write-Host "--------------------------------" -ForegroundColor Blue

# register required namespaces in subscription if not done yet (required only once per subscription)
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights
# ensure that the Azure CLI has the required extensions installed (required only once per machine)
az extension add -n monitor-control-service

# configuration
$CONFIG_YAML_STRING = (Get-Content -Path $ConfigFile -Raw)
$CONFIG = (python config/to_json_string.py --yaml-file $ConfigFile) | ConvertFrom-Json
$SUBSCRIPTION_ID = $CONFIG.azure_subscription_id
$RESOURCE_GROUP = $CONFIG.resource_group
$REGION = $CONFIG.region
$UNIQUE_PREFIX = $CONFIG.unique_prefix
$KEY_VAULT_NAME = "${UNIQUE_PREFIX}powerproxyaoai"
$REDIS_CACHE_NAME = "${UNIQUE_PREFIX}powerproxyaoai"
$ACR_REGISTRY_NAME = "${UNIQUE_PREFIX}powerproxyaoai"
$ACR_SKU = "Basic"
$ACR_ADMIN_ENABLED = $True
$CONTAINER_NAME = "powerproxyaoai"
$CONTAINER_TAG = "latest"
$CONTAINER_APP_NAME = "powerproxyaoai"
$CONTAINER_APP_ENVIRONMENT = "powerproxyaoai"
$IMAGE = "$ACR_REGISTRY_NAME.azurecr.io/${CONTAINER_NAME}:$CONTAINER_TAG"
$LOG_ANALYTICS_WORKSPACE_NAME = "${UNIQUE_PREFIX}powerproxyaoai"
$LOG_ANALYTICS_AOAIUSAGE_TABLE_RETENTION_TIME = 90
$DATA_COLLECTION_ENDPOINT_NAME = "${UNIQUE_PREFIX}powerproxyaoai"
$USER_MANAGED_IDENTITY_NAME = "${UNIQUE_PREFIX}powerproxyaoai"

# set subscription if set
if ($NULL -ne $SUBSCRIPTION_ID) {
  az account set -s $SUBSCRIPTION_ID
}

#--------------------------------------[Create assets]----------------------------------------------

# create resource group
Write-Host "Creating resource group..." -ForegroundColor Blue
az group create --name $RESOURCE_GROUP --location $REGION

# create user-assigned managed identity
Write-Host "Creating user-assigned managed identity..." -ForegroundColor Blue
az identity create --name $USER_MANAGED_IDENTITY_NAME --resource-group $RESOURCE_GROUP
$USER_MANAGED_IDENTITY_ID = (az identity show `
  --name $USER_MANAGED_IDENTITY_NAME `
  --resource-group $RESOURCE_GROUP `
  --query id `
  -o tsv
)
$USER_MANAGED_IDENTITY_PRINCIPAL_ID = (az identity show `
  --name $USER_MANAGED_IDENTITY_NAME `
  --resource-group $RESOURCE_GROUP `
  --query principalId `
  -o tsv
)
$USER_MANAGED_IDENTITY_CLIENT_ID = (az identity show `
  --name $USER_MANAGED_IDENTITY_NAME `
  --resource-group $RESOURCE_GROUP `
  --query clientId `
  -o tsv
)

# create key vault (deleting/purging if pre-exists)
Write-Host "Creating Key Vault..." -ForegroundColor Blue
Write-Host "Checking if Key Vault pre-exists..." -ForegroundColor Blue
if ($(az keyvault list --query [?name==``$KEY_VAULT_NAME``] -g $RESOURCE_GROUP -o tsv)) {
  Write-Host "Deleting pre-existing Key Vault..." -ForegroundColor Blue
  az keyvault delete --name $KEY_VAULT_NAME -g $RESOURCE_GROUP
  Write-Host "Waiting for Key Vault to be deleted..." -ForegroundColor Blue
  az keyvault wait --name $KEY_VAULT_NAME --deleted -g $RESOURCE_GROUP
}
Write-Host "Checking if Key Vault needs to be purged..." -ForegroundColor Blue
if ($(az keyvault list-deleted --query [?name==``$KEY_VAULT_NAME``] -o tsv)) {
  Write-Host "Purging Key Vault..." -ForegroundColor Blue
  az keyvault purge --name $KEY_VAULT_NAME --location $REGION
  Start-Sleep -Seconds 30
}
Write-Host "Creating Key Vault service..." -ForegroundColor Blue
az keyvault create `
  --name $KEY_VAULT_NAME `
  --resource-group $RESOURCE_GROUP `
  --location $REGION
Write-Host "Waiting for Key Vault creation to complete..." -ForegroundColor Blue
az keyvault wait --name $KEY_VAULT_NAME --created
Write-Host "Getting Key Vault URI..." -ForegroundColor Blue
$KEY_VAULT_URI = (az keyvault show `
  --name $KEY_VAULT_NAME `
  --resource-group $RESOURCE_GROUP `
  --query properties.vaultUri `
  -o tsv
)
Write-Host "Assigning permissions to managed identity..." -ForegroundColor Blue
az keyvault set-policy `
  --name $KEY_VAULT_NAME `
  --object-id $USER_MANAGED_IDENTITY_PRINCIPAL_ID `
  --secret-permissions get set

# create Redis cache
Write-Host "Creating Redis cache..." -ForegroundColor Blue
az redis create `
  --location $REGION `
  --name $REDIS_CACHE_NAME `
  --resource-group $RESOURCE_GROUP `
  --sku Standard `
  --vm-size c0
$REDIS_HOST = $(az redis show `
  --name $REDIS_CACHE_NAME `
  -g $RESOURCE_GROUP `
  --query hostName `
  -o tsv
)
$REDIS_PASSWORD = $(az redis list-keys `
  --name $REDIS_CACHE_NAME `
  -g $RESOURCE_GROUP `
  --query primaryKey `
  -o tsv `
)

# create container registry
Write-Host "Creating container registry..." -ForegroundColor Blue
az acr create `
  --name $ACR_REGISTRY_NAME `
  --resource-group $RESOURCE_GROUP `
  --sku $ACR_SKU `
  --admin-enabled $ACR_ADMIN_ENABLED

# build container (in Azure)
Write-Host "Building container..." -ForegroundColor Blue
az acr build `
  -t $IMAGE `
  -r $ACR_REGISTRY_NAME .

# create log analytics workspace, tables, data collection endpoint and rules
# workspace
Write-Host "Creating Log Analytics workspace..." -ForegroundColor Blue
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
# see: https://learn.microsoft.com/en-us/azure/azure-monitor/logs/tutorial-logs-ingestion-portal
Write-Host "Creating assets required to log usage data to Log Analytics..." -ForegroundColor Blue
Write-Host "Creating custom table 'AzureOpenAIUsage_PP_CL'..." -ForegroundColor Blue
az monitor log-analytics workspace table create `
  --resource-group $RESOURCE_GROUP `
  --workspace-name $LOG_ANALYTICS_WORKSPACE_NAME `
  --name "AzureOpenAIUsage_PP_CL" `
  --retention-time $LOG_ANALYTICS_AOAIUSAGE_TABLE_RETENTION_TIME `
  --columns `
    TimeGenerated=datetime `
    RequestReceivedUtc=string `
    Client=string `
    IsStreaming=boolean `
    PromptTokens=int `
    CompletionTokens=int `
    TotalTokens=int `
    AoaiRoundtripTimeMS=int `
    AoaiRegion=string `
    AoaiEndpointName=string
# data collection endpoint
Write-Host "Creating data collection endpoint..." -ForegroundColor Blue
$DATA_COLLECTION_ENDPOINT_ID = (az monitor data-collection endpoint create `
  --name $DATA_COLLECTION_ENDPOINT_NAME `
  --resource-group $RESOURCE_GROUP `
  --location $REGION `
  --public-network-access "enabled" `
  --query immutableId `
  --output tsv `
)
$LOGS_INGESTION_ENDPOINT = (az monitor data-collection endpoint show `
  --name $DATA_COLLECTION_ENDPOINT_NAME `
  --resource-group $RESOURCE_GROUP `
  --query logsIngestion.endpoint `
  --output tsv `
)
# data collection rule
Write-Host "Creating data collection rule..." -ForegroundColor Blue
$rule_file_path = "rule-file.json"
Try {
  Copy-Item -Path "rule-file.template.json" -Destination $rule_file_path
  ((Get-Content $rule_file_path) -replace "##workspaceResourceId##", $LOG_ANALYTICS_WORKSPACE_ID) `
    | Set-Content -Path $rule_file_path
  ((Get-Content $rule_file_path) -replace "##dataCollectionEndpointId##", `
      $DATA_COLLECTION_ENDPOINT_ID) | Set-Content -Path $rule_file_path
  $DCR_IMMUTABLE_ID = (az monitor data-collection rule create `
    --name "AzureOpenAIUsage_PP_CL" `
    --resource-group $RESOURCE_GROUP `
    --location $REGION `
    --rule-file $rule_file_path `
    --query immutableId `
    --output tsv
  )
}
Finally {
  if (Test-Path $rule_file_path) {
    Remove-Item $rule_file_path
  }
}
# assign Monitoring Metrics Publisher role at data collection rule to user-managed identity
Write-Host "Assigning managed identity Monitoring Metrics Publisher role..." -ForegroundColor Blue
$DCR_ID = (az monitor data-collection rule show `
  --name "AzureOpenAIUsage_PP_CL" `
  --resource-group $RESOURCE_GROUP `
  --query id `
  --output tsv
)
az role assignment create `
  --assignee-object-id $USER_MANAGED_IDENTITY_PRINCIPAL_ID `
  --assignee-principal-type ServicePrincipal `
  --role "Monitoring Metrics Publisher" `
  --scope $DCR_ID

# set updated config string in key vault
Write-Host "Updating and setting configuration in Key Vault..." -ForegroundColor Blue
$temp_config_yaml_path = "config.temp.a9f8f42.yaml"
Try {
  #--  update values in temp config
  $new_yaml_config_string = $CONFIG_YAML_STRING
  # user_assigned_managed_identity_client_id
  $new_yaml_config_string = ($new_yaml_config_string `
    -replace "(?m)(?<=^\s*user_assigned_managed_identity_client_id\s*:\s+).*$", `
    $USER_MANAGED_IDENTITY_CLIENT_ID)
  # log_ingestion_endpoint
  $new_yaml_config_string = ($new_yaml_config_string `
    -replace "(?m)(?<=^\s*log_ingestion_endpoint\s*:\s+).*$", `
    $LOGS_INGESTION_ENDPOINT)
  # data_collection_rule_id
  $new_yaml_config_string = ($new_yaml_config_string `
    -replace "(?m)(?<=^\s*data_collection_rule_id\s*:\s+).*$", `
    $DCR_IMMUTABLE_ID)
  # redis_host
  $new_yaml_config_string = ($new_yaml_config_string `
    -replace "(?m)(?<=^\s*redis_host\s*:\s+).*$", `
    $REDIS_HOST)
  # redis_password
  $new_yaml_config_string = ($new_yaml_config_string `
    -replace "(?m)(?<=^\s*redis_password\s*:\s+).*$", `
    $REDIS_PASSWORD)

  #-- write to file and set secret in Key Vault
  $new_yaml_config_string | Set-Content -Path $temp_config_yaml_path
  az keyvault secret set `
    --vault-name $KEY_VAULT_NAME `
    --name "config-string" `
    --file $temp_config_yaml_path `
    --output none

}
Finally {
  if (Test-Path $temp_config_yaml_path) {
    Remove-Item $temp_config_yaml_path
  }
}

# deploy container to Azure Container Apps
Write-Host "Deploying PowerProxy to Container Apps..." -ForegroundColor Blue
# environment
Write-Host "Creating Container Apps environment..." -ForegroundColor Blue
az containerapp env create `
  --name $CONTAINER_APP_ENVIRONMENT `
  --resource-group $RESOURCE_GROUP `
  --location $REGION `
  --logs-destination log-analytics `
  --logs-workspace-id $LOG_ANALYTICS_WORKSPACE_CUSTOMER_ID `
  --logs-workspace-key $LOG_ANALYTICS_WORKSPACE_KEY
# app incl. secrets and env vars
Write-Host "Creating Container Apps app..." -ForegroundColor Blue
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
# user-managed identity
Write-Host "Assigning managed identity to Container App..." -ForegroundColor Blue
az containerapp identity assign `
  --resource-group $RESOURCE_GROUP `
  --name $CONTAINER_APP_NAME `
  --user-assigned $USER_MANAGED_IDENTITY_NAME
# secrets and env vars
Write-Host "Sharing config from Key Vault to Container App..." -ForegroundColor Blue
az containerapp secret set `
  --name $CONTAINER_APP_NAME `
  --resource-group $RESOURCE_GROUP `
  --secrets "config-string=keyvaultref:$($KEY_VAULT_URI)secrets/config-string,identityref:$USER_MANAGED_IDENTITY_ID"
az containerapp update `
  --name $CONTAINER_APP_NAME `
  --resource-group $RESOURCE_GROUP `
  --set-env-vars "POWERPROXY_CONFIG_STRING=secretref:config-string"
# restart active revisions to bring secrects and env vars into effect
Write-Host "Restarting Container App to bring new secret value into effect..." -ForegroundColor Blue
az containerapp revision list `
  --name $CONTAINER_APP_NAME `
  --resource-group $RESOURCE_GROUP `
  --query "[?properties.active].name" -o tsv | ForEach-Object {
az containerapp revision restart `
    --name $CONTAINER_APP_NAME `
    --resource-group $RESOURCE_GROUP `
    --revision $_
}

#-----------------------------------------[Done Message]--------------------------------------------
# deployed message
$POWERPROXY_URL = "https://$(`
  az containerapp show `
    --name $CONTAINER_APP_NAME `
    --resource-group $RESOURCE_GROUP `
    --query properties.configuration.ingress.fqdn `
    -o tsv `
)"
Write-Host "🎉 PowerProxy has been deployed successfully and is ready to serve requests."
Write-Host "Endpoint      : $POWERPROXY_URL"
Write-Host "Liveness test : $POWERPROXY_URL/powerproxy/health/liveness"
Write-Host "Enjoy!"

#--------------------------------------------[Cleanup]----------------------------------------------
# # explictly delete the Log Analytics workspace to delete contained data
# az monitor log-analytics workspace delete `
#   --resource-group $RESOURCE_GROUP `
#   --workspace-name $LOG_ANALYTICS_WORKSPACE_NAME `
#   --force `
#   -y
# # then delete the entire resource group containing all the rest
# az group delete -n $RESOURCE_GROUP -y
