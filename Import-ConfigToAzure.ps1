<#
.SYNOPSIS
Imports a PowerProxy's configuration into a given Key Vault.

.DESCRIPTION
Writes a PowerProxy's configuration into the given Key Vault from the given file.

.PARAMETER KeyVaultName
Name of the Key Vault in which the configuration is stored.

.EXAMPLE
PS> .\Import-ConfigToAzure.ps1 -KeyVaultName abdefpowerproxyaoai -FromFile production.config.json

Imports the PowerProxy config from Key Vault 'abdefpowerproxyaoai' from JSON file 'production.config.json'.

.LINK
GitHub repo: https://github.com/timoklimmer/powerproxy-aoai

.NOTES
PowerShell version should be 7+. Also make sure your Azure CLI installation is up-to-date.
#>
param(
  [Parameter(mandatory=$true)]
  [string] $KeyVaultName,

  [Parameter(mandatory=$true)]
  [string] $FromFile,

  [Parameter(mandatory=$true)]
  [string] $ResourceGroup
)

#---------------------------------------[Initialisation]--------------------------------------------
$ErrorActionPreference = "Stop"
Write-Host "Importing PowerProxy config into Key Vault '$KeyVaultName' from file '$FromFile'..."
$CONTAINER_APP_NAME = "powerproxyaoai"

#--------------------------------------------[Code]-------------------------------------------------
Write-Host "Updating config in Key Vault..."
az keyvault secret set `
    --name config-string `
    --vault-name $KeyVaultName `
    --file $FromFile `
    --output none

Write-Host "Creating new revision in Container App (required for the new config to come into effect)..."
$random_revision_suffix = (`
  -join ((48..57) + (97..122) | Get-Random -Count 7 | ForEach-Object {[char]$_}) `
)
az containerapp revision copy `
  -n $CONTAINER_APP_NAME `
  -g $ResourceGroup `
  --revision-suffix $random_revision_suffix

#--------------------------------------------[Done]-------------------------------------------------
Write-Host "Done."
