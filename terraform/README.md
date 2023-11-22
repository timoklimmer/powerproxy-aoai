# Terraform

## Prerequisites

1. Select one credential to use for the deployment
2. Login to Azure CLI with the selected credential
3. Use the selected credential to run Terraform deployment

## Usage

### install

```pwsh
terraform init
```

### lint

```pwsh
terraform fmt
```

### upgrade

```pwsh
terraform init -upgrade
```

### deploy

```pwsh
terraform apply -auto-approve -var-file=.tfvars.json
```

### dry-run

```pwsh
terraform plan -var-file=.tfvars.json
```
