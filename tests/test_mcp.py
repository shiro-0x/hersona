"""hersona MCP サーバー (hersona.mcp) の回帰テスト (ROADMAP C / M3)。

純粋ロジック (tools.py) は mcp SDK 非依存で全面テストする。server.py は mcp
未インストール時に導入手順付き RuntimeError を送出することのみ検証する
(CI には mcp を入れないため、配線本体は実行しない)。
"""
from __future__ import annotations

import pytest

from hersona.mcp import tools
from tests.catalog_counts import TOTAL_PUBLIC_ATTRIBUTES


@pytest.fixture(autouse=True)
def _isolate_user_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("HERSONA_USER_DIR", str(tmp_path / "userattrs"))


# --- tools.list_attributes --------------------------------------------------


def test_list_attributes_total_and_categories() -> None:
    out = tools.list_attributes()
    assert out["total"] == TOTAL_PUBLIC_ATTRIBUTES
    cats = out["categories"]
    assert set(cats) == {"personality", "speech", "archetype", "visual", "hobby"}
    names = [a["name"] for a in cats["personality"]]
    assert "tsundere" in names
    # each entry carries a source marker
    assert all("source" in a for a in cats["speech"])


# --- tools.show_attribute ---------------------------------------------------


def test_show_attribute_resolves_meta() -> None:
    out = tools.show_attribute("tsundere")
    assert out["name"] == "tsundere"
    assert out["category"] == "personality"
    assert out["display_name"]
    assert out["description"]
    assert out["core_traits"]
    assert out["catchphrases"]


def test_show_attribute_first_person_surfaced() -> None:
    out = tools.show_attribute("ore_boy")
    assert out.get("first_person")  # B4 field exposed


def test_show_attribute_unknown_raises() -> None:
    with pytest.raises(KeyError):
        tools.show_attribute("no_such_attr_xyz")


# --- tools.blend ------------------------------------------------------------


def test_blend_returns_prompt_and_conflicts() -> None:
    out = tools.blend(["tsundere", "keigo"], weight="strong")
    assert out["names"] == ["tsundere", "keigo"]
    assert out["weight"] == "strong"
    assert out["content_lang"] == "ja"
    assert out["conflicts"] == []
    assert "hersona" in out["system_prompt"]


def test_blend_reports_conflicts() -> None:
    out = tools.blend(["airhead", "intellectual"])
    assert ["airhead", "intellectual"] in out["conflicts"]


# --- tools.export -----------------------------------------------------------


def test_export_delegates_to_core() -> None:
    import json

    raw = tools.export(["tsundere"], weight="mild", fmt="messages")
    msgs = json.loads(raw)
    assert msgs[0]["role"] == "system"


# --- tools.recommend_blend --------------------------------------------------


def test_recommend_blend_returns_blend() -> None:
    out = tools.recommend_blend({"distance": 1, "speech": 0, "role": 1})
    assert isinstance(out["blend"], list) and out["blend"]
    assert out["summary"]
    assert out["weight_suggestion"] in {"none", "mild", "moderate", "strong"}
    assert isinstance(out["ranked"], list)
    assert "export" not in out  # export_format 未指定なら含めない


def test_recommend_blend_with_export_format() -> None:
    import json

    out = tools.recommend_blend(
        {"distance": 1, "speech": 0, "role": 1}, export_format="openai_assistants"
    )
    payload = json.loads(out["export"])
    assert payload["instructions"]
    # v1.8.0: export 経路は persona_lock を既定で付加するため、metadata の blend は
    # 推薦結果 + persona_lock になる。
    assert json.loads(payload["metadata"]["hersona_blend"]) == [*out["blend"], "persona_lock"]


# --- tools.compatibility ----------------------------------------------------


def test_compatibility_single_attribute() -> None:
    out = tools.compatibility("tsundere")
    assert out["name"] == "tsundere"
    assert isinstance(out["conflicts_with"], list)
    assert isinstance(out["compatible_with"], list)


def test_compatibility_full_matrix() -> None:
    out = tools.compatibility()
    assert isinstance(out, dict)
    assert "tsundere" in out["attributes"]


# --- server.py: mcp 未インストール時の挙動 ----------------------------------


def test_build_server_raises_without_mcp(monkeypatch) -> None:
    """mcp 未インストールなら build_server は導入手順付き RuntimeError を送出する。"""
    import builtins

    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "mcp" or name.startswith("mcp."):
            raise ImportError("simulated missing mcp")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    from hersona.mcp.server import build_server

    with pytest.raises(RuntimeError) as excinfo:
        build_server()
    assert "hersona[mcp]" in str(excinfo.value)


def test_server_module_imports_without_mcp() -> None:
    """server モジュール自体は mcp 非依存で import できる (lazy import)。"""
    import hersona.mcp.server as srv

    assert hasattr(srv, "build_server")
    assert hasattr(srv, "main")
