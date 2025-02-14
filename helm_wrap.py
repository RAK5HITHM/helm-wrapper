#!/usr/bin/env python3

import sys
import subprocess
import re
import os
from hwrap_settings import REAL_HELM, HARBOR_HOST

# Define repository substitutions
SUBSTITUTION_HOSTS = {
    "https://charts.bitnami.com/bitnami": "bitnami"
}

def get_helm_repos():
    """Retrieve Helm repositories as a dictionary {repo_name: repo_url}."""
    try:
        result = subprocess.run(
            [REAL_HELM, "repo", "list"],
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError:
        return {}  # Return empty if `helm repo list` fails

    repos = {}
    for line in result.stdout.splitlines()[1:]:  # Skip header
        parts = line.split()
        if len(parts) >= 2:
            repos[parts[0]] = parts[1]
    return repos

def is_local_chart(chart_ref):
    """Checks if the given chart_ref is a local Helm chart."""
    return os.path.isdir(chart_ref) and os.path.isfile(os.path.join(chart_ref, "Chart.yaml")) and os.path.isdir(os.path.join(chart_ref, "templates"))

def find_chart_reference(args):
    """Finds and returns the repo/chartname in the argument list."""
    for arg in args:
        if re.match(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$", arg):  # Match word/word pattern
            return arg
    return None

def modify_helm_command(args):
    """Modifies the Helm command if a valid repo/chartname is found and it's not a local chart."""
    if len(args) < 2:
        return " ".join([REAL_HELM] + args[1:])  # Pass through unchanged if too few arguments

    chart_ref = find_chart_reference(args)
    if not chart_ref:
        return " ".join([REAL_HELM] + args[1:])  # No valid repo/chartname found

    # Check if the chart is a local Helm chart (Chart.yaml & templates/)
    if is_local_chart(chart_ref):
        return " ".join([REAL_HELM] + args[1:])  # If local, don't modify

    repo, chart = chart_ref.split("/")
    repos = get_helm_repos()

    if repo not in repos:
        return " ".join([REAL_HELM] + args[1:])  # Repo not found, return unchanged

    repo_url = repos[repo]
    if repo_url in SUBSTITUTION_HOSTS:
        # Modify chart reference
        new_chart_ref = f"oci://{HARBOR_HOST}/{SUBSTITUTION_HOSTS[repo_url]}/{chart}"

        # Replace in args
        modified_args = [new_chart_ref if arg == chart_ref else arg for arg in args]
        return " ".join([REAL_HELM] + modified_args[1:])  # Ensure `helm` is used

    return " ".join([REAL_HELM] + args[1:])  # Default case, no substitution

if __name__ == "__main__":
    # Execute when the module is not initialized from an import statement.
    if 'DEBUG_WRAPPER' in os.environ:
        import debugpy
        debugpy.listen(('0.0.0.0', 5678))
        print("Waiting for debugger attach", file=sys.stderr)
        debugpy.wait_for_client()

    modified_cmd = modify_helm_command(sys.argv)
    print(modified_cmd)  # Print the modified command for the wrapper script