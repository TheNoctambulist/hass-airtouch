#!/usr/bin/env python3
"""Validates the manifest.json.

Validates that the manifest.json dependency versions match the PDM lock file version.
"""

import argparse
import json
import pathlib
import subprocess
import sys
from dataclasses import dataclass


@dataclass
class Error:
    """Encapsulates a detected error."""

    file_path: pathlib.Path
    message: str


parser = argparse.ArgumentParser("validate-manifest.py")
parser.add_argument("--manifest", type=str, required=True)

args = parser.parse_args()
manifest_path = pathlib.Path(args.manifest)

with manifest_path.open() as f:
    manifest = json.load(f)

errors: list[Error] = []
for dependency in manifest["requirements"]:
    if "==" not in dependency:
        errors.append(
            Error(manifest_path, f"{dependency} must be pinned to a specific release")
        )
    depencency_split = dependency.split("==")
    dependency_name = depencency_split[0]
    pdm_version = (
        subprocess.check_output(["pdm", "list", "--freeze", dependency_name])  # noqa: S603, S607
        .decode()
        .strip()
    )
    if dependency != pdm_version:
        errors.append(
            Error(
                manifest_path,
                f"'{dependency}' does not match PDM lock, must be '{pdm_version}'",
            )
        )

if errors:
    for err in errors:
        print(f"::error {err.file_path}:: {err.message}", file=sys.stderr)  # noqa: T201
sys.exit(len(errors))
