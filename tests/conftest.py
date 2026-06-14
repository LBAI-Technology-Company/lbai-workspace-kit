from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from tests.helpers.workspace import create_isolated_workspace, fixtures_root, kit_root

sys.dont_write_bytecode = True


@pytest.fixture
def kit() -> Path:
    return kit_root()


@pytest.fixture
def fixtures() -> Path:
    return fixtures_root()


@pytest.fixture
def load_fixture(fixtures):
    def _load(name: str) -> dict:
        path = fixtures / 'enrichments' / name
        return json.loads(path.read_text(encoding='utf-8'))

    return _load


@pytest.fixture
def write_fixture(tmp_path):
    def _write(name: str, data: dict) -> Path:
        path = tmp_path / name
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        return path

    return _write


@pytest.fixture
def isolated_workspace(tmp_path):
    return create_isolated_workspace(tmp_path)


@pytest.fixture
def tools_path(isolated_workspace):
    return isolated_workspace / 'lbai_system' / 'tools'
