---
name: azure-deploy
description: This skill should be used when deploying resources to Azure or creating Azure infrastructure. Trigger phrases include "deploy to Azure", "create Azure resources", "build this in Azure", "create a function app", "set up infrastructure", or when discussing Azure Functions, SQL databases, Storage accounts, or Data Factory deployments. Uses Bicep templates with Azure naming conventions and defaults to cheapest/lowest tiers unless specified otherwise.
---

# Azure Deploy

## Overview

This skill provides guidance and tools for deploying Azure resources using Bicep templates. It focuses on microservice architectures with Azure Functions, SQL databases, Storage accounts, and Data Factory, following Microsoft naming conventions and defaulting to the most cost-effective tiers.

## When to Use This Skill

Trigger this skill when:
- Deploying or creating Azure resources
- Building infrastructure for new projects
- Setting up microservice environments
- Creating Azure Functions, SQL databases, Storage accounts, or Data Factory resources
- User mentions: "deploy to Azure", "create a function for this", "lets build this in azure", "set up infrastructure"

## Core Principles

### 1. Azure Naming Conventions

Always follow Microsoft Azure naming conventions for all resources:

**Standard Pattern**: `<resource-type>-<app-name>-<environment>-<region>[-<instance>]`

**Example**:
- Resource Group: `rg-orderservice-dev-weu`
- Function App: `func-orderservice-dev-weu`
- SQL Database: `sqldb-orderservice-dev-weu`
- Storage Account: `storderservicedevweu` (no hyphens, globally unique)

Use the `generate_resource_name.py` script to ensure consistent naming:

```bash
python3 scripts/generate_resource_name.py function-app myapp dev weu
# Output: func-myapp-dev-weu
```

See `references/naming-conventions.md` for complete naming standards and resource type abbreviations.

### 2. Cost Optimization - Default to Cheapest Tiers

**IMPORTANT**: Unless the user explicitly specifies otherwise, always use the lowest/cheapest tier for all resources:

- **Azure Functions**: Consumption plan (Y1) - pay-per-execution
- **SQL Database**:
  - Dev/Test: Serverless (GP_S_Gen5) with auto-pause after 60 minutes
  - Production: Basic tier (5 DTU)
- **Storage Account**: Standard LRS (Locally Redundant Storage)
- **Data Factory**: Pay-as-you-go (no fixed tier)
- **Application Insights**: 30-day retention, pay-per-GB
- **Key Vault**: Standard tier

Only suggest scaling up when:
- User explicitly requests higher performance
- Requirements clearly indicate need (e.g., "high traffic", "production-grade", "geo-redundant")
- Current tier has technical limitations for the use case

### 3. Bicep as Infrastructure-as-Code

Always use Bicep templates for resource deployment:
- Version controlled infrastructure
- Repeatable deployments
- Environment-specific parameter files
- Modular and reusable templates

## Workflow

### Step 1: Understand Requirements

When a user requests Azure deployment, clarify:
1. **What resources are needed?** (Function App, SQL, Storage, Data Factory?)
2. **Application name** (for resource naming)
3. **Environment** (dev, test, prod) - default to `dev`
4. **Azure region** - default to West Europe (`weu`)
5. **Special requirements** (runtime, database schema, specific configurations)

### Step 2: Generate Resource Names

Use the naming script to ensure consistency:

```bash
# Generate names for all resources
python3 scripts/generate_resource_name.py resource-group myapp dev weu
python3 scripts/generate_resource_name.py function-app myapp dev weu
python3 scripts/generate_resource_name.py sql-database myapp dev weu
python3 scripts/generate_resource_name.py storage-account myapp dev weu
```

### Step 3: Select or Customize Bicep Template

Choose the appropriate template from `assets/templates/`:

1. **function-app.bicep** - For standalone Azure Function deployments
2. **sql-database.bicep** - For SQL Server and Database
3. **data-factory.bicep** - For ETL pipelines
4. **microservice-complete.bicep** - For complete microservice stack (Function + SQL + Storage + Key Vault + App Insights)

Customize templates as needed based on requirements. Reference `references/bicep-patterns.md` for common patterns and examples.

### Step 4: Create Parameter File

Create a parameter file based on `assets/templates/parameters.example.json`:

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "appName": {
      "value": "myapp"
    },
    "environment": {
      "value": "dev"
    },
    "regionAbbr": {
      "value": "weu"
    },
    "sqlAdminUsername": {
      "value": "sqladmin"
    },
    "sqlAdminPassword": {
      "value": "SECURE_PASSWORD_HERE"
    }
  }
}
```

**Security Note**: Never commit passwords to source control. Use Azure Key Vault references or parameter files that are gitignored.

### Step 5: Validate Bicep Template

Before deploying, validate the template:

```bash
# Build check (compiles Bicep to ARM)
bash scripts/validate_bicep.sh main.bicep

# Full validation (requires resource group)
bash scripts/validate_bicep.sh main.bicep rg-myapp-dev-weu
```

### Step 6: Deploy with What-If (Optional)

Run a what-if analysis to preview changes:

```bash
python3 scripts/deploy_bicep.py main.bicep rg-myapp-dev-weu \
  --param-file parameters.json \
  --what-if
```

### Step 7: Deploy to Azure

Deploy the template:

```bash
python3 scripts/deploy_bicep.py main.bicep rg-myapp-dev-weu \
  --param-file parameters.json \
  --location westeurope
