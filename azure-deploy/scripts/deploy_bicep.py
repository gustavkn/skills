#!/usr/bin/env python3
"""
Deploy Bicep templates to Azure with proper parameter handling.
"""

import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional


def load_parameters(param_file: Optional[str]) -> Dict[str, Any]:
    """Load parameters from JSON file."""
    if not param_file:
        return {}

    param_path = Path(param_file)
    if not param_path.exists():
        print(f"Error: Parameter file not found: {param_file}", file=sys.stderr)
        sys.exit(1)

    with open(param_path) as f:
        params = json.load(f)

    # Handle both direct parameters and Azure parameter file format
    if "parameters" in params:
        # Azure parameter file format
        return {k: v["value"] for k, v in params["parameters"].items()}
    else:
        # Direct parameter format
        return params


def build_az_command(
    template_file: str,
    resource_group: str,
    parameters: Dict[str, Any],
    deployment_name: Optional[str] = None,
    location: Optional[str] = None,
    what_if: bool = False,
) -> list:
    """Build Azure CLI deployment command."""

    # Base command
    if what_if:
        cmd = ["az", "deployment", "group", "what-if"]
    else:
        cmd = ["az", "deployment", "group", "create"]

    # Add resource group
    cmd.extend(["--resource-group", resource_group])

    # Add template
    cmd.extend(["--template-file", template_file])

    # Add deployment name
    if deployment_name:
        cmd.extend(["--name", deployment_name])
    else:
        # Generate name from template file
        template_name = Path(template_file).stem
        cmd.extend(["--name", f"{template_name}-deployment"])

    # Add parameters
    if parameters:
        param_str = " ".join([f"{k}={v}" for k, v in parameters.items()])
        cmd.extend(["--parameters", param_str])

    return cmd


def ensure_resource_group(resource_group: str, location: str) -> bool:
    """Ensure resource group exists, create if needed."""
    # Check if resource group exists
    check_cmd = ["az", "group", "exists", "--name", resource_group]
    result = subprocess.run(check_cmd, capture_output=True, text=True)

    if result.stdout.strip().lower() == "false":
        print(f"Creating resource group: {resource_group} in {location}")
        create_cmd = ["az", "group", "create", "--name", resource_group, "--location", location]
        result = subprocess.run(create_cmd)
        return result.returncode == 0

    return True


def deploy_bicep(
    template_file: str,
    resource_group: str,
    param_file: Optional[str] = None,
    location: str = "westeurope",
    deployment_name: Optional[str] = None,
    what_if: bool = False,
) -> int:
    """
    Deploy Bicep template to Azure.

    Args:
        template_file: Path to Bicep template file
        resource_group: Target resource group name
        param_file: Optional path to parameters JSON file
        location: Azure region (default: westeurope)
        deployment_name: Optional deployment name
        what_if: If True, run what-if analysis instead of actual deployment

    Returns:
        Exit code (0 for success)
    """
    # Validate template file
    template_path = Path(template_file)
    if not template_path.exists():
        print(f"Error: Template file not found: {template_file}", file=sys.stderr)
        return 1

    # Load parameters
    parameters = load_parameters(param_file)

    # Ensure resource group exists (skip for what-if)
    if not what_if:
        if not ensure_resource_group(resource_group, location):
            print(f"Error: Failed to create resource group: {resource_group}", file=sys.stderr)
            return 1

    # Build and execute deployment command
    cmd = build_az_command(
        template_file,
        resource_group,
        parameters,
        deployment_name,
        location,
        what_if,
    )

    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    return result.returncode


def main():
    if len(sys.argv) < 3:
        print("Usage: deploy_bicep.py <template-file> <resource-group> [options]")
        print("\nOptions:")
        print("  --param-file <file>       Path to parameters JSON file")
        print("  --location <location>     Azure region (default: westeurope)")
        print("  --name <name>             Deployment name")
        print("  --what-if                 Run what-if analysis instead of deploying")
        print("\nExamples:")
        print("  deploy_bicep.py main.bicep rg-myapp-dev-weu")
        print("  deploy_bicep.py main.bicep rg-myapp-dev-weu --param-file params.json")
        print("  deploy_bicep.py main.bicep rg-myapp-dev-weu --what-if")
        sys.exit(1)

    template_file = sys.argv[1]
    resource_group = sys.argv[2]

    # Parse optional arguments
    param_file = None
    location = "westeurope"
    deployment_name = None
    what_if = False

    i = 3
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--param-file" and i + 1 < len(sys.argv):
            param_file = sys.argv[i + 1]
            i += 2
        elif arg == "--location" and i + 1 < len(sys.argv):
            location = sys.argv[i + 1]
            i += 2
        elif arg == "--name" and i + 1 < len(sys.argv):
            deployment_name = sys.argv[i + 1]
            i += 2
        elif arg == "--what-if":
            what_if = True
            i += 1
        else:
            print(f"Unknown argument: {arg}", file=sys.stderr)
            sys.exit(1)

    # Deploy
    exit_code = deploy_bicep(
        template_file,
        resource_group,
        param_file,
        location,
        deployment_name,
        what_if,
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
