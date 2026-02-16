#!/bin/bash
# Validate Bicep templates before deployment

set -e

if [ $# -eq 0 ]; then
    echo "Usage: validate_bicep.sh <bicep-file> [resource-group]"
    echo ""
    echo "Examples:"
    echo "  validate_bicep.sh main.bicep"
    echo "  validate_bicep.sh main.bicep rg-myapp-dev-weu"
    exit 1
fi

BICEP_FILE="$1"
RESOURCE_GROUP="${2:-}"

# Check if file exists
if [ ! -f "$BICEP_FILE" ]; then
    echo "Error: Bicep file not found: $BICEP_FILE"
    exit 1
fi

echo "Validating Bicep template: $BICEP_FILE"
echo "----------------------------------------"

# Build the template (compiles Bicep to ARM)
echo "Building template..."
az bicep build --file "$BICEP_FILE"
echo "✓ Build successful"

# If resource group provided, validate deployment
if [ -n "$RESOURCE_GROUP" ]; then
    echo ""
    echo "Validating deployment to resource group: $RESOURCE_GROUP"
    az deployment group validate \
        --resource-group "$RESOURCE_GROUP" \
        --template-file "$BICEP_FILE"
    echo "✓ Validation successful"
else
    echo ""
    echo "Note: Skipping deployment validation (no resource group specified)"
    echo "To validate deployment, provide resource group name as second argument"
fi

echo ""
echo "✓ All validation checks passed"
