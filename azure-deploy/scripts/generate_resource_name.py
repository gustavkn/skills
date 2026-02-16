#!/usr/bin/env python3
"""
Generate Azure resource names following Microsoft naming conventions.
See: https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/azure-best-practices/resource-naming
"""

import sys
import re
from typing import Optional


# Azure naming convention patterns
RESOURCE_ABBR = {
    "resource-group": "rg",
    "storage-account": "st",
    "function-app": "func",
    "app-service-plan": "asp",
    "sql-server": "sql",
    "sql-database": "sqldb",
    "data-factory": "adf",
    "key-vault": "kv",
    "application-insights": "appi",
    "log-analytics-workspace": "log",
    "cosmos-db": "cosmos",
    "api-management": "apim",
    "service-bus-namespace": "sb",
    "event-hub-namespace": "evhns",
    "event-hub": "evh",
    "container-registry": "cr",
    "kubernetes-service": "aks",
}


def sanitize_name(name: str, resource_type: str) -> str:
    """Sanitize name according to Azure resource naming rules."""
    # Convert to lowercase
    name = name.lower()

    # Storage accounts have strict rules: only alphanumeric, 3-24 chars
    if resource_type == "storage-account":
        name = re.sub(r'[^a-z0-9]', '', name)
        return name[:24]

    # Most resources: alphanumeric and hyphens
    name = re.sub(r'[^a-z0-9-]', '-', name)

    # Remove consecutive hyphens
    name = re.sub(r'-+', '-', name)

    # Remove leading/trailing hyphens
    name = name.strip('-')

    return name


def generate_resource_name(
    resource_type: str,
    app_name: str,
    environment: str = "dev",
    region: str = "weu",
    instance: Optional[str] = None,
) -> str:
    """
    Generate Azure resource name following naming conventions.

    Pattern: <resource-type>-<app-name>-<environment>-<region>[-<instance>]

    Args:
        resource_type: Type of Azure resource (e.g., 'function-app', 'sql-database')
        app_name: Application or project name
        environment: Environment (dev, test, prod)
        region: Azure region abbreviation (weu=West Europe, eus=East US, etc.)
        instance: Optional instance number or identifier

    Returns:
        Formatted resource name
    """
    if resource_type not in RESOURCE_ABBR:
        print(f"Warning: Unknown resource type '{resource_type}'. Using as-is.", file=sys.stderr)
        abbr = resource_type
    else:
        abbr = RESOURCE_ABBR[resource_type]

    # Build name components
    parts = [abbr, app_name, environment, region]
    if instance:
        parts.append(instance)

    # Join and sanitize
    name = "-".join(parts)
    name = sanitize_name(name, resource_type)

    return name


def main():
    if len(sys.argv) < 3:
        print("Usage: generate_resource_name.py <resource-type> <app-name> [environment] [region] [instance]")
        print("\nExamples:")
        print("  generate_resource_name.py function-app myapp")
        print("  generate_resource_name.py storage-account myapp prod weu")
        print("  generate_resource_name.py sql-database myapp dev weu 01")
        print("\nSupported resource types:")
        for rt in sorted(RESOURCE_ABBR.keys()):
            print(f"  - {rt}")
        sys.exit(1)

    resource_type = sys.argv[1]
    app_name = sys.argv[2]
    environment = sys.argv[3] if len(sys.argv) > 3 else "dev"
    region = sys.argv[4] if len(sys.argv) > 4 else "weu"
    instance = sys.argv[5] if len(sys.argv) > 5 else None

    name = generate_resource_name(resource_type, app_name, environment, region, instance)
    print(name)


if __name__ == "__main__":
    main()
