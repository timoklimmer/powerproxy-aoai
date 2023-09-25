# Terraform

## Prerequisites

1. Terraform CLI (tested with v1.5.7)
2. A Azure Log Analytics workspace
3. A Azure Application Insights linked to the previous Log Analytics workspace

## Usage

### install

```pwsh
terraform init
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
