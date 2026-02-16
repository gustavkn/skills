# Azure Resource Naming Conventions

This document outlines the Azure naming conventions used for resources. Following these conventions ensures consistency, clarity, and maintainability.

## Naming Pattern

The standard naming pattern is:

```
<resource-type>-<app-name>-<environment>-<region>[-<instance>]
```

### Components

- **resource-type**: Abbreviated resource type (see table below)
- **app-name**: Application or project name (lowercase, alphanumeric, hyphens)
- **environment**: Environment identifier
  - `dev` - Development
  - `test` - Testing/QA
  - `stage` - Staging
  - `prod` - Production
- **region**: Azure region abbreviation
  - `weu` - West Europe
  - `neu` - North Europe
  - `eus` - East US
  - `wus` - West US
  - `sea` - Southeast Asia
- **instance**: Optional instance number or identifier (e.g., `01`, `02`)

## Resource Type Abbreviations

| Resource Type | Abbreviation | Example |
|--------------|--------------|---------|
| Resource Group | `rg` | `rg-myapp-dev-weu` |
| Storage Account | `st` | `stmyappdevweu` (no hyphens) |
| Function App | `func` | `func-myapp-dev-weu` |
| App Service Plan | `asp` | `asp-myapp-dev-weu` |
| SQL Server | `sql` | `sql-myapp-dev-weu` |
| SQL Database | `sqldb` | `sqldb-myapp-dev-weu` |
| Data Factory | `adf` | `adf-myapp-dev-weu` |
| Key Vault | `kv` | `kv-myapp-dev-weu` |
| Application Insights | `appi` | `appi-myapp-dev-weu` |
| Log Analytics Workspace | `log` | `log-myapp-dev-weu` |
| Cosmos DB | `cosmos` | `cosmos-myapp-dev-weu` |
| API Management | `apim` | `apim-myapp-dev-weu` |
| Service Bus Namespace | `sb` | `sb-myapp-dev-weu` |
| Event Hub Namespace | `evhns` | `evhns-myapp-dev-weu` |
| Event Hub | `evh` | `evh-myapp-dev-weu` |
| Container Registry | `cr` | `crmyappdevweu` (no hyphens) |
| Kubernetes Service | `aks` | `aks-myapp-dev-weu` |

## Special Naming Rules

### Storage Accounts
- **Only alphanumeric characters** (no hyphens, underscores)
- **3-24 characters** maximum
- **Globally unique** across all of Azure
- Example: `stmyappdevweu`, `stmyappprodweu01`

### Key Vaults
- **3-24 characters** maximum
- Alphanumeric and hyphens only
- Must start with a letter
- **Globally unique** across all of Azure

### Container Registry
- **Only alphanumeric characters** (no hyphens)
- **5-50 characters**
- **Globally unique** across all of Azure

## Examples

### Simple Function App Environment
```
rg-paymentapi-dev-weu           # Resource group
func-paymentapi-dev-weu         # Function app
asp-paymentapi-dev-weu          # App service plan (consumption)
stpaymentapidevweu              # Storage account
appi-paymentapi-dev-weu         # Application insights
```

### SQL Database with Multiple Instances
```
rg-customerdb-prod-weu          # Resource group
sql-customerdb-prod-weu         # SQL server
sqldb-customerdb-prod-weu-01    # Database instance 1
sqldb-customerdb-prod-weu-02    # Database instance 2
```

### Data Factory ETL Pipeline
```
rg-etl-prod-weu                 # Resource group
adf-etl-prod-weu                # Data factory
sql-etl-prod-weu                # SQL server (source/sink)
stletlprodweu                   # Storage account for staging
```

### Complete Microservice Environment
```
rg-orderservice-dev-weu         # Resource group
func-orderservice-dev-weu       # Function app
asp-orderservice-dev-weu        # App service plan
storderservicedevweu            # Storage account
sqldb-orderservice-dev-weu      # SQL database
sql-orderservice-dev-weu        # SQL server
appi-orderservice-dev-weu       # Application insights
kv-orderservice-dev-weu         # Key vault
```

## Best Practices

1. **Consistency**: Always follow the naming pattern for all resources
2. **Lowercase**: Use lowercase for better readability and consistency
3. **Descriptive app names**: Use meaningful application/project names
4. **Avoid abbreviations**: In app names, prefer full words (e.g., `customer` not `cust`)
5. **Global uniqueness**: For globally unique resources (Storage, Key Vault, Container Registry), consider adding organization prefix
6. **Instance numbers**: Use 2-digit instance numbers (01, 02) when needed
7. **Documentation**: Document any deviations from the standard pattern

## Using the Name Generator Script

The `generate_resource_name.py` script automates name generation:

```bash
# Basic usage (defaults to dev environment, weu region)
python3 scripts/generate_resource_name.py function-app myapp
# Output: func-myapp-dev-weu

# Specify environment and region
python3 scripts/generate_resource_name.py storage-account myapp prod weu
# Output: stmyappprodweu

# With instance number
python3 scripts/generate_resource_name.py sql-database myapp prod weu 01
# Output: sqldb-myapp-prod-weu-01
```

## References

- [Microsoft Cloud Adoption Framework - Naming Conventions](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/azure-best-practices/resource-naming)
- [Azure Resource Naming Restrictions](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/resource-name-rules)
