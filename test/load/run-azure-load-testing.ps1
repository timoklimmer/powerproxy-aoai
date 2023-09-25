$ErrorActionPreference = "Stop"

# Variables
$loadTestResource="powerproxyload"
$location="francecentral"
$resourceGroup="powerproxyload"
$testId = "default"

# Change directory to the script location, so that relative paths work
Set-Location (Split-Path $MyInvocation.MyCommand.Path)

# Configure the CLI
Write-Host "Configuring the CLI (RG ${resourceGroup})"
az configure --defaults group=$resourceGroup

# Create a resource
Write-Host "Creating the test (resource ${loadTestResource})"
az load create `
  --location $location `
  --name $loadTestResource

# Create the test
Write-Host "Creating the test (ID ${testId}))"
az load test create `
  --load-test-config-file "default.yaml" `
  --load-test-resource $loadTestResource `
  --test-id $testId

# Run
$testRunId = "run-" + (Get-Date -UFormat "%Y%m%d%-%H%M%S")
$displayName = "Run " + (Get-Date -UFormat "%Y/%m/%d %H:%M:%S")
Write-Host "Running the test (ID ${testRunId})"
az load test-run create `
  --description "Test run from CLI" `
  --display-name $displayName `
  --load-test-resource $loadTestResource `
  --test-id $testId `
  --test-run-id $testRunId

# Return metrics
Write-Host "Returning metrics"
az load test-run metrics list `
  --load-test-resource $loadTestResource `
  --metric-namespace LoadTestRunMetrics `
  --test-run-id $testRunId
