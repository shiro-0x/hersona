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
from hersona.core.persona_lock import apply_persona_lock
from hersona.core.weight import WeightLevel, coerce_level

# エクスポート対象に含める属性フィールド (人格を再構成できる最小集合)。
_LIST_FIELDS = ("core_traits", "catchphrases", "sentence_endings", "lexical_markers", "tags")
_SCALAR_FIELDS = ("second_person", "first_person", "register", "tone", "speech_style")

EXPORT_FORMATS = (
    "json",
    "messages",
    "markdown",
    "openai_assistants",
    "langchain_system_message",
)


def export_for_openai_assistants(
    names: list[str],
    *,
    weight: str | WeightLevel = WeightLevel.MODERATE,
    matrix: CompatibilityMatrix | None = None,
    public_root=None,
    user_root=None,
    use_case: str | None = None,
    use_case_root=None,
) -> str:
    """OpenAI Assistants API の ``instructions`` フィールド向け JSON を返す。

    ``render_blend(...).prompt`` を ``instructions`` に、メタ情報を ``metadata`` に
    ``hersona_*`` プレフィックス付きで格納する。OpenAI Python SDK や
    HTTP API へそのまま渡せる。``first_mes`` / ``scenario`` /
    ``character_book`` などの「固定キャラ」フィールドは一切生成しない
    (hersona の generic 属性 library 方針を維持)。
    """
    result = render_blend(
        names,
        matrix=matrix,
        public_root=public_root,
        user_root=user_root,
        weight=weight,
        use_case=use_case,
        use_case_root=use_case_root,
    )
    level = coerce_level(weight)
    # OpenAI Assistants API の metadata は string → string の dict (各値最大 512 chars)
    # list / dict / number は不可。hersona_blend / hersona_conflicts は構造化データ
    # なので JSON 文字列化して格納する (v1.4.1 fix)。
    payload = {
        "model": "gpt-4o",
        "instructions": result.prompt,
        "name": "hersona-blend",
        "metadata": {
            "hersona_version": __version__,
            "hersona_blend": json.dumps(list(result.names)),
            "hersona_weight": level.value,
            "hersona_content_lang": content_language(result.attributes),
            "hersona_conflicts": json.dumps([list(pair) for pair in result.conflicts]),
        },
    }
    if use_case:
        payload["metadata"]["hersona_use_case"] = use_case
    return json.dumps(payload, ensure_ascii=False, indent=2)


def export_for_langchain_system_message(
    names: list[str],
    *,
    weight: str | WeightLevel = WeightLevel.MODERATE,
    matrix: CompatibilityMatrix | None = None,
    public_root=None,
    user_root=None,
    use_case: str | None = None,
    use_case_root=None,
) -> str:
    """LangChain ``SystemMessage`` 互換 JSON を返す。

    ``langchain.schema.SystemMessage(content=...)`` の ``content`` に
    ``render_blend(...).prompt`` を入れ、``type="system"`` /
    ``additional_kwargs={}`` / ``response_metadata`` に hersona 情報を格納する。
    LangChain Python SDK の ``SystemMessage.parse_raw()`` または手動 dict 渡し
    で取り込める。Tool definitions 等は合成しない (generic 維持)。
    """
    result = render_blend(
        names,
        matrix=matrix,
        public_root=public_root,
        user_root=user_root,
        weight=weight,
        use_case=use_case,
        use_case_root=use_case_root,
    )
    level = coerce_level(weight)
    payload = {
        "type": "system",
        "content": result.prompt,
        "additional_kwargs": {},
        "response_metadata": {
            "hersona_version": __version__,
            "hersona_blend": list(result.names),
            "hersona_weight": level.value,
            "hersona_content_lang": content_language(result.attributes),
        },
    }
    if use_case:
        payload["response_metadata"]["hersona_use_case"] = use_case
    return json.dumps(payload, ensure_ascii=False, indent=2)


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
    use_case: str | None = None,
    use_case_root=None,
    persona_lock: bool = True,
) -> str:
    """ブレンドを指定フォーマットの文字列へエクスポートする。

    - ``json``     : 構造化データ (メタ情報 + system_prompt + 属性要約 + conflicts)
    - ``messages`` : チャットメッセージ列 ``[{"role": "system", "content": ...}]``
    - ``markdown`` : 注入ブロックの素文 (``render_blend(...).prompt`` と同一)
    - ``openai_assistants`` : OpenAI Assistants API ``instructions`` 向け JSON
    - ``langchain_system_message`` : LangChain ``SystemMessage`` 互換 JSON

    未知の ``fmt`` は ``ValueError``。
    """
    if fmt not in EXPORT_FORMATS:
        raise ValueError(tr("export.bad_format", fmt=fmt, formats=", ".join(EXPORT_FORMATS)))

    names = apply_persona_lock(names, enabled=persona_lock)

    if fmt == "openai_assistants":
        return export_for_openai_assistants(
            names,
            weight=weight,
            matrix=matrix,
            public_root=public_root,
            user_root=user_root,
            use_case=use_case,
            use_case_root=use_case_root,
        )
    if fmt == "langchain_system_message":
        return export_for_langchain_system_message(
            names,
            weight=weight,
            matrix=matrix,
            public_root=public_root,
            user_root=user_root,
            use_case=use_case,
            use_case_root=use_case_root,
        )

    result = render_blend(
        names,
        matrix=matrix,
        public_root=public_root,
        user_root=user_root,
        weight=weight,
        use_case=use_case,
        use_case_root=use_case_root,
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
    if use_case:
        payload["hersona"]["use_case"] = use_case
    return json.dumps(payload, ensure_ascii=False, indent=2)
