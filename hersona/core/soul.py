"""SOUL.md 永続化 (ROADMAP §⑤ / docs/soul_md_persistence.md)。

hersona blend を Hermes One 公式の `SOUL.md` 形式に変換し、
`~/.hermes/profiles/<name>/SOUL.md` に書き出す。

公式 4 要素:
- Name
- Personality
- Tone
- Behavioral Guidelines

設計方針:
- core 共有: 合成は `attach.render_blend` に委譲し、本モジュールは整形と IO のみ。
- フレームワーク非依存: SOUL.md は plain Markdown テキストで出力。
- 安全: 既存ファイルは既定で上書き拒否 ( `overwrite=True` / `force=True` で許可)。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from hersona import __version__
from hersona.core.attach import catchphrase_usage_directive, render_blend
from hersona.core.compatibility import CompatibilityMatrix
from hersona.core.intensity import content_language
from hersona.core.persona_lock import (
    apply_persona_lock,
    blend_includes_persona_lock,
    merge_memory_persona_lock,
    persona_lock_meta_comment,
    render_persona_lock_guidelines,
)
from hersona.core.use_cases import load_use_case, render_use_case_block
from hersona.core.weight import WeightLevel, coerce_level, normalize_catchphrase

#: Marker that separates hersona-generated sections from user-edited tail.
#: Anything below this line is preserved across `write_soul_preserving_tail`
#: regenerations, including the `## Operating Mode:` block and free-form notes.
GEN_END_MARKER = "<!-- hersona:gen-end -->"

# Hermes One の SOUL.md 公式 4 要素にマップする既定の第一人称/二人称。
# Name フラグで上書き可能。ブレンドの speech 属性が first_person / second_person を
# 持つ場合はそちらを優先する (英語ペルソナに「私」が注入されるのを防ぐ)。
_DEFAULT_NAME = "Libra"
_DEFAULT_FIRST_PERSON = "私"
_DEFAULT_SECOND_PERSON = "あなた / きみ"
_DEFAULT_FIRST_PERSON_EN = "I"
_DEFAULT_SECOND_PERSON_EN = "you"

_MEMORY_KEY_RE = re.compile(r"^[a-z0-9_]{1,32}$")
_MAX_MEMORY_KEYS = 16
_MAX_MEMORY_VALUE_LEN = 512

# LLM へのフレーミングディレクティブ: 記事の知見「会話ターンと参考情報を分離」「最新値を優先」に対応。
_RECENT_CONTEXT_DIRECTIVE = (
    "> **[背景情報]** 以下は直近の文脈メモ。会話のターンや発言としてではなく背景情報として参照すること。\n"
    "> 否定・変化がある場合は最後に記録された値を現在の状態とする。関連する場合のみ参照すること。"
)


@dataclass
class SoulRenderResult:
    """SOUL.md レンダリング結果。"""

    content: str  # ファイルに書き出す markdown 文字列
    output_path: Path  # 書き込み予定のパス
    blend_names: list[str]
    weight: WeightLevel
    lang: str
    name: str
    memory: dict[str, str] | None = None
    use_case: str | None = None


def default_soul_path(profile: str = "default") -> Path:
    """Local Hermes CLI が実際に読む SOUL.md パスを返す。

    Local Hermes CLI の prompt_builder は `get_hermes_home() / "SOUL.md"`
    (`~/.hermes/SOUL.md`) を読む。profile 別パス
    (`~/.hermes/profiles/<profile>/SOUL.md`) は Hermes One 専用で
    Local CLI には反映されない。

    `profile` 引数は後方互換のため残す。

    Args:
        profile: 互換性のために残す引数 (現在は無視される)

    Returns:
        `~/.hermes/SOUL.md`
    """
    return Path.home() / ".hermes" / "SOUL.md"


def render_soul(
    names: list[str],
    *,
    weight: str | WeightLevel = WeightLevel.MODERATE,
    name: str = _DEFAULT_NAME,
    matrix: CompatibilityMatrix | None = None,
    public_root=None,
    user_root=None,
    title: str | None = None,
    intro: list[str] | None = None,
    agent_label: str | None = "Hermes Agent",
    memory: dict[str, str] | None = None,
    use_case: str | None = None,
    use_case_root: Path | None = None,
    persona_lock: bool = True,
) -> str:
    """blend を SOUL.md 形式の markdown 文字列にレンダリングする。

    Args:
        names: 適用する属性名 (例: `["personality/tsundere", "speech/keigo"]`)
        weight: 強度 (none / mild / moderate / strong)
        name: SOUL.md Name セクションの表示名
        matrix: 相性マトリクス (省略時自動ロード)
        public_root / user_root: 属性解決パス (テスト用)
        title: 先頭見出し (省略時は Hermes SOUL.md の既定見出し)
        intro: 見出し直下の引用 (blockquote) 行 (省略時は Hermes 既定)
        agent_label: Name セクションの「正式名称」ラベル (None なら行を省略)
        use_case: Optional Operating Mode / use-case prompt pack ID.

    Returns:
        SOUL.md 形式の markdown 文字列

    Raises:
        ValueError: blend が空 / conflict 検出
        KeyError: 存在しない属性

    Note:
        sharpen-and-grow A-4 の ``compact`` (response_style_directive 短縮) は
        本関数には無い。SOUL.md 本文は ``blend.prompt`` を使わず属性フィールド
        (``rules`` / ``notes`` / ``behavioral_guidelines`` 等) から直接組み立てる
        ため、短縮の対象になる文がそもそも含まれない。``render_blend`` /
        ``export_blend`` / ``run_persistent`` (Hermes config.yaml ブロック) 側の
        ``compact`` を使うこと。
    """
    if not names:
        raise ValueError("blend が空です (names は 1 つ以上必要)")

    names = apply_persona_lock(names, enabled=persona_lock)

    # CLI と同じ正規化: `<category>/<name>` 形式なら name 部分だけ取り出す
    norm_names = [_normalize_name(n) for n in names]

    level = coerce_level(weight)
    blend = render_blend(
        norm_names,
        matrix=matrix,
        public_root=public_root,
        user_root=user_root,
        weight=level,
    )

    if blend.conflicts:
        # 公式 SOUL.md は人格の「正本」になるため、conflict は警告で済ませず拒否する。
        # (multi モードの挙動と整合)
        raise ValueError(
            f"blend に conflict 検出: {blend.conflicts}。SOUL.md 化は安全のため中止します。"
        )

    lang = content_language(blend.attributes)
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    blend_str = ", ".join(names)
    blend_meta = f"<!-- generated by hersona v{__version__} at {timestamp} -->\n"
    blend_meta += f"<!-- blend: {blend_str} -->\n"
    blend_meta += f"<!-- weight: {level.value} / lang: {lang} -->\n"
    if use_case:
        blend_meta += f"<!-- use_case: {use_case} -->\n"
    blend_meta += "<!-- DO NOT EDIT: regenerate via `hersona soul ...` -->\n"
    blend_meta += persona_lock_meta_comment(enabled=persona_lock)

    body = _render_soul_body(
        blend=blend,
        weight=level,
        name=name,
        lang=lang,
        title=title,
        intro=intro,
        agent_label=agent_label,
    )
    if use_case:
        # use_case は attrs 同様に決定的 (memory/timestamp のような可変要素ではない)
        # ため、可変部より前 (安定 prefix 側) に置く。
        mode = load_use_case(use_case, root=use_case_root)
        body = f"{body.rstrip()}\n\n---\n\n{render_use_case_block(mode).rstrip()}"

    # A-4 part 2 (sharpen-and-grow): 安定 prefix (固定ディレクティブ + 属性本文 +
    # use_case) → 可変部 (memory / Recent Context / タイムスタンプ) の順に配置し、
    # プロンプトキャッシュの境界 (先頭からの一致) を属性本文側で最大化する。
    # かつては blend_meta が先頭にあり、regenerate のたびに 1 バイト目から変わっていた。
    memory = _validate_memory(memory)
    lang_for_memory = content_language(blend.attributes)
    memory = merge_memory_persona_lock(memory, enabled=persona_lock, lang=lang_for_memory)
    variable_tail = ""
    if memory:
        ctx = _render_recent_context(memory)
        rc_header = f"## Recent Context (as of {timestamp})"
        variable_tail += f"\n\n{rc_header}\n\n{ctx}"
    if lang.startswith("ja"):
        footer = f"_作成: {timestamp} / hersona v{__version__} + Hermes One 公式仕様準拠_"
    else:
        footer = f"_Generated {timestamp} / hersona v{__version__} (Hermes One SOUL.md spec)_"
    variable_tail += f"\n\n---\n\n{footer}"
    return f"{body.rstrip()}{variable_tail}\n\n{blend_meta.rstrip()}\n{GEN_END_MARKER}\n"


def write_soul(
    output: str | Path,
    names: list[str],
    *,
    weight: str | WeightLevel = WeightLevel.MODERATE,
    name: str = _DEFAULT_NAME,
    matrix: CompatibilityMatrix | None = None,
    public_root=None,
    user_root=None,
    append: bool = False,
    overwrite: bool = False,
    force: bool = False,
    memory: dict[str, str] | None = None,
    use_case: str | None = None,
    use_case_root: Path | None = None,
    persona_lock: bool = True,
) -> SoulRenderResult:
    """blend を SOUL.md 形式で `output` に書き出す。

    Args:
        output: 出力パス
        names: 適用する属性名
        weight: 強度
        name: SOUL.md Name セクションの表示名
        matrix: 相性マトリクス
        public_root / user_root: 属性解決パス
        append: True なら追記モード (既存ファイルに "## 追記" セクションを追加)
        overwrite: True なら上書きを許可
        force: True なら --force 相当 (確認なし)

    Returns:
        SoulRenderResult (content / output_path / blend_names / weight / lang / name)

    Raises:
        FileExistsError: 既存ファイルがあり overwrite=False の場合
        FileNotFoundError: 親ディレクトリが存在しない
        ValueError: blend が空 / conflict 検出

    Note:
        ``compact`` (sharpen-and-grow A-4) は無い。理由は ``render_soul`` の
        docstring を参照 (SOUL.md 本文は ``response_style_directive`` を含まない)。
    """
    output_path = Path(output)
    if not output_path.parent.exists():
        raise FileNotFoundError(
            f"親ディレクトリが存在しません: {output_path.parent}。"
            "profile ディレクトリを先に作成してください (hermes profile create 等)。"
        )

    if output_path.exists() and not overwrite and not force and not append:
        raise FileExistsError(
            f"SOUL.md が既に存在します: {output_path}。"
            "上書きするには overwrite=True / force=True を使うか、append=True で追記してください。"
        )

    validated_memory = _validate_memory(memory)
    applied_names = apply_persona_lock(names, enabled=persona_lock)
    content = render_soul(
        applied_names,
        weight=weight,
        name=name,
        matrix=matrix,
        public_root=public_root,
        user_root=user_root,
        memory=validated_memory,
        use_case=use_case,
        use_case_root=use_case_root,
        persona_lock=persona_lock,
    )

    if not append and output_path.exists() and (overwrite or force):
        content = _merge_preserved_tail(content, output_path.read_text(encoding="utf-8"))

    if append and output_path.exists():
        # 追記モード: 既存ファイル末尾に "## 追記" セクションを追加
        timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        blend_str = ", ".join(names)
        level = coerce_level(weight)
        appended = (
            f"\n\n---\n\n## 追記 ({timestamp})\n\n"
            f"_以下の blend を `hersona soul ... --append` で追記: {blend_str} (weight={level.value})_\n\n"
            f"{content}\n"
        )
        with open(output_path, "a", encoding="utf-8") as f:
            f.write(appended)
    else:
        # 上書きモード
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

    return SoulRenderResult(
        content=content,
        output_path=output_path,
        blend_names=list(applied_names),
        weight=coerce_level(weight),
        lang=_detect_lang_from_names(
            names, matrix=matrix, public_root=public_root, user_root=user_root
        ),
        name=name,
        memory=validated_memory,
        use_case=use_case,
    )


def resolve_memory(
    *,
    memory: dict[str, str] | None = None,
    memory_file: str | Path | None = None,
) -> dict[str, str] | None:
    """Resolve caller-supplied memory from inline dict or JSON file."""
    if memory is not None and memory_file is not None:
        raise ValueError("--memory and --memory-file are mutually exclusive")
    if memory_file is not None:
        with open(memory_file, encoding="utf-8") as f:
            memory = json.load(f)
    return _validate_memory(memory)


def _merge_preserved_tail(new_content: str, old_content: str) -> str:
    """Preserve caller-owned text below ``GEN_END_MARKER`` across regeneration."""
    if GEN_END_MARKER not in old_content:
        return new_content
    tail = old_content.split(GEN_END_MARKER, 1)[1].strip()
    if not tail:
        return new_content
    return f"{new_content.rstrip()}\n\n{tail}\n"


def _detect_lang_from_names(
    names: list[str],
    *,
    matrix=None,
    public_root=None,
    user_root=None,
) -> str:
    """blend の先頭属性からコンテンツ言語を検出する (ヘルパー)。"""
    if not names:
        return "ja"
    norm = [_normalize_name(n) for n in names]
    blend = render_blend(
        norm, matrix=matrix, public_root=public_root, user_root=user_root
    )
    return content_language(blend.attributes)


def detect_lang_from_names(
    names: list[str],
    *,
    matrix=None,
    public_root=None,
    user_root=None,
) -> str:
    """Public wrapper: infer content language from a blend name list."""
    return _detect_lang_from_names(
        names, matrix=matrix, public_root=public_root, user_root=user_root
    )


# --- 内部 ---------------------------------------------------------------


def _normalize_name(name: str) -> str:
    """`<category>/<name>` 形式なら name 部分を返す (CLI と整合)。"""
    return name.split("/", 1)[1] if "/" in name else name


def _validate_memory(memory: dict | None) -> dict | None:
    """Validate caller-supplied memory dict (shape only; content is caller-owned)."""
    if memory is None:
        return None
    if not isinstance(memory, dict):
        raise ValueError(f"memory must be dict[str, str], got {type(memory).__name__}")
    if not memory:
        return None
    if len(memory) > _MAX_MEMORY_KEYS:
        raise ValueError(f"memory has {len(memory)} keys (> {_MAX_MEMORY_KEYS})")
    for key, value in memory.items():
        if not isinstance(key, str) or not _MEMORY_KEY_RE.match(key):
            raise ValueError(
                f"memory key invalid: {key!r} (must match {_MEMORY_KEY_RE.pattern})"
            )
        if not isinstance(value, str) or not value:
            raise ValueError(f"memory[{key!r}] must be non-empty str")
        if len(value) > _MAX_MEMORY_VALUE_LEN:
            raise ValueError(
                f"memory[{key!r}] length {len(value)} > {_MAX_MEMORY_VALUE_LEN}"
            )
    return memory


def _escape_memory_text(text: str) -> str:
    """Safelist markdown escape for user-supplied memory values."""
    replacements = (
        ("`", "\\`"),
        ("##", "\\#\\#"),
        ("[", "\\["),
        ("]", "\\]"),
        ("*", "\\*"),
        ("_", "\\_"),
    )
    escaped = text
    for old, new in replacements:
        escaped = escaped.replace(old, new)
    return escaped


def _render_recent_context(memory: dict[str, str]) -> str:
    """Assemble the Recent Context markdown block with framing directive."""
    lines: list[str] = [_RECENT_CONTEXT_DIRECTIVE, ""]
    for key, value in memory.items():
        safe_value = _escape_memory_text(value)
        lines.append(f"### {key}: {safe_value}")
    return "\n".join(lines)


_DEFAULT_TITLE = "# SOUL — Hermes Agent ペルソナ定義"
_DEFAULT_INTRO = [
    "> 公式仕様: hermesagents.cc の \"Soul\" スクリーン参照。",
    "> 含まれるべき 4 要素: name / personality / tone / behavioral guidelines。",
    "> 効果: 次回セッション開始時から即時反映。再起動不要。",
]

#: SOUL.md の章見出し・ラベル・プレースホルダの言語別テキスト。
#:
#: 本文 (core_traits / tone / catchphrases) は `content_i18n` で言語解決される一方、
#: 章の枠組みだけが日本語固定で残っていたため、`--lang en` + 英語 speech 属性でも
#: 「## 1. Name (エージェント名)」「**一人称**: 私」が英語ペルソナの CLAUDE.md /
#: AGENTS.md に注入されていた。ja 以外は en にフォールバックする
#: (`hersona.core.intensity` の表示言語解決と同じ割り切り)。
_SOUL_LABELS: dict[str, dict[str, str]] = {
    "ja": {
        "sec_name": "## 1. Name (エージェント名)",
        "display_name": "表示名",
        "formal_name": "正式名称",
        "persona_suffix": "ペルソナ",
        "first_person": "一人称",
        "second_person": "二人称",
        "sec_personality": "## 2. Personality (性格特性)",
        "no_personality": "(personality 属性が指定されていません)",
        "compat_heading": "### 2.x 互換 / 衝突 (他カテゴリ属性)",
        "sec_tone": "## 3. Tone (口調)",
        "no_speech": "(speech 属性が指定されていません)",
        "sec_behavior": "## 4. Behavioral Guidelines (行動指針)",
        "iron_rule": "鉄則",
        "weight_label": "強度",
        "blend_rules": "blend 共通の行動ルール",
        "no_rules": "(blend に明示的な行動ルールなし)",
        "persona_lock": "persona lock",
    },
    "en": {
        "sec_name": "## 1. Name",
        "display_name": "Display name",
        "formal_name": "Full name",
        "persona_suffix": "persona",
        "first_person": "First person",
        "second_person": "Second person",
        "sec_personality": "## 2. Personality",
        "no_personality": "(no personality attribute specified)",
        "compat_heading": "### 2.x Compatibility / conflicts (other categories)",
        "sec_tone": "## 3. Tone",
        "no_speech": "(no speech attribute specified)",
        "sec_behavior": "## 4. Behavioral Guidelines",
        "iron_rule": "Core rule",
        "weight_label": "intensity",
        "blend_rules": "Blend-wide behavioral rules",
        "no_rules": "(no explicit behavioral rules in this blend)",
        "persona_lock": "persona lock",
    },
}


def _labels(lang: str) -> dict[str, str]:
    """`lang` 用のラベル辞書 (ja 以外は en にフォールバック)。"""
    return _SOUL_LABELS["ja"] if lang.startswith("ja") else _SOUL_LABELS["en"]


def _render_soul_body(
    *,
    blend,
    weight: WeightLevel,
    name: str,
    lang: str,
    title: str | None = None,
    intro: list[str] | None = None,
    agent_label: str | None = "Hermes Agent",
) -> str:
    """SOUL.md の本文 (公式 4 要素) を組み立てる。"""
    lb = _labels(lang)
    lines: list[str] = [title if title is not None else _DEFAULT_TITLE]
    lines.append("")
    for intro_line in (intro if intro is not None else _DEFAULT_INTRO):
        lines.append(intro_line)
    lines.append("")

    # --- 1. Name ---
    lines.append(lb["sec_name"])
    lines.append("")
    lines.append(f"- **{lb['display_name']}**: {name}")
    if agent_label:
        lines.append(
            f"- **{lb['formal_name']}**: {agent_label} ({name} {lb['persona_suffix']})"
        )
    # 一人称/二人称は blend の speech 属性に宣言があればそれを使う。
    # 無い場合のみ言語別の既定値へ落とす (英語ペルソナに「私」を注入しないため)。
    first_person, second_person = _pronouns_for(blend.attributes, lang)
    lines.append(f"- **{lb['first_person']}**: {first_person}")
    lines.append(f"- **{lb['second_person']}**: {second_person}")
    lines.append("")

    # --- 2. Personality ---
    lines.append(lb["sec_personality"])
    lines.append("")
    personality_attrs = [
        a for a in blend.attributes if a.get("attribute_category") == "personality"
    ]
    if not personality_attrs:
        lines.append(lb["no_personality"])
        lines.append("")
    else:
        for attr in personality_attrs:
            attr_id = (
                f"{attr.get('attribute_category', '?')}/{attr.get('attribute_name', '?')}"
            )
            lines.append(f"### 2.{personality_attrs.index(attr) + 1} {attr_id}")
            lines.append("")
            desc = attr.get("description", "").strip()
            if desc:
                lines.append(f"> {desc}")
                lines.append("")
            # 言語拘束: content_i18n.<lang> があれば優先
            traits = _resolve_lang_field(attr, "core_traits", lang)
            if traits:
                lines.append("**core_traits**:")
                for t in traits:
                    lines.append(f"- {t}")
                lines.append("")

        # 互換 / 衝突 (archetype / visual / hobby もここに集約)
        other_attrs = [
            a for a in blend.attributes if a.get("attribute_category") != "personality"
        ]
        if other_attrs:
            lines.append(lb["compat_heading"])
            lines.append("")
            for attr in other_attrs:
                attr_id = (
                    f"{attr.get('attribute_category', '?')}/{attr.get('attribute_name', '?')}"
                )
                compat = attr.get("compatible_archetypes", []) or []
                conflicts = attr.get("conflicts_with", []) or []
                lines.append(f"- **{attr_id}**")
                if compat:
                    lines.append(f"  - compatible: {', '.join(compat)}")
                if conflicts:
                    lines.append(f"  - conflicts: {', '.join(conflicts)}")
            lines.append("")

    # --- 3. Tone ---
    lines.append(lb["sec_tone"])
    lines.append("")
    speech_attrs = [
        a for a in blend.attributes if a.get("attribute_category") == "speech"
    ]
    if not speech_attrs:
        lines.append(lb["no_speech"])
        lines.append("")
    else:
        for idx, attr in enumerate(speech_attrs, start=1):
            attr_id = (
                f"{attr.get('attribute_category', '?')}/{attr.get('attribute_name', '?')}"
            )
            lines.append(f"### 3.{idx} {attr_id}")
            lines.append("")
            tone = _resolve_lang_str(attr, "tone", lang)
            if tone:
                lines.append(f"**tone**: {tone}")
                lines.append("")
            catchphrases = _resolve_lang_field(attr, "catchphrases", lang)
            if catchphrases:
                lines.append("**catchphrases**:")
                for c in catchphrases:
                    nc = normalize_catchphrase(c)
                    if nc["when"]:
                        lines.append(f"- {nc['phrase']} — {nc['when']}")
                    else:
                        lines.append(f"- {nc['phrase']}")
                lines.append("")
                lines.append(catchphrase_usage_directive(lang))
                lines.append("")
            endings = _resolve_lang_field(attr, "sentence_endings", lang)
            if endings:
                lines.append(f"**sentence_endings**: {' / '.join(endings)}")
                lines.append("")
    lines.append("")

    # --- 4. Behavioral Guidelines ---
    lines.append(lb["sec_behavior"])
    lines.append("")
    lines.append(f"### 4.1 {lb['iron_rule']} ({lb['weight_label']}: {weight.value})")
    lines.append("")
    lines.append(_weight_guidelines_for(weight, lang))
    lines.append("")
    lines.append(f"### 4.2 {lb['blend_rules']}")
    lines.append("")
    rules: list[str] = []
    for attr in blend.attributes:
        rules.extend(_extract_behavior_rules(attr, lang))
    if rules:
        # 重複排除 (順序保持)
        seen: set[str] = set()
        for r in rules:
            if r not in seen:
                seen.add(r)
                lines.append(f"- {r}")
    else:
        lines.append(f"- {lb['no_rules']}")
    lines.append("")

    if blend_includes_persona_lock(blend.attributes):
        lines.append(f"### 4.3 {lb['persona_lock']} ({lb['weight_label']}: strong)")
        lines.append("")
        for rule in render_persona_lock_guidelines(lang):
            lines.append(rule)
        lines.append("")

    return "\n".join(lines)


def _resolve_lang_field(attr: dict, key: str, lang: str) -> list[str]:
    """content_i18n.<lang>.<key> があれば優先、なければ BASE の key を返す。"""
    i18n = attr.get("content_i18n", {}) or {}
    localized = i18n.get(lang, {}) or {}
    value = localized.get(key)
    if value:
        return list(value)
    return list(attr.get(key, []) or [])


def _resolve_lang_str(attr: dict, key: str, lang: str) -> str:
    """content_i18n.<lang>.<key> があれば優先、なければ BASE の key を返す (str 版)。"""
    i18n = attr.get("content_i18n", {}) or {}
    localized = i18n.get(lang, {}) or {}
    value = localized.get(key)
    if isinstance(value, str) and value:
        return value
    base = attr.get(key, "")
    return base if isinstance(base, str) else ""


def _pronouns_for(attrs: list[dict], lang: str) -> tuple[str, str]:
    """ブレンドの属性から (一人称, 二人称) を解決する。

    属性が `first_person` / `second_person` を宣言していればそれを使い、
    無ければ言語別の既定値へ落とす。英語 speech 属性 (`british_en` 等) は
    `first_person` を持たないため、既定値が日本語固定だと英語ペルソナの
    CLAUDE.md に「一人称: 私」が入ってしまっていた。
    """
    ja = lang.startswith("ja")
    first = _first_str(attrs, "first_person") or (
        _DEFAULT_FIRST_PERSON if ja else _DEFAULT_FIRST_PERSON_EN
    )
    second = _first_str(attrs, "second_person") or (
        _DEFAULT_SECOND_PERSON if ja else _DEFAULT_SECOND_PERSON_EN
    )
    return first, second


def _first_str(attrs: list[dict], key: str) -> str:
    """`attrs` を順に見て、最初に見つかった非空の文字列フィールドを返す。"""
    for attr in attrs:
        value = attr.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


_WEIGHT_GUIDANCE: dict[str, dict[WeightLevel, str]] = {
    "ja": {
        WeightLevel.NONE: "- 特性として質的にのみ効かせる。口癖・語尾の顕在化は最小限。",
        WeightLevel.MILD: "- ほのかに滲ませる。catchphrases は時折、語尾は控えめに。",
        WeightLevel.MODERATE: "- 標準的な強度。catchphrases と語尾を自然な頻度で用いる。",
        WeightLevel.STRONG: "- 明確に顕在化させる。catchphrases を多用し、語尾・一人称を徹底。",
    },
    "en": {
        WeightLevel.NONE: (
            "- Let the traits show only qualitatively; keep catchphrases and "
            "speech markers to a minimum."
        ),
        WeightLevel.MILD: (
            "- Keep it subtle: catchphrases occasionally, speech markers restrained."
        ),
        WeightLevel.MODERATE: (
            "- Standard intensity: use catchphrases and speech markers at a natural "
            "frequency."
        ),
        WeightLevel.STRONG: (
            "- Make it unmistakable: use catchphrases freely and hold the speech "
            "markers and first person consistently."
        ),
    },
}


def _weight_guidelines_for(weight: WeightLevel, lang: str = "ja") -> str:
    """強度別の行動ガイドライン (SOUL.md 用、ja 以外は en)。"""
    table = _WEIGHT_GUIDANCE["ja"] if lang.startswith("ja") else _WEIGHT_GUIDANCE["en"]
    return table[weight]


def _attr_content_lang(attr: dict) -> str:
    """属性のコンテンツ言語 (`content_lang` 未指定は ja 扱い、load_matrix と同じ規約)。"""
    return attr.get("content_lang") or "ja"


def _extract_behavior_rules(attr: dict, lang: str = "ja") -> list[str]:
    """属性の behavioral_guidelines / rules / notes から行動ルール文字列を抽出。

    `content_i18n.<lang>.<key>` があればそれを優先する。無い場合は、属性の
    コンテンツ言語が `lang` と一致するときだけ採用する — 一致しない場合に
    生の値を使うと、英語ペルソナの CLAUDE.md / AGENTS.md の
    「Blend-wide behavioral rules」に日本語の `notes` がそのまま流れ込む。
    """
    rules: list[str] = []
    i18n = attr.get("content_i18n", {}) or {}
    localized = i18n.get(lang, {}) or {}
    same_lang = _attr_content_lang(attr) == lang
    for key in ("behavioral_guidelines", "rules", "notes"):
        value = localized.get(key)
        if value is None:
            if not same_lang:
                # この言語向けの訳が無く、属性の言語も違う → 混入させない。
                continue
            value = attr.get(key)
        if isinstance(value, str) and value:
            for line in value.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    rules.append(line)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    rules.append(item.strip())
    return rules
