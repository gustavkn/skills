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

@description('Function runtime (dotnet-isolated, python, node, java)')
@allowed(['dotnet-isolated', 'python', 'node', 'java'])
param runtime string = 'dotnet-isolated'

@description('Runtime version')
param runtimeVersion string = '8.0'

// Variables
var resourceNames = {
  functionApp: 'func-${appName}-${environment}-${regionAbbr}'
  appServicePlan: 'asp-${appName}-${environment}-${regionAbbr}'
  storageAccount: 'st${replace(appName, '-', '')}${environment}${regionAbbr}'
  appInsights: 'appi-${appName}-${environment}-${regionAbbr}'
  logAnalytics: 'log-${appName}-${environment}-${regionAbbr}'
}

var tags = {
  Environment: environment
  Application: appName
  ManagedBy: 'Bicep'
}

var runtimeMap = {
  'dotnet-isolated': {
    linuxFxVersion: 'DOTNET-ISOLATED|${runtimeVersion}'
    workerRuntime: 'dotnet-isolated'
  }
  python: {
    linuxFxVersion: 'PYTHON|${runtimeVersion}'
    workerRuntime: 'python'
  }
  node: {
    linuxFxVersion: 'NODE|${runtimeVersion}'
    workerRuntime: 'node'
  }
  java: {
    linuxFxVersion: 'JAVA|${runtimeVersion}'
    workerRuntime: 'java'
  }
}

// Storage Account (required for Functions)
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: resourceNames.storageAccount
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'  // Cheapest tier
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

// Log Analytics Workspace
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: resourceNames.logAnalytics
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30  // Minimum retention
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

// App Service Plan (Consumption - cheapest)
resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: resourceNames.appServicePlan
  location: location
  tags: tags
  sku: {
    name: 'Y1'  // Consumption plan
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
      linuxFxVersion: runtimeMap[runtime].linuxFxVersion
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
          value: runtimeMap[runtime].workerRuntime
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: applicationInsights.properties.ConnectionString
        }
      ]
    }
    httpsOnly: true
  }
  identity: {
    type: 'SystemAssigned'
  }
}

// Outputs
output functionAppName string = functionApp.name
output functionAppUrl string = 'https://${functionApp.properties.defaultHostName}'
output functionAppPrincipalId string = functionApp.identity.principalId
output storageAccountName string = storageAccount.name
output appInsightsConnectionString string = applicationInsights.properties.ConnectionString
output appInsightsInstrumentationKey string = applicationInsights.properties.InstrumentationKey
