Write-Host "Starting Azure OpenAI mock server"
npx --yes @stoplight/prism-cli@5.3.1 `
  mock `
  --errors=true `
  --host=localhost `
  --multiprocess=true `
  --port=8081 `
    "https://raw.githubusercontent.com/Azure/azure-rest-api-specs/main/specification/cognitiveservices/data-plane/AzureOpenAI/inference/preview/2023-08-01-preview/inference.json"
