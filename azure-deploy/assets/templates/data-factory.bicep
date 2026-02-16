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

@description('SQL Server FQDN (if linking to SQL)')
param sqlServerFqdn string = ''

@description('SQL Database name (if linking to SQL)')
param sqlDatabaseName string = ''

@description('SQL Admin username (if linking to SQL)')
@secure()
param sqlAdminUsername string = ''

@description('SQL Admin password (if linking to SQL)')
@secure()
param sqlAdminPassword string = ''

@description('Storage account name for staging (if using blob storage)')
param storageAccountName string = ''

// Variables
var resourceNames = {
  dataFactory: 'adf-${appName}-${environment}-${regionAbbr}'
}

var tags = {
  Environment: environment
  Application: appName
  ManagedBy: 'Bicep'
}

var hasSqlConnection = !empty(sqlServerFqdn) && !empty(sqlDatabaseName) && !empty(sqlAdminUsername)
var hasStorageConnection = !empty(storageAccountName)

// Data Factory
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

// Linked Service - SQL Database (optional)
resource linkedServiceSql 'Microsoft.DataFactory/factories/linkedservices@2018-06-01' = if (hasSqlConnection) {
  parent: dataFactory
  name: 'LinkedServiceSqlDb'
  properties: {
    type: 'AzureSqlDatabase'
    typeProperties: {
      connectionString: 'Integrated Security=False;Encrypt=True;Connection Timeout=30;Data Source=${sqlServerFqdn};Initial Catalog=${sqlDatabaseName};User ID=${sqlAdminUsername};Password=${sqlAdminPassword}'
    }
  }
}

// Linked Service - Blob Storage (optional)
resource linkedServiceBlob 'Microsoft.DataFactory/factories/linkedservices@2018-06-01' = if (hasStorageConnection) {
  parent: dataFactory
  name: 'LinkedServiceBlobStorage'
  properties: {
    type: 'AzureBlobStorage'
    typeProperties: {
      connectionString: 'DefaultEndpointsProtocol=https;AccountName=${storageAccountName};EndpointSuffix=${az.environment().suffixes.storage}'
    }
  }
}

// Outputs
output dataFactoryName string = dataFactory.name
output dataFactoryId string = dataFactory.id
output dataFactoryPrincipalId string = dataFactory.identity.principalId
