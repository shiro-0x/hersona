"""~/.hermes/config.yaml への安全な personality 書き込み。

`hermes config set` は ネスト YAML を破壊する (Pitfall 8) ため、
PyYAML で直接 config.yaml を読み書きする。

安全策:
- 書き込み前に <path>.bak を作成する
- 書き込み後に yaml.safe_load で妥当性を再検証する
- `agent.personalities` キーが存在しない場合は作成する
- 既存の personality キーは `overwrite=True` でのみ上書きする
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# PyYAML literal block scalar representer
# ---------------------------------------------------------------------------

class _LiteralStr(str):
    """PyYAML に literal block scalar (|) を強制するラッパー。"""


def _literal_presenter(dumper: yaml.Dumper, data: _LiteralStr) -> yaml.ScalarNode:
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")


# Dumper クラスに一度だけ登録
yaml.add_representer(_LiteralStr, _literal_presenter)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@dataclass
class ConfigWriteResult:
    """config.yaml 書き込み結果。"""

    config_path: Path
    backup_path: Path | None  # 上書き時のバックアップ先 (新規作成時は None)
    persona_name: str
    created: bool  # True = 新規挿入 / False = 既存エントリを上書き


def default_config_path() -> Path:
    """~/.hermes/config.yaml を返す。"""
    return Path.home() / ".hermes" / "config.yaml"


def write_personality(
    persona_name: str,
    blend_prompt: str,
    *,
    config_path: Path | None = None,
    overwrite: bool = False,
) -> ConfigWriteResult:
    """config.yaml の agent.personalities.<persona_name> に blend_prompt を書き込む。

    Args:
        persona_name: キー名 (例: ``tsundere_keigo_strong``)
        blend_prompt: SOUL.md / システムプロンプトに注入する文字列
        config_path: 書き込み先 (省略時は ``~/.hermes/config.yaml``)
        overwrite: 既存キーを上書きするか (False なら FileExistsError)

    Returns:
        ConfigWriteResult

    Raises:
        FileExistsError: overwrite=False かつ既にキーが存在する場合
        FileNotFoundError: config_path の親ディレクトリが存在しない場合
    """
    path = Path(config_path) if config_path is not None else default_config_path()

    if not path.parent.exists():
        raise FileNotFoundError(
            f"親ディレクトリが存在しません: {path.parent}。"
            f"先に作成してください (例: mkdir -p {path.parent})。"
        )

    # --- 既存ファイルを読み込む ---
    if path.exists():
        raw = path.read_text(encoding="utf-8")
        data: dict = yaml.safe_load(raw) or {}
    else:
        raw = ""
        data = {}

    # --- agent.personalities までのパスを保証 ---
    data.setdefault("agent", {})
    if data["agent"] is None:
        data["agent"] = {}
    data["agent"].setdefault("personalities", {})
    if data["agent"]["personalities"] is None:
        data["agent"]["personalities"] = {}

    personalities: dict = data["agent"]["personalities"]
    created = persona_name not in personalities

    if not created and not overwrite:
        raise FileExistsError(
            f"persona '{persona_name}' は既に {path} に存在します。"
            f"上書きするには --force を使用してください。"
        )

    # --- バックアップ ---
    backup_path: Path | None = None
    if path.exists():
        backup_path = path.with_suffix(".yaml.bak")
        shutil.copy2(path, backup_path)

    # --- 書き込み ---
    personalities[persona_name] = _LiteralStr(blend_prompt)
    out = yaml.dump(
        data,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )
    path.write_text(out, encoding="utf-8")

    # --- 書き込み後の妥当性確認 ---
    verified = yaml.safe_load(path.read_text(encoding="utf-8"))
    if (
        verified is None
        or "agent" not in verified
        or "personalities" not in verified.get("agent", {})
        or persona_name not in verified["agent"]["personalities"]
    ):
        # バックアップから復元してエラー
        if backup_path and backup_path.exists():
            shutil.copy2(backup_path, path)
        raise RuntimeError(
            f"config.yaml 書き込み後の検証に失敗しました。"
            f"バックアップ {backup_path} から復元しました。"
        )

    return ConfigWriteResult(
        config_path=path,
        backup_path=backup_path,
        persona_name=persona_name,
        created=created,
    )
