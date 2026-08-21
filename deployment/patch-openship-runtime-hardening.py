#!/usr/bin/env python3
"""Patch Openship 0.1.11 to honor opt-in advanced Docker hardening fields."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import shutil
import subprocess
import sys
from pathlib import Path


USER_ANCHOR = """        Env: env,
        Hostname: config.serviceName,"""
USER_REPLACEMENT = """        Env: env,
        ...config.advanced?.user && { User: config.advanced.user },
        Hostname: config.serviceName,"""

HOST_ANCHOR = """        HostConfig: {
          RestartPolicy: restartPolicy,"""
HOST_REPLACEMENT = """        HostConfig: {
          RestartPolicy: restartPolicy,
          ...config.advanced?.readOnly === true && { ReadonlyRootfs: true },
          ...Array.isArray(config.advanced?.capDrop) && { CapDrop: config.advanced.capDrop },
          ...Array.isArray(config.advanced?.securityOpt) && { SecurityOpt: config.advanced.securityOpt },
          ...config.advanced?.init === true && { Init: true },
          ...config.advanced?.tmpfs && { Tmpfs: config.advanced.tmpfs },"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle")
    args = parser.parse_args()

    bundle = Path(args.bundle).resolve()
    source = bundle.read_text(encoding="utf-8")
    if "config.advanced?.readOnly === true" in source:
        print("Openship runtime hardening patch already present")
        return 0
    if source.count(USER_ANCHOR) != 1:
        raise RuntimeError("Openship service user anchor did not match exactly once")

    patched = source.replace(USER_ANCHOR, USER_REPLACEMENT)
    before_host, separator, after_host = patched.partition(USER_REPLACEMENT)
    if not separator or HOST_ANCHOR not in after_host:
        raise RuntimeError("Openship service HostConfig anchor was not found after the user anchor")
    patched = before_host + separator + after_host.replace(HOST_ANCHOR, HOST_REPLACEMENT, 1)
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = bundle.with_name(f"{bundle.name}.pre-brain-hardening-{timestamp}")
    shutil.copy2(bundle, backup)

    temporary = bundle.with_name(f".{bundle.name}.brain-hardening.tmp")
    try:
        temporary.write_text(patched, encoding="utf-8")
        os.replace(temporary, bundle)
        subprocess.run(["node", "--check", str(bundle)], check=True)
    except Exception:
        shutil.copy2(backup, bundle)
        temporary.unlink(missing_ok=True)
        raise

    print(f"Patched Openship runtime; backup={backup}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
