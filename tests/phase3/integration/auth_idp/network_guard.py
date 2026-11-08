"""Fail closed unless the disposable IdP Docker environment is internal/loopback.

Reads Docker metadata only; never prints inspect JSON, secrets or addresses other
than the static expected loopback ports. Used solely by isolated GitHub Actions.
"""
import json
import os
import subprocess

PROJECT = "authidpci"
NETWORK = PROJECT + "_authisolated"
IMAGES = {
    "identity-db": "postgres:17.11",
    "mailpit": "ghcr.io/axllent/mailpit:v1.32.0",
    "keycloak": "quay.io/keycloak/keycloak:26.8.2",
}
PORTS = {"identity-db": set(), "mailpit": set(), "keycloak": set()}


def docker(*args):
    return subprocess.check_output(["docker", *args], text=True)


def verify():
    if os.environ.get("CI") != "true":
        raise AssertionError("CI_ONLY")
    network = json.loads(docker("network", "inspect", NETWORK))[0]
    assert network["Internal"] is True, "Docker egress network must be internal"
    ids = docker("ps", "--filter", "label=com.docker.compose.project=" + PROJECT,
                 "--format", "{{.ID}}").split()
    assert len(ids) == 3, "exactly three IdP-only containers required"
    found = set()
    for item in json.loads(docker("inspect", *ids)):
        cfg = item["Config"]
        name = cfg["Labels"]["com.docker.compose.service"]
        assert name in IMAGES and name not in found
        found.add(name)
        assert cfg["Image"] == IMAGES[name], "unexpected unpinned image"
        assert set(item["NetworkSettings"]["Networks"]) == {NETWORK}, "external network attached"
        bindings = item["HostConfig"].get("PortBindings") or {}
        assigned = set()
        for hosts in bindings.values():
            for bind in hosts or []:
                assert bind["HostIp"] == "127.0.0.1", "not loopback"
                assigned.add(int(bind["HostPort"]))
        assert assigned == PORTS[name], "unexpected published ports"
    assert found == set(IMAGES)
    print("ISOLATED_NETWORK_INSPECT_PASS")


if __name__ == "__main__":
    verify()
