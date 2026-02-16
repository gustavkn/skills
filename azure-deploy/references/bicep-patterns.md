# Common Bicep Patterns

This document provides common Bicep patterns for the most frequently used Azure resources in microservice architectures.

## Table of Contents

1. [Parameters and Variables](#parameters-and-variables)
2. [Azure Functions](#azure-functions)
3. [SQL Database](#sql-database)
4. [Storage Account](#storage-account)
5. [Data Factory](#data-factory)
6. [Application Insights](#application-insights)
7. [Key Vault](#key-vault)
8. [Complete Microservice Stack](#complete-microservice-stack)

---

## Parameters and Variables

### Common Parameters Pattern

```bicep
@description('Application name used for resource naming')
param appName string

@description('Environment (dev, test, prod)')
@allowed([
  'dev'
  'test'
  'prod'
])
param environment string = 'dev'

@description('Azure region')
param location string = resourceGroup().location

@description('Azure region abbreviation for naming')
param regionAbbr string = 'weu'

@description('Tags to apply to all resources')
param tags object = {
  Environment: environment
  Application: appName
  ManagedBy: 'Bicep'
}
```

### Resource Naming Variables

```bicep
var resourceNames = {
  functionApp: 'func-${appName}-${environment}-${regionAbbr}'
  appServicePlan: 'asp-${appName}-${environment}-${regionAbbr}'
  storageAccount: 'st${replace(appName, '-', '')}${environment}${regionAbbr}'
  sqlServer: 'sql-${appName}-${environment}-${regionAbbr}'
  sqlDatabase: 'sqldb-${appName}-${environment}-${regionAbbr}'
  dataFactory: 'adf-${appName}-${environment}-${regionAbbr}'
  appInsights: 'appi-${appName}-${environment}-${regionAbbr}'
  keyVault: 'kv-${appName}-${environment}-${regionAbbr}'
}
```

---

## Azure Functions

### Basic Function App (Consumption Plan)

```bicep
// Storage account (required for Functions)
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: resourceNames.storageAccount
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'  // Cheapest: Locally Redundant Storage
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

// App Service Plan (Consumption)
resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: resourceNames.appServicePlan
  location: location
  tags: tags
  sku: {
    name: 'Y1'  // Consumption plan (cheapest)
    tier: 'Dynamic'
  }
  properties: {
    reserved: true  // Required for Linux
  }
}

// Function App
resource functionApp 'Microsoft.Web/sites@2023-01-01' = {
  name: resourceNames.functionApp
  location: location
  tags: tags
  kind: 'functionapp,linux'
  properties: {
    serverFarmId: appServicePlan.id
    reserved: true
    siteConfig: {
      linuxFxVersion: 'DOTNET-ISOLATED|8.0'  // or 'PYTHON|3.11', 'NODE|20', etc.
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};EndpointSuffix=${az.environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
        }
        {
          name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};EndpointSuffix=${az.environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
        }
        {
          name: 'WEBSITE_CONTENTSHARE'
          value: toLower(resourceNames.functionApp)
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'dotnet-isolated'  // or 'python', 'node', etc.
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: applicationInsights.properties.ConnectionString
        }
      ]
    }
    httpsOnly: true
  }
}
```

---

## SQL Database

### SQL Server and Database (Basic Tier)

```bicep
@description('SQL Admin username')
@secure()
param sqlAdminUsername string

@description('SQL Admin password')
@secure()
param sqlAdminPassword string

// SQL Server
resource sqlServer 'Microsoft.Sql/servers@2023-05-01-preview' = {
  name: resourceNames.sqlServer
  location: location
  tags: tags
  properties: {
    administratorLogin: sqlAdminUsername
    administratorLoginPassword: sqlAdminPassword
    version: '12.0'
    minimalTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'  // Consider 'Disabled' for production
  }
}

// Firewall rule to allow Azure services
resource sqlFirewallAzure 'Microsoft.Sql/servers/firewallRules@2023-05-01-preview' = {
  parent: sqlServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// SQL Database (Basic tier - cheapest)
resource sqlDatabase 'Microsoft.Sql/servers/databases@2023-05-01-preview' = {
  parent: sqlServer
  name: resourceNames.sqlDatabase
  location: location
  tags: tags
  sku: {
    name: 'Basic'  // Cheapest tier
    tier: 'Basic'
    capacity: 5
  }
  properties: {
    collation: 'SQL_Latin1_General_CP1_CI_AS'
    maxSizeBytes: 2147483648  // 2 GB
    catalogCollation: 'SQL_Latin1_General_CP1_CI_AS'
    zoneRedundant: false
  }
}

// Output connection string (for reference, store in Key Vault)
output sqlConnectionString string = 'Server=tcp:${sqlServer.properties.fullyQualifiedDomainName},1433;Initial Catalog=${sqlDatabase.name};Persist Security Info=False;User ID=${sqlAdminUsername};Password=${sqlAdminPassword};MultipleActiveResultSets=False;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;'
```

### SQL Database (Serverless - Better for Dev)

```bicep
// SQL Database (Serverless - auto-pauses, good for dev)
resource sqlDatabaseServerless 'Microsoft.Sql/servers/databases@2023-05-01-preview' = {
  parent: sqlServer
  name: resourceNames.sqlDatabase
  location: location
  tags: tags
  sku: {
    name: 'GP_S_Gen5'  // Serverless
    tier: 'GeneralPurpose'
    family: 'Gen5'
    capacity: 1  // Min vCores
  }
  properties: {
    collation: 'SQL_Latin1_General_CP1_CI_AS'
    maxSizeBytes: 34359738368  // 32 GB
    autoPauseDelay: 60  // Auto-pause after 60 minutes of inactivity
    minCapacity: 0.5  // Minimum vCores when active
  }
}
```

---

## Storage Account

### General Purpose Storage Account

```bicep
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: resourceNames.storageAccount
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'  // Cheapest: Locally Redundant Storage
    // Other options: 'Standard_GRS' (geo-redundant), 'Standard_ZRS' (zone-redundant)
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false  // Security best practice
    supportsHttpsTrafficOnly: true
    accessTier: 'Hot'  // Or 'Cool' for infrequent access
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'  // Consider 'Deny' for production with specific rules
    }
  }
}

// Blob container
resource blobContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: '${storageAccount.name}/default/data'
  properties: {
    publicAccess: 'None'
  }
}

// Output connection string
output storageConnectionString string = 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};EndpointSuffix=${az.environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
```

---

## Data Factory

### Basic Data Factory

```bicep
resource dataFactory 'Microsoft.DataFactory/factories@2018-06-01' = {
  name: resourceNames.dataFactory
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    publicNetworkAccess: 'Enabled'
  }
}

// Linked service example (SQL Database)
resource linkedServiceSql 'Microsoft.DataFactory/factories/linkedservices@2018-06-01' = {
  parent: dataFactory
  name: 'LinkedServiceSqlDb'
  properties: {
    type: 'AzureSqlDatabase'
    typeProperties: {
      connectionString: 'Integrated Security=False;Encrypt=True;Connection Timeout=30;Data Source=${sqlServer.properties.fullyQualifiedDomainName};Initial Catalog=${sqlDatabase.name}'
      userName: sqlAdminUsername
      password: {
        type: 'SecureString'
        value: sqlAdminPassword
      }
    }
  }
}

// Output Data Factory identity (for granting permissions)
output dataFactoryPrincipalId string = dataFactory.identity.principalId
```

---

## Application Insights

### Application Insights with Log Analytics

```bicep
// Log Analytics Workspace
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: resourceNames.logAnalytics
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'  // Pay-as-you-go
    }
    retentionInDays: 30  // Minimum retention (cheapest)
  }
}

// Application Insights
resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: resourceNames.appInsights
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    RetentionInDays: 30
  }
}

output appInsightsConnectionString string = applicationInsights.properties.ConnectionString
output appInsightsInstrumentationKey string = applicationInsights.properties.InstrumentationKey
```

---

## Key Vault

### Key Vault for Secrets Management

```bicep
@description('Object ID of the user/service principal to grant access')
param keyVaultAccessObjectId string

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: resourceNames.keyVault
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'  // Cheapest tier
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true  // Use RBAC instead of access policies (recommended)
    enableSoftDelete: true
    softDeleteRetentionInDays: 7  // Minimum retention
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'  // Consider 'Deny' for production
    }
  }
}

// Store SQL connection string in Key Vault
resource secretSqlConnection 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'SqlConnectionString'
  properties: {
    value: 'Server=tcp:${sqlServer.properties.fullyQualifiedDomainName},1433;Initial Catalog=${sqlDatabase.name};...'
  }
}

output keyVaultUri string = keyVault.properties.vaultUri
```

---

## Complete Microservice Stack

### Full Microservice Template

This combines Function App, SQL Database, Storage, Application Insights, and Key Vault into a complete microservice environment.

```bicep
targetScope = 'resourceGroup'

// Parameters
@description('Application name')
param appName string

@description('Environment')
@allowed(['dev', 'test', 'prod'])
param environment string = 'dev'

@description('Azure region abbreviation')
param regionAbbr string = 'weu'

param location string = resourceGroup().location

@description('SQL Admin username')
@secure()
param sqlAdminUsername string

@description('SQL Admin password')
@secure()
param sqlAdminPassword string

// Variables
var resourceNames = {
  functionApp: 'func-${appName}-${environment}-${regionAbbr}'
  appServicePlan: 'asp-${appName}-${environment}-${regionAbbr}'
  storageAccount: 'st${replace(appName, '-', '')}${environment}${regionAbbr}'
  sqlServer: 'sql-${appName}-${environment}-${regionAbbr}'
  sqlDatabase: 'sqldb-${appName}-${environment}-${regionAbbr}'
  appInsights: 'appi-${appName}-${environment}-${regionAbbr}'
  logAnalytics: 'log-${appName}-${environment}-${regionAbbr}'
  keyVault: 'kv-${appName}-${environment}-${regionAbbr}'
}

var tags = {
  Environment: environment
  Application: appName
  ManagedBy: 'Bicep'
}

// Storage Account
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: resourceNames.storageAccount
  location: location
  tags: tags
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

// Log Analytics
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: resourceNames.logAnalytics
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

// Application Insights
resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: resourceNames.appInsights
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    RetentionInDays: 30
  }
}

// App Service Plan (Consumption)
resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: resourceNames.appServicePlan
  location: location
  tags: tags
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  properties: { reserved: true }
}

// Function App
resource functionApp 'Microsoft.Web/sites@2023-01-01' = {
  name: resourceNames.functionApp
  location: location
  tags: tags
  kind: 'functionapp,linux'
  properties: {
    serverFarmId: appServicePlan.id
    reserved: true
    siteConfig: {
      linuxFxVersion: 'DOTNET-ISOLATED|8.0'
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};EndpointSuffix=${az.environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
        }
        {
          name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};EndpointSuffix=${az.environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
        }
        {
          name: 'WEBSITE_CONTENTSHARE'
          value: toLower(resourceNames.functionApp)
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'dotnet-isolated'
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: applicationInsights.properties.ConnectionString
        }
        {
          name: 'SqlConnectionString'
          value: '@Microsoft.KeyVault(SecretUri=${keyVault.properties.vaultUri}secrets/SqlConnectionString/)'
        }
      ]
    }
    httpsOnly: true
  }
  identity: {
    type: 'SystemAssigned'
  }
}

// SQL Server
resource sqlServer 'Microsoft.Sql/servers@2023-05-01-preview' = {
  name: resourceNames.sqlServer
  location: location
  tags: tags
  properties: {
    administratorLogin: sqlAdminUsername
    administratorLoginPassword: sqlAdminPassword
    version: '12.0'
    minimalTlsVersion: '1.2'
  }
}

// SQL Firewall
resource sqlFirewallAzure 'Microsoft.Sql/servers/firewallRules@2023-05-01-preview' = {
  parent: sqlServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// SQL Database (Serverless for dev)
resource sqlDatabase 'Microsoft.Sql/servers/databases@2023-05-01-preview' = {
  parent: sqlServer
  name: resourceNames.sqlDatabase
  location: location
  tags: tags
  sku: environment == 'prod' ? {
    name: 'Basic'
    tier: 'Basic'
    capacity: 5
  } : {
    name: 'GP_S_Gen5'
    tier: 'GeneralPurpose'
    family: 'Gen5'
    capacity: 1
  }
  properties: {
    collation: 'SQL_Latin1_General_CP1_CI_AS'
    autoPauseDelay: environment == 'prod' ? null : 60
    minCapacity: environment == 'prod' ? null : 0.5
  }
}

// Key Vault
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: resourceNames.keyVault
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
  }
}

// Key Vault RBAC - Grant Function App access
resource keyVaultRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: keyVault
  name: guid(keyVault.id, functionApp.id, 'Key Vault Secrets User')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6') // Key Vault Secrets User
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Store SQL connection in Key Vault
resource secretSqlConnection 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'SqlConnectionString'
  properties: {
    value: 'Server=tcp:${sqlServer.properties.fullyQualifiedDomainName},1433;Initial Catalog=${sqlDatabase.name};User ID=${sqlAdminUsername};Password=${sqlAdminPassword};Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;'
  }
}

// Outputs
output functionAppName string = functionApp.name
output functionAppUrl string = 'https://${functionApp.properties.defaultHostName}'
output sqlServerFqdn string = sqlServer.properties.fullyQualifiedDomainName
output storageAccountName string = storageAccount.name
output keyVaultUri string = keyVault.properties.vaultUri
```

---

## Tier Comparison

### When to Scale Up from Cheapest Tiers

| Resource | Cheapest Tier | When to Scale Up |
|----------|--------------|------------------|
| **Function App** | Consumption (Y1) | High traffic (>1M executions/month), need VNet integration, need dedicated resources |
| **SQL Database** | Basic | Need >2GB storage, need better performance, need geo-replication |
| **Storage Account** | Standard LRS | Need geo-redundancy, need zone redundancy, need high IOPS |
| **Data Factory** | Pay-as-you-go | Never (ADF scales automatically) |
| **App Insights** | 30-day retention | Need longer retention, need daily cap increase |
| **Key Vault** | Standard | Need HSM-backed keys (Premium tier) |

## Best Practices

1. **Always use parameters** for environment-specific values
2. **Use variables** for resource names to ensure consistency
3. **Enable soft delete** on Key Vault and Storage
4. **Use managed identities** instead of connection strings when possible
5. **Store secrets in Key Vault**, reference from Function App
6. **Enable Application Insights** for all compute resources
7. **Use RBAC** over access keys/policies where supported
8. **Tag all resources** for cost tracking and governance
9. **Start with cheapest tiers** in dev/test, scale up in production
10. **Use serverless SQL** for development (auto-pause saves costs)
