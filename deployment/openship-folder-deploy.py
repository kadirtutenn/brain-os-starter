#!/usr/bin/env python3
"""Start an Openship folder deployment while preserving the custom domain."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def unwrap(value: Any) -> Any:
    if isinstance(value, dict) and set(value) == {"data"}:
        return value["data"]
    return value


class OpenshipApi:
    def __init__(self) -> None:
        config_path = Path(os.environ.get("OPENSHIP_CONFIG", "/root/.openship/config.json"))
        config = json.loads(config_path.read_text(encoding="utf-8"))
        context = config["contexts"][config["current"]]
        self.base_url = context["apiUrl"].rstrip("/")
        self.token = context["token"]

    def request(
        self,
        path_or_url: str,
        *,
        method: str = "GET",
        json_body: dict[str, Any] | None = None,
        raw_body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        if path_or_url.startswith(("http://", "https://")):
            url = path_or_url
        else:
            path = path_or_url.lstrip("/")
            if not path.startswith("api/"):
                path = f"api/{path}"
            url = f"{self.base_url}/{path}"
        request_headers = {"Accept": "application/json"}
        if url.startswith(self.base_url):
            request_headers["Authorization"] = f"Bearer {self.token}"
        if headers:
            request_headers.update(headers)
        body = raw_body
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=body, headers=request_headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                payload = response.read()
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", "replace")
            raise RuntimeError(f"Openship API {method} {url} failed: HTTP {error.code}: {detail}") from error
        if not payload:
            return {}
        return unwrap(json.loads(payload))


def scan_value(scan: dict[str, Any], key: str, default: Any = "") -> Any:
    value = scan.get(key, default)
    return default if value is None else value


def compose_services(scan: dict[str, Any]) -> list[dict[str, Any]]:
    allowed = {
        "name",
        "image",
        "build",
        "dockerfile",
        "ports",
        "dependsOn",
        "environment",
        "volumes",
        "command",
        "restart",
        "exposed",
        "exposedPort",
        "domain",
        "customDomain",
        "domainType",
        "kind",
        "enabled",
        "advanced",
    }
    services: list[dict[str, Any]] = []
    for raw in scan.get("services") or []:
        service = {key: value for key, value in raw.items() if key in allowed}
        service.setdefault("ports", [])
        service.setdefault("dependsOn", [])
        service.setdefault("environment", {})
        service.setdefault("volumes", [])
        service.setdefault("kind", "compose")
        service.setdefault("enabled", True)
        service.setdefault("exposed", False)
        # The root docker-compose.yml is copied from deployment/compose.yml;
        # its original ".." context must resolve to the uploaded project root.
        if service.get("build"):
            service["build"] = "."
        if service.get("name") == "brain-mcp":
            advanced = dict(service.get("advanced") or {})
            advanced.update(
                {
                    "user": "10001:10001",
                    "readOnly": True,
                    "tmpfs": {"/tmp": "size=64m,mode=1777"},
                    "capDrop": ["ALL"],
                    "securityOpt": ["no-new-privileges:true"],
                    "init": True,
                }
            )
            service["advanced"] = advanced
        services.append(service)
    return services


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-dir", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--scan-only", action="store_true")
    args = parser.parse_args()

    app_dir = Path(args.app_dir).resolve()
    api = OpenshipApi()
    endpoint = {
        "port": args.port,
        "customDomain": args.domain,
        "domainType": "custom",
    }

    print("openship adapter: creating upload session", file=sys.stderr, flush=True)
    session = api.request(
        "/api/projects/folder/session",
        method="POST",
        json_body={"name": "brain-os", "stack": "docker-compose"},
    )
    session_id = session["sessionId"]
    upload = session["upload"]

    print("openship adapter: packaging release", file=sys.stderr, flush=True)
    with tempfile.NamedTemporaryFile(prefix="openship-brain-", suffix=".tar.gz") as archive:
        subprocess.run(
            [
                "tar",
                "-czf",
                archive.name,
                "--exclude=./.git",
                "--exclude=./.openship",
                "--exclude=./.pytest_cache",
                "--exclude=__pycache__",
                "-C",
                str(app_dir),
                ".",
            ],
            check=True,
        )
        print("openship adapter: uploading release", file=sys.stderr, flush=True)
        upload_headers = dict(upload.get("headers") or {})
        upload_headers.setdefault("Content-Type", "application/gzip")
        api.request(
            upload["url"],
            method=upload.get("method", "POST"),
            raw_body=Path(archive.name).read_bytes(),
            headers=upload_headers,
        )

    print("openship adapter: scanning compose config", file=sys.stderr, flush=True)
    scan = api.request(
        f"/api/projects/folder/scan/{session_id}",
        method="POST",
        json_body={},
    )
    if scan.get("success") is False:
        raise RuntimeError(scan.get("error") or "Openship folder scan failed")
    if args.scan_only:
        print(json.dumps(scan, indent=2, sort_keys=True))
        return 0
    is_compose = any((app_dir / name).is_file() for name in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"))
    services = compose_services(scan)
    if is_compose and not services:
        raise RuntimeError("Openship did not return any Compose services")

    has_build = False if is_compose else bool(scan.get("buildCommand"))
    has_server = True if is_compose else bool(scan.get("startCommand"))
    ensure_body: dict[str, Any] = {
        "projectId": args.project,
        "name": scan_value(scan, "name", "brain-os"),
        "gitProvider": "upload",
        "framework": "docker-compose" if is_compose else scan_value(scan, "stack", "unknown"),
        "packageManager": scan_value(scan, "packageManager", "unknown"),
        "installCommand": scan_value(scan, "installCommand"),
        "buildCommand": scan_value(scan, "buildCommand"),
        "outputDirectory": scan_value(scan, "outputDirectory", "."),
        "rootDirectory": scan_value(scan, "rootDirectory", "./"),
        "buildImage": scan_value(scan, "buildImage", "ubuntu:22.04"),
        "hasBuild": has_build,
        "hasServer": has_server,
        "productionMode": "standalone" if has_server else "static",
        "publicEndpoints": [endpoint],
    }
    for optional in ("projectType", "startCommand"):
        if scan.get(optional):
            ensure_body[optional] = scan[optional]
    if has_server and scan.get("port"):
        ensure_body["port"] = scan["port"]

    print("openship adapter: preserving custom domain", file=sys.stderr, flush=True)
    ensured = api.request("/api/projects/ensure", method="POST", json_body=ensure_body)
    project_id = ensured.get("project_id") or ensured.get("projectId") or args.project

    domains = api.request(f"/api/domains?projectId={project_id}")
    domain_rows = domains if isinstance(domains, list) else domains.get("data", domains.get("domains", []))
    custom = next((row for row in domain_rows if row.get("hostname") == args.domain), None)
    if not custom:
        raise RuntimeError(f"custom domain disappeared during project ensure: {args.domain}")
    verification = api.request(f"/api/domains/{custom['id']}/verify", method="POST")
    if not verification.get("verified"):
        raise RuntimeError(verification.get("message") or f"custom domain is not verified: {args.domain}")

    print("openship adapter: starting deployment", file=sys.stderr, flush=True)
    deployment = api.request(
        "/api/deployments/build/access",
        method="POST",
        json_body={
            "projectId": project_id,
            "uploadSessionId": session_id,
            "environment": "production",
            "publicEndpoints": [endpoint],
            "buildStrategy": "local",
            "deployTarget": "local",
            "runtimeMode": "docker",
            "serviceDeploymentMode": "services",
            "services": services,
        },
    )
    deployment_id = deployment.get("deployment_id") or deployment.get("deploymentId")
    if not deployment_id:
        raise RuntimeError(f"Openship did not return a deployment id: {deployment}")
    print(deployment_id)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"openship adapter: ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
