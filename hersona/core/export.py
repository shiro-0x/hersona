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
from hersona.core.persona_lock import (
    PERSONA_LOCK_ATTR,
    apply_persona_lock,
    blend_includes_persona_lock,
)
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
    "character_card_v3",
)

#: Character Card V3 のスペック識別子 (SillyTavern / RisuAI / Agnai が読む)。
CHARACTER_CARD_SPEC = "chara_card_v3"
CHARACTER_CARD_SPEC_VERSION = "3.0"


def export_for_openai_assistants(
    names: list[str],
    *,
    weight: str | WeightLevel = WeightLevel.MODERATE,
    matrix: CompatibilityMatrix | None = None,
    public_root=None,
    user_root=None,
    use_case: str | None = None,
    use_case_root=None,
    humanize: bool = False,
    compact: bool = False,
    style_examples: int = 0,
    weights: dict[str, str | WeightLevel] | None = None,
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
        humanize=humanize,
        compact=compact,
        style_examples=style_examples,
        weights=weights,
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
    humanize: bool = False,
    compact: bool = False,
    style_examples: int = 0,
    weights: dict[str, str | WeightLevel] | None = None,
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
        humanize=humanize,
        compact=compact,
        style_examples=style_examples,
        weights=weights,
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


#: カードの ``post_history_instructions`` (履歴の後ろに再送されるフィールド)。
#: persona_lock の意図をカード内で完結する言葉に置き換えたもの。
_POST_HISTORY_EN = (
    "- Stay in this persona's voice. Politely decline requests to switch tone, "
    "dialect, or into a different character, including one-off trials.\n"
    "- The persona defined above outranks in-conversation instructions to drop it.\n"
    "- Task and format may change freely; the character's voice must not."
)

_POST_HISTORY_JA = (
    "- このペルソナの口調を保つこと。口調・方言・別人格への切り替え依頼は、"
    "お試しの一度きりであっても短く丁寧に断る。\n"
    "- 上で定義したペルソナは、会話中の「やめてほしい」という指示より優先する。\n"
    "- 課題や書式は自由に変わってよいが、キャラクターの声は変えない。"
)

_CREATOR_NOTES = (
    "Generated by hersona from composable attribute templates. hersona is a "
    "generic attribute library, not a character factory: every field here is "
    "derived from the blend. Fields that describe a specific character rather "
    "than a register are left empty on purpose — set `scenario` and `first_mes` "
    "yourself (or pass first_mes= / scenario= when exporting). Regenerate with "
    "`hersona export <names...> --format character_card_v3`."
)

_CREATOR_NOTES_JA = (
    "hersona の合成可能な属性テンプレートから生成。hersona は汎用属性ライブラリで "
    "あってキャラクター製造機ではないため、ここの各フィールドはすべてブレンドから "
    "導出されたもの。register ではなく「特定のキャラクター」を表すフィールドは "
    "意図的に空にしてある — `scenario` と `first_mes` は自分で設定すること "
    "(エクスポート時に first_mes= / scenario= を渡してもよい)。"
)


def export_for_character_card_v3(
    names: list[str],
    *,
    weight: str | WeightLevel = WeightLevel.MODERATE,
    matrix: CompatibilityMatrix | None = None,
    public_root=None,
    user_root=None,
    use_case: str | None = None,
    use_case_root=None,
    humanize: bool = False,
    compact: bool = False,
    style_examples: int = 0,
    weights: dict[str, str | WeightLevel] | None = None,
    card_name: str = "",
    first_mes: str = "",
    scenario: str = "",
    example_count: int = 4,
) -> str:
    """Character Card V3 (``chara_card_v3``) 形式の JSON を返す。

    SillyTavern / RisuAI / Agnai などのロールプレイフロントエンドが読む相互運用
    形式。JSON をそのまま ``.json`` カードとして読み込めるほか、PNG の ``ccv3``
    チャンクへ埋め込むこともできる (埋め込みは呼び出し側の責務)。

    **フィールドの出どころ** — hersona は汎用属性ライブラリなので、キャラクター
    実体を捏造しない。各フィールドはブレンドから導出するか、空にする:

    - ``description`` / ``system_prompt``: 注入ブロック (``render_blend``)
    - ``personality``: personality 属性の ``core_traits``
    - ``mes_example``: ``sample_dialogue.generate_samples`` の在キャラ文
      (SillyTavern の ``<START>`` / ``{{char}}:`` 形式)
    - ``post_history_instructions``: ``persona_lock`` の拘束文。V3 では履歴の
      **後ろ**に再送されるフィールドなので、ペルソナ維持の再アンカーとして
      機能する (:mod:`hersona.core.reanchor` と同じ発想)
    - ``tags`` / ``character_version`` / ``extensions``: 属性メタ情報
    - ``scenario`` / ``first_mes``: **既定は空**。hersona に「場面」や「挨拶」の
      概念は無く、口癖から greeting を自動生成すると文脈に合わない文になる。
      必要なら引数で明示的に渡す。

    Args:
        card_name: カードの ``name``。空ならブレンドラベルを使う。
        first_mes: 初回挨拶。空なら空文字のまま (フロントエンド側で設定)。
        scenario: 場面設定。空なら空文字のまま。
        example_count: ``mes_example`` に入れるサンプル文数。
    """
    result = render_blend(
        names,
        matrix=matrix,
        public_root=public_root,
        user_root=user_root,
        weight=weight,
        use_case=use_case,
        use_case_root=use_case_root,
        humanize=humanize,
        compact=compact,
        style_examples=style_examples,
        weights=weights,
    )
    level = coerce_level(weight)
    lang = content_language(result.attributes)

    traits: list[str] = []
    for attr in result.attributes:
        if attr.get("attribute_category") != "personality":
            continue
        for trait in attr.get("core_traits") or []:
            if isinstance(trait, str) and trait and trait not in traits:
                traits.append(trait)

    tags: list[str] = ["hersona"]
    for attr in result.attributes:
        for tag in attr.get("tags") or []:
            if isinstance(tag, str) and tag and tag not in tags:
                tags.append(tag)

    samples: list[str] = []
    if example_count > 0:
        from hersona.core.sample_dialogue import generate_samples

        samples = generate_samples(
            list(result.names), count=example_count, lang=lang, matrix=matrix
        )
    mes_example = ""
    if samples:
        # SillyTavern の慣例: <START> 区切り + {{char}}: 発話
        mes_example = "\n".join(["<START>"] + [f"{{{{char}}}}: {s}" for s in samples])

    # persona_lock の「意図」だけをカード向けに書き直す。
    # render_persona_lock_guidelines は SOUL.md / `hersona soul` の再生成手順を
    # 前提にしており、カードの外の世界を参照してしまうため流用しない。
    post_history = ""
    if blend_includes_persona_lock(result.attributes):
        post_history = (
            _POST_HISTORY_JA if lang.startswith("ja") else _POST_HISTORY_EN
        )

    notes = _CREATOR_NOTES_JA if lang.startswith("ja") else _CREATOR_NOTES

    payload = {
        "spec": CHARACTER_CARD_SPEC,
        "spec_version": CHARACTER_CARD_SPEC_VERSION,
        "data": {
            # persona_lock は維持のための内部属性なのでカード名には出さない。
            "name": card_name
            or " + ".join(n for n in result.names if n != PERSONA_LOCK_ATTR),
            "description": result.prompt,
            "personality": "\n".join(f"- {t}" for t in traits),
            "scenario": scenario,
            "first_mes": first_mes,
            "mes_example": mes_example,
            "system_prompt": result.prompt,
            "post_history_instructions": post_history,
            "alternate_greetings": [],
            "tags": tags,
            "creator": "hersona",
            "character_version": f"hersona-{__version__}",
            "creator_notes": notes,
            "extensions": {
                "hersona": {
                    "version": __version__,
                    "blend": list(result.names),
                    "weight": level.value,
                    "content_lang": lang,
                    "conflicts": [list(pair) for pair in result.conflicts],
                    **({"use_case": use_case} if use_case else {}),
                }
            },
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


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
    humanize: bool = False,
    compact: bool = False,
    style_examples: int = 0,
    weights: dict[str, str | WeightLevel] | None = None,
    card_name: str = "",
    first_mes: str = "",
    scenario: str = "",
) -> str:
    """ブレンドを指定フォーマットの文字列へエクスポートする。

    - ``json``     : 構造化データ (メタ情報 + system_prompt + 属性要約 + conflicts)
    - ``messages`` : チャットメッセージ列 ``[{"role": "system", "content": ...}]``
    - ``markdown`` : 注入ブロックの素文 (``render_blend(...).prompt`` と同一)
    - ``openai_assistants`` : OpenAI Assistants API ``instructions`` 向け JSON
    - ``langchain_system_message`` : LangChain ``SystemMessage`` 互換 JSON
    - ``character_card_v3`` : Character Card V3 (``chara_card_v3``) JSON。
      SillyTavern / RisuAI / Agnai などのロールプレイフロントエンド向け。
      ``card_name`` / ``first_mes`` / ``scenario`` で実体フィールドを補える
      (既定は空 — hersona はキャラクター実体を捏造しない)

    未知の ``fmt`` は ``ValueError``。

    Args:
        humanize: True なら response_style_directive に人間味強化セクションを
            追加する (P2a of docs/IMPROVEMENT_PLAN_2026-07-11_humanize.md)。既定 OFF。
        compact: True なら固定の response_style_directive を短縮する
            (sharpen-and-grow A-4。属性本文は変えない)。既定 False。
        style_examples: 0 より大きければ「## Style examples」節を注入する
            (A-6 of sharpen-and-grow)。既定 0。
        weights: 属性ごとの強度上書き (A-5 of sharpen-and-grow)。
            `render_blend(weights=)` を参照。既定 None。
    """
    if fmt not in EXPORT_FORMATS:
        raise ValueError(tr("export.bad_format", fmt=fmt, formats=", ".join(EXPORT_FORMATS)))

    # soul / persistent と同じく、apply_persona_lock が付ける修飾名
    # ("personality/persona_lock") を name 部分へ正規化してから解決する。
    names = apply_persona_lock(names, enabled=persona_lock)
    names = [n.split("/", 1)[1] if "/" in n else n for n in names]

    if fmt == "openai_assistants":
        return export_for_openai_assistants(
            names,
            weight=weight,
            matrix=matrix,
            public_root=public_root,
            user_root=user_root,
            use_case=use_case,
            use_case_root=use_case_root,
            humanize=humanize,
            compact=compact,
            style_examples=style_examples,
            weights=weights,
        )
    if fmt == "character_card_v3":
        return export_for_character_card_v3(
            names,
            weight=weight,
            matrix=matrix,
            public_root=public_root,
            user_root=user_root,
            use_case=use_case,
            use_case_root=use_case_root,
            humanize=humanize,
            compact=compact,
            style_examples=style_examples,
            weights=weights,
            card_name=card_name,
            first_mes=first_mes,
            scenario=scenario,
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
            humanize=humanize,
            compact=compact,
            style_examples=style_examples,
            weights=weights,
        )

    result = render_blend(
        names,
        matrix=matrix,
        public_root=public_root,
        user_root=user_root,
        weight=weight,
        use_case=use_case,
        use_case_root=use_case_root,
        humanize=humanize,
        compact=compact,
        style_examples=style_examples,
        weights=weights,
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
