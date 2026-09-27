"""Keep registry metadata consistent with the package prepared for release."""

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_registry_versions_match_package() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    manifest = json.loads((ROOT / "server.json").read_text())
    assert manifest["version"] == project["version"]
    assert len(manifest["packages"]) == 1
    package = manifest["packages"][0]
    assert package["registryType"] == "pypi"
    assert package["identifier"] == project["name"]
    assert package["version"] == project["version"]
    assert package["runtimeHint"] == "uvx"


def test_pypi_readme_proves_registry_ownership() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    manifest = json.loads((ROOT / "server.json").read_text())
    readme = (ROOT / project["readme"]).read_text()
    markers = re.findall(r"<!-- mcp-name: ([^\s]+) -->", readme)
    assert markers == [manifest["name"]]
    assert manifest["name"] == "io.github.Zelinqa/zelinqa-mcp"
    assert manifest["repository"] == {
        "source": "github",
        "url": project["urls"]["Repository"],
    }


def test_registry_requires_a_host_secret_and_local_transport() -> None:
    manifest = json.loads((ROOT / "server.json").read_text())
    assert "remotes" not in manifest
    package = manifest["packages"][0]
    assert package["transport"] == {"type": "stdio"}
    assert len(package["environmentVariables"]) == 1
    api_key = package["environmentVariables"][0]
    assert api_key["name"] == "ZELINQA_API_KEY"
    assert api_key["isRequired"] is True
    assert api_key["isSecret"] is True
    assert api_key["format"] == "string"
    assert not {"value", "default", "choices", "variables"}.intersection(api_key)


def test_manifest_is_included_in_source_distribution() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    included = config["tool"]["hatch"]["build"]["targets"]["sdist"]["include"]
    assert "server.json" in included