```

The deployment script will:
- Create the resource group if it doesn't exist
- Deploy all resources defined in the template
- Output deployment results and resource details

### Step 8: Verify Deployment

After deployment, verify:
1. All resources are created successfully
2. Function App is running (if applicable)
3. Database is accessible (if applicable)
4. Application Insights is collecting telemetry
5. Key Vault secrets are accessible

## Common Scenarios

### Scenario 1: Deploy a New Function App

**User request**: "Create a function app for processing orders"

**Action**:
1. Generate resource names
2. Use `function-app.bicep` template
3. Set parameters: `appName=orderprocessor`, `environment=dev`, `runtime=dotnet-isolated`
4. Deploy with default cheapest tiers (Consumption plan, Standard LRS storage)

### Scenario 2: Complete Microservice Environment

**User request**: "Set up infrastructure for a payment service with SQL database"

**Action**:
1. Generate resource names for all components
2. Use `microservice-complete.bicep` template
3. Set parameters with SQL credentials
4. Deploy entire stack (Function + SQL + Storage + Key Vault + App Insights)
5. Note: SQL will use Serverless tier for dev (auto-pause to save costs)

### Scenario 3: Add Data Factory for ETL

**User request**: "Add Data Factory to process CSV files from blob storage to SQL"

**Action**:
1. Use `data-factory.bicep` template
2. Configure linked services for Storage and SQL
3. Deploy Data Factory with system-assigned managed identity
4. Grant Data Factory permissions to Storage and SQL

### Scenario 4: Production Deployment

**User request**: "Deploy the payment service to production"

**Action**:
1. Change environment parameter to `prod`
2. Confirm resource tier requirements (may stay on cheapest for low-traffic services)
3. Use production-specific parameter file (separate credentials)
4. Deploy to production resource group
5. Note: Production SQL uses Basic tier by default (not Serverless)

## Resources

### Scripts

- **generate_resource_name.py** - Generate Azure resource names following conventions
- **deploy_bicep.py** - Deploy Bicep templates to Azure
- **validate_bicep.sh** - Validate Bicep templates before deployment

### References

- **naming-conventions.md** - Complete Azure naming conventions guide with examples
- **bicep-patterns.md** - Common Bicep patterns for Functions, SQL, Storage, Data Factory, Key Vault, and complete microservice stacks

### Assets

- **templates/function-app.bicep** - Azure Function with Storage and App Insights
- **templates/sql-database.bicep** - SQL Server and Database (Basic or Serverless)
- **templates/data-factory.bicep** - Data Factory with linked services
- **templates/microservice-complete.bicep** - Complete microservice stack
- **templates/parameters.example.json** - Example parameter file

## Best Practices

1. **Always use naming conventions** - Consistency is critical for management
2. **Default to cheapest tiers** - Scale up only when needed
3. **Use serverless SQL for dev/test** - Auto-pause saves significant costs
4. **Store secrets in Key Vault** - Never hardcode credentials
5. **Enable Application Insights** - Essential for monitoring and debugging
6. **Use managed identities** - Avoid connection strings where possible
7. **Tag all resources** - Environment, Application, ManagedBy tags for governance
8. **Validate before deploying** - Catch errors early with what-if analysis
9. **Use parameter files** - Environment-specific configurations
10. **Version control everything** - Bicep templates and parameter files in git

## Prerequisites

Before using this skill, ensure:
- Azure CLI is installed and authenticated (`az login`)
- User has appropriate Azure permissions (Contributor role on subscription/resource group)
- Bicep CLI is installed (usually bundled with Azure CLI)
- Python 3 is available for scripts

Check Azure CLI authentication:
```bash
az account show
```

## Troubleshooting

### Resource name already taken (Storage, Key Vault)
These resources require globally unique names. Add organization prefix or additional identifiers:
```bash
python3 scripts/generate_resource_name.py storage-account mycompany-myapp dev weu
# Output: stmycompanymyappdevweu
```

### SQL Database too slow in dev
Serverless tier auto-pauses after 60 minutes of inactivity. First query after pause takes ~10-30 seconds to resume. This is expected and saves costs.

### Function App deployment fails
- Ensure storage account is created first (dependency)
- Check if Application Insights is in the same region
- Verify runtime version is supported (e.g., .NET 8, Python 3.11, Node 20)

### Permission denied errors
- Check if user has Contributor role on resource group
- For Key Vault, ensure RBAC is enabled and proper role assignments exist
- For managed identities, ensure system-assigned identity is enabled

## Quick Reference

### Deploy Function App Only
```bash
# Generate name
python3 scripts/generate_resource_name.py function-app myapp

# Deploy
python3 scripts/deploy_bicep.py assets/templates/function-app.bicep rg-myapp-dev-weu \
  --param-file params.json
```

### Deploy Complete Microservice
```bash
# Deploy full stack
python3 scripts/deploy_bicep.py assets/templates/microservice-complete.bicep rg-myapp-dev-weu \
  --param-file params.json
```

### Generate All Resource Names
```bash
APP="myapp"
ENV="dev"
REGION="weu"

echo "Resource Group: $(python3 scripts/generate_resource_name.py resource-group $APP $ENV $REGION)"
echo "Function App: $(python3 scripts/generate_resource_name.py function-app $APP $ENV $REGION)"
echo "SQL Server: $(python3 scripts/generate_resource_name.py sql-server $APP $ENV $REGION)"
echo "SQL Database: $(python3 scripts/generate_resource_name.py sql-database $APP $ENV $REGION)"
echo "Storage: $(python3 scripts/generate_resource_name.py storage-account $APP $ENV $REGION)"
```
