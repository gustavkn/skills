targetScope = 'resourceGroup'

@description('Application name for resource naming')
param appName string

@description('Environment (dev, test, prod)')
@allowed(['dev', 'test', 'prod'])
param environment string = 'dev'

@description('Azure region abbreviation')
param regionAbbr string = 'weu'

@description('Azure region')
param location string = resourceGroup().location

@description('SQL Admin username')
@secure()
param sqlAdminUsername string

@description('SQL Admin password')
@secure()
param sqlAdminPassword string

@description('Use serverless tier (recommended for dev/test)')
param useServerless bool = (environment != 'prod')

// Variables
var resourceNames = {
  sqlServer: 'sql-${appName}-${environment}-${regionAbbr}'
  sqlDatabase: 'sqldb-${appName}-${environment}-${regionAbbr}'
}

var tags = {
  Environment: environment
  Application: appName
  ManagedBy: 'Bicep'
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
    publicNetworkAccess: 'Enabled'
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

// SQL Database - Conditional SKU based on environment
resource sqlDatabase 'Microsoft.Sql/servers/databases@2023-05-01-preview' = {
  parent: sqlServer
  name: resourceNames.sqlDatabase
  location: location
  tags: tags
  sku: useServerless ? {
    name: 'GP_S_Gen5'  // Serverless (auto-pause, good for dev)
    tier: 'GeneralPurpose'
    family: 'Gen5'
    capacity: 1
  } : {
    name: 'Basic'  // Basic tier (cheapest for prod)
    tier: 'Basic'
    capacity: 5
  }
  properties: {
    collation: 'SQL_Latin1_General_CP1_CI_AS'
    maxSizeBytes: useServerless ? 34359738368 : 2147483648  // 32 GB serverless, 2 GB basic
    catalogCollation: 'SQL_Latin1_General_CP1_CI_AS'
    zoneRedundant: false
    autoPauseDelay: useServerless ? 60 : null  // Auto-pause after 60 min of inactivity
    minCapacity: useServerless ? json('0.5') : null  // Minimum vCores when active
  }
}

// Outputs
output sqlServerName string = sqlServer.name
output sqlServerFqdn string = sqlServer.properties.fullyQualifiedDomainName
output sqlDatabaseName string = sqlDatabase.name
output sqlConnectionString string = 'Server=tcp:${sqlServer.properties.fullyQualifiedDomainName},1433;Initial Catalog=${sqlDatabase.name};User ID=${sqlAdminUsername};Password=<password>;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;'
