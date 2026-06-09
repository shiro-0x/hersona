"""属性のロードとブレンド合成 (attach / blend の core ロジック)。

公開 `attributes/` とユーザー名前空間 (`hersona.core.authoring.user_attributes_root`)
の両方から属性を解決し、複数属性を 1 つのシステムプロンプト注入ブロックに合成する。
Hermes スキルの `/hersona <category>/<name> [mode]` も CLI/TUI も本モジュールを使う。

ユーザー名前空間の同名属性は公開属性を上書きする (override_attribute の保存先)。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from hersona.core.authoring import user_attributes_root
from hersona.core.compatibility import CompatibilityMatrix, load_matrix
from hersona.core.weight import (
    WEIGHT_GUIDANCE,
    WeightLevel,
    catchphrase_subset,
    coerce_level,
)

PUBLIC_ATTRIBUTES_ROOT = Path(__file__).resolve().parent.parent.parent / "attributes"


@dataclass
class BlendResult:
    """ブレンド合成の結果。"""

    names: list[str]
    attributes: list[dict]
    conflicts: list[tuple[str, str]] = field(default_factory=list)
    prompt: str = ""


def available_attributes(
    *,
    public_root: Path | None = None,
    user_root: Path | None = None,
) -> dict[str, dict]:
    """利用可能な属性の {name: {category, source, path}} を返す。

    user 名前空間が公開属性と同名なら user を優先する。
    """
    pub = public_root or PUBLIC_ATTRIBUTES_ROOT
    usr = user_root or user_attributes_root()
    found: dict[str, dict] = {}
    for source, root in (("public", pub), ("user", usr)):
        if not root or not root.exists():
            continue
        for yml in sorted(root.rglob("*.yaml")):
            data = _safe_load(yml)
            if not isinstance(data, dict) or "attribute_name" not in data:
                continue
            name = data["attribute_name"]
            found[name] = {
                "category": data.get("attribute_category", ""),
                "source": source,
                "path": yml,
            }
    return found


def load_attribute(
    name: str,
    *,
    public_root: Path | None = None,
    user_root: Path | None = None,
) -> dict:
    """属性名から YAML を解決して dict を返す (user を公開より優先)。"""
    pub = public_root or PUBLIC_ATTRIBUTES_ROOT
    usr = user_root or user_attributes_root()
    # user を先に探索 (上書き優先)
    for root in (usr, pub):
        if not root or not root.exists():
            continue
        for yml in sorted(root.rglob("*.yaml")):
            data = _safe_load(yml)
            if isinstance(data, dict) and data.get("attribute_name") == name:
                return data
    raise KeyError(f"属性が見つかりません: '{name}'")


def render_blend(
    names: list[str],
    *,
    matrix: CompatibilityMatrix | None = None,
    public_root: Path | None = None,
    user_root: Path | None = None,
    weight: str | WeightLevel = WeightLevel.MODERATE,
) -> BlendResult:
    """複数属性をシステムプロンプト注入ブロックに合成する。

    ① 相性マトリクスで conflict を検出した場合は BlendResult.conflicts に格納する
    (ブロックには警告として併記する)。`weight` で強度 (none/mild/moderate/strong)
    を指定し、catchphrases の露出量と強度ガイダンスを調整する。
    """
    if not names:
        raise ValueError("少なくとも 1 属性を指定してください")

    attrs = [
        load_attribute(n, public_root=public_root, user_root=user_root) for n in names
    ]
    m = matrix or load_matrix(public_root)
    conflicts = m.check_blend([n for n in names if n in m.attributes])

    result = BlendResult(names=list(names), attributes=attrs, conflicts=conflicts)
    result.prompt = _render_prompt(attrs, conflicts, coerce_level(weight))
    return result


# --- 内部 ---------------------------------------------------------------


def _render_prompt(
    attrs: list[dict],
    conflicts: list[tuple[str, str]],
    level: WeightLevel,
) -> str:
    """属性群からシステムプロンプト注入ブロックを組み立てる。"""
    lines: list[str] = ["# hersona 属性ブレンド"]
    display = " + ".join(
        f"{a.get('attribute_category', '?')}/{a.get('attribute_name', '?')}" for a in attrs
    )
    lines.append(f"以下の属性を統合した人格として応答する: {display}")

    lines.append("")
    lines.append(f"## 強度: {level}")
    lines.append(WEIGHT_GUIDANCE[level])

    if conflicts:
        lines.append("")
        lines.append("⚠ conflict 検出 (不誠実さ過剰の可能性):")
        for a, b in conflicts:
            lines.append(f"  - {a} ⇔ {b}")

    core_traits = _merge_list(attrs, "core_traits")
    catchphrases = catchphrase_subset(_merge_list(attrs, "catchphrases"), level)
    sentence_endings = _merge_list(attrs, "sentence_endings")
    second_person = _first_str(attrs, "second_person")
    tones = [a["tone"] for a in attrs if a.get("tone")]

    if core_traits:
        lines.append("")
        lines.append("## core_traits")
        lines.extend(f"- {t}" for t in core_traits)
    if second_person:
        lines.append("")
        lines.append(f"## 二人称: {second_person}")
    if sentence_endings:
        lines.append("")
        lines.append("## 語尾: " + " / ".join(sentence_endings))
    if catchphrases:
        lines.append("")
        lines.append("## catchphrases")
        lines.extend(f"- {c}" for c in catchphrases)
    if tones:
        lines.append("")
        lines.append("## tone")
        lines.extend(f"- {t}" for t in tones)

    return "\n".join(lines)


def _merge_list(attrs: list[dict], key: str) -> list[str]:
    """複数属性の list フィールドを順序保持で重複排除して結合する。"""
    out: list[str] = []
    seen: set[str] = set()
    for a in attrs:
        for item in a.get(key, []) or []:
            if item not in seen:
                seen.add(item)
                out.append(item)
    return out


def _first_str(attrs: list[dict], key: str) -> str:
    for a in attrs:
        value = a.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _safe_load(path: Path) -> object:
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError:
        return None
