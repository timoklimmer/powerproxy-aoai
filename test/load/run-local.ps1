$ErrorActionPreference = "Stop"

# Change directory to the script location, so that relative paths work
Set-Location (Split-Path $MyInvocation.MyCommand.Path)

Write-Host "Starting JMeter test..."
jmeter `
  --globalproperty="default.properties" `
  --logfile="results/jmeter.log" `
  --loglevel="info" `
  --nongui `
  --reportatendofloadtests `
  --reportoutputfolder="results" `
  --testfile="default.jmx"
