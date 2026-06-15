"""hersona.core.config_writer の回帰テスト。"""
from __future__ import annotations

import pytest
import yaml

from hersona.core.config_writer import ConfigWriteResult, write_personality

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _read(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 新規ファイル作成
# ---------------------------------------------------------------------------


def test_creates_new_file(tmp_path):
    cfg = tmp_path / "config.yaml"
    result = write_personality("tsundere_strong", "prompt text", config_path=cfg)
    assert cfg.exists()
    data = _read(cfg)
    assert data["agent"]["personalities"]["tsundere_strong"] == "prompt text"
    assert isinstance(result, ConfigWriteResult)
    assert result.created is True
    assert result.backup_path is None  # 新規作成なのでバックアップなし


def test_creates_nested_keys_when_agent_absent(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("other_key: value\n", encoding="utf-8")
    write_personality("my_persona", "hello", config_path=cfg)
    data = _read(cfg)
    assert data["other_key"] == "value"
    assert data["agent"]["personalities"]["my_persona"] == "hello"


def test_literal_block_scalar_written(tmp_path):
    """multiline プロンプトが literal block scalar (| or |-) で書き出されること。"""
    cfg = tmp_path / "config.yaml"
    prompt = "line1\nline2\nline3"
    write_personality("persona", prompt, config_path=cfg)
    raw = cfg.read_text(encoding="utf-8")
    # PyYAML は | または |- を使う (chomping モードによる)
    assert "| " in raw or "|\n" in raw or "|-\n" in raw
    data = _read(cfg)
    assert data["agent"]["personalities"]["persona"].strip() == prompt


# ---------------------------------------------------------------------------
# 既存ファイルへの追記
# ---------------------------------------------------------------------------


def test_appends_to_existing_personalities(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "agent:\n  personalities:\n    existing: old prompt\n", encoding="utf-8"
    )
    write_personality("new_persona", "new prompt", config_path=cfg)
    data = _read(cfg)
    assert data["agent"]["personalities"]["existing"] == "old prompt"
    assert data["agent"]["personalities"]["new_persona"] == "new prompt"


def test_backup_created_on_existing_file(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("agent:\n  personalities: {}\n", encoding="utf-8")
    result = write_personality("p", "x", config_path=cfg)
    assert result.backup_path is not None
    assert result.backup_path.exists()


# ---------------------------------------------------------------------------
# 上書き保護
# ---------------------------------------------------------------------------


def test_raises_on_duplicate_without_overwrite(tmp_path):
    cfg = tmp_path / "config.yaml"
    write_personality("persona", "v1", config_path=cfg)
    with pytest.raises(FileExistsError, match="persona"):
        write_personality("persona", "v2", config_path=cfg)


def test_overwrite_replaces_value(tmp_path):
    cfg = tmp_path / "config.yaml"
    write_personality("persona", "v1", config_path=cfg)
    result = write_personality("persona", "v2", config_path=cfg, overwrite=True)
    assert result.created is False
    data = _read(cfg)
    assert data["agent"]["personalities"]["persona"] == "v2"


# ---------------------------------------------------------------------------
# 親ディレクトリ不在
# ---------------------------------------------------------------------------


def test_raises_when_parent_missing(tmp_path):
    cfg = tmp_path / "nonexistent_dir" / "config.yaml"
    with pytest.raises(FileNotFoundError, match="親ディレクトリ"):
        write_personality("p", "x", config_path=cfg)


# ---------------------------------------------------------------------------
# null / 空 YAML の扱い
# ---------------------------------------------------------------------------


def test_handles_empty_file(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("", encoding="utf-8")
    write_personality("p", "prompt", config_path=cfg)
    data = _read(cfg)
    assert data["agent"]["personalities"]["p"] == "prompt"


def test_handles_null_agent_key(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("agent:\n", encoding="utf-8")
    write_personality("p", "prompt", config_path=cfg)
    data = _read(cfg)
    assert data["agent"]["personalities"]["p"] == "prompt"


# ---------------------------------------------------------------------------
# run_persistent との統合
# ---------------------------------------------------------------------------


def test_run_persistent_auto_config(tmp_path, monkeypatch):
    """run_persistent(auto_config=True) が config.yaml を自動書き込みすること。"""
    monkeypatch.setenv("HERSONA_USER_DIR", str(tmp_path / "userattrs"))
    cfg = tmp_path / "config.yaml"
    profile_dir = tmp_path / "profiles" / "default"
    profile_dir.mkdir(parents=True)

    from hersona.core.persistent import run_persistent

    result = run_persistent(
        ["tsundere"],
        weight="mild",
        profile=str(profile_dir),
        auto_config=True,
        config_path=cfg,
        force=True,
    )
    assert result.config_write_result is not None
    data = _read(cfg)
    assert "tsundere_mild" in data["agent"]["personalities"]


def test_run_persistent_auto_config_false_does_not_write(tmp_path, monkeypatch):
    """auto_config=False (既定) では config.yaml を書かないこと。"""
    monkeypatch.setenv("HERSONA_USER_DIR", str(tmp_path / "userattrs"))
    cfg = tmp_path / "config.yaml"
    profile_dir = tmp_path / "profiles" / "default"
    profile_dir.mkdir(parents=True)

    from hersona.core.persistent import run_persistent

    result = run_persistent(
        ["tsundere"],
        weight="mild",
        profile=str(profile_dir),
        auto_config=False,
        config_path=cfg,
        force=True,
    )
    assert result.config_write_result is None
    assert not cfg.exists()
