"""ブレンドの可搬エクスポート (ROADMAP C: 他エージェント対応 / LangGraph 等)。

`render_blend` の結果を、他のエージェントフレームワーク (LangGraph / LangChain /
OpenAI / Anthropic SDK 等) がそのまま取り込める形へ変換する core ロジック。

設計方針:
- **core 再利用**: 合成は `attach.render_blend` に委譲し、本モジュールは整形のみ。
- **フレームワーク非依存**: 特定 SDK に依存しない。`json` は構造化データ、
  `messages` はチャットメッセージ列 (role=system)、`markdown` は注入ブロック素文。
  どのフレームワークでも `messages` をそのまま、もしくは `json` から自前で組める。
"""
from __future__ import annotations

import json

from hersona import __version__
from hersona.core.attach import render_blend
from hersona.core.compatibility import CompatibilityMatrix
from hersona.core.i18n import tr
from hersona.core.intensity import content_language
from hersona.core.weight import WeightLevel, coerce_level

# エクスポート対象に含める属性フィールド (人格を再構成できる最小集合)。
_LIST_FIELDS = ("core_traits", "catchphrases", "sentence_endings", "lexical_markers", "tags")
_SCALAR_FIELDS = ("second_person", "first_person", "register", "tone", "speech_style")

EXPORT_FORMATS = ("json", "messages", "markdown")


def _attribute_summary(attr: dict) -> dict:
    """1 属性をエクスポート用の要約 dict にする (空フィールドは省略)。"""
    out: dict[str, object] = {
        "name": attr.get("attribute_name", ""),
        "category": attr.get("attribute_category", ""),
    }
    for key in _LIST_FIELDS:
        value = attr.get(key)
        if value:
            out[key] = list(value)
    for key in _SCALAR_FIELDS:
        value = attr.get(key)
        if value:
            out[key] = value
    return out


def export_blend(
    names: list[str],
    *,
    weight: str | WeightLevel = WeightLevel.MODERATE,
    fmt: str = "json",
    matrix: CompatibilityMatrix | None = None,
    public_root=None,
    user_root=None,
) -> str:
    """ブレンドを指定フォーマットの文字列へエクスポートする。

    - ``json``     : 構造化データ (メタ情報 + system_prompt + 属性要約 + conflicts)
    - ``messages`` : チャットメッセージ列 ``[{"role": "system", "content": ...}]``
    - ``markdown`` : 注入ブロックの素文 (``render_blend(...).prompt`` と同一)

    未知の ``fmt`` は ``ValueError``。
    """
    if fmt not in EXPORT_FORMATS:
        raise ValueError(tr("export.bad_format", fmt=fmt, formats=", ".join(EXPORT_FORMATS)))

    result = render_blend(
        names,
        matrix=matrix,
        public_root=public_root,
        user_root=user_root,
        weight=weight,
    )
    level = coerce_level(weight)

    if fmt == "markdown":
        return result.prompt

    if fmt == "messages":
        return json.dumps(
            [{"role": "system", "content": result.prompt}],
            ensure_ascii=False,
            indent=2,
        )

    # fmt == "json"
    payload = {
        "hersona": {
            "version": __version__,
            "names": list(result.names),
            "weight": level.value,
            "content_lang": content_language(result.attributes),
        },
        "system_prompt": result.prompt,
        "conflicts": [[a, b] for a, b in result.conflicts],
        "attributes": [_attribute_summary(a) for a in result.attributes],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
