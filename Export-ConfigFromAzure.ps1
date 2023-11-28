<#
.SYNOPSIS
Exports a PowerProxy's configuration from a given Key Vault.

.DESCRIPTION
Writes a PowerProxy's configuration from the given Key Vault to the given file.

.PARAMETER KeyVaultName
Name of the Key Vault in which the configuration is stored.

.EXAMPLE
PS> .\Export-ConfigFromAzure.ps1 -KeyVaultName abdefpowerproxyaoai -ToFile production.config.yaml

Exports the PowerProxy config from Key Vault 'abdefpowerproxyaoai' to file 'production.config.yaml'.

.LINK
GitHub repo: https://github.com/timoklimmer/powerproxy-aoai

.NOTES
PowerShell version should be 7+. Also make sure your Azure CLI installation is up-to-date.
#>
param(
  [Parameter(mandatory=$true)]
  [string] $KeyVaultName,

  [Parameter(mandatory=$true)]
  [string] $ToFile
)

#---------------------------------------[Initialisation]--------------------------------------------
$ErrorActionPreference = "Stop"
Write-Host "Exporting PowerProxy config from Key Vault '$KeyVaultName' to file '$ToFile'..."

#--------------------------------------------[Code]-------------------------------------------------
Write-Host "Getting config from Key Vault..."
$config_json_string = ( `
    az keyvault secret show `
        -n config-string `
        --vault-name $KeyVaultName `
        --query value `
        -o tsv `
    )
Write-Host "Saving file..."
$config_json_string | Out-File $ToFile

#--------------------------------------------[Done]-------------------------------------------------
Write-Host "Done."
