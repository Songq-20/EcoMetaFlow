"""Tests for built-in requirements.yaml loading."""

import pytest

from ecometa_flow.config import MODULE_NAMES
from ecometa_flow.requirements import (
    get_module_requirements,
    list_all_tools_and_databases,
    load_requirements,
)


def test_load_requirements_has_all_modules() -> None:
    data = load_requirements()
    modules = data.get("modules", {})
    for name in MODULE_NAMES:
        assert name in modules
        assert "tools" in modules[name]
        assert "databases" in modules[name]


def test_virus_prediction_requirements() -> None:
    req = get_module_requirements("virus_prediction")
    assert "trimmomatic" in req["tools"]
    assert "checkv_db" in req["databases"]


def test_unknown_module_raises() -> None:
    with pytest.raises(ValueError, match="Unknown module"):
        get_module_requirements("nonexistent_module")


def test_list_all_tools_and_databases() -> None:
    all_req = list_all_tools_and_databases()
    assert "trimmomatic" in all_req["tools"]
    assert len(all_req["tools"]) > 0
    assert len(all_req["databases"]) > 0
