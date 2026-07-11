"""属性のロードとブレンド合成 (attach / blend の core ロジック)。

公開 `attributes/` とユーザー名前空間 (`hersona.core.authoring.user_attributes_root`)
の両方から属性を解決し、複数属性を 1 つのシステムプロンプト注入ブロックに合成する。
Hermes スキルの `/hersona <category>/<name> [mode]` も CLI/TUI も本モジュールを使う。

ユーザー名前空間の同名属性は公開属性を上書きする (override_attribute の保存先)。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from hersona.core.authoring import user_attributes_root
from hersona.core.compatibility import CompatibilityMatrix, load_matrix
from hersona.core.i18n import tr
from hersona.core.intensity import content_language, resolve_content_field
from hersona.core.paths import public_attributes_root
from hersona.core.use_cases import load_use_case, render_use_case_block
from hersona.core.weight import (
    WEIGHT_GUIDANCE,
    WeightLevel,
    catchphrase_subset,
    coerce_level,
    normalize_catchphrase,
)

PUBLIC_ATTRIBUTES_ROOT = public_attributes_root()


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


def _split_qualified(name: str) -> tuple[str | None, str]:
    """'<category>/<name>' 形式を (category, name) に分解する (非修飾なら category=None)。"""
    if "/" in name:
        cat, base = name.split("/", 1)
        return cat, base
    return None, name


def load_attribute(
    name: str,
    *,
    public_root: Path | None = None,
    user_root: Path | None = None,
) -> dict:
    """属性名から YAML を解決して dict を返す (user を公開より優先)。

    ``name`` は非修飾 (``tsundere``) と修飾 (``personality/tsundere``) の両方を
    受理する。修飾時は category も一致する属性だけを返す (apply_persona_lock 等が
    修飾名を生成するため、core 単体でも解決できるようにする)。
    """
    pub = public_root or PUBLIC_ATTRIBUTES_ROOT
    usr = user_root or user_attributes_root()
    cat, base = _split_qualified(name)
    # user を先に探索 (上書き優先)
    for root in (usr, pub):
        if not root or not root.exists():
            continue
        for yml in sorted(root.rglob("*.yaml")):
            data = _safe_load(yml)
            if (
                isinstance(data, dict)
                and data.get("attribute_name") == base
                and (cat is None or data.get("attribute_category") == cat)
            ):
                return data
    raise KeyError(tr("core.attr_not_found", name=name))


def render_blend(
    names: list[str],
    *,
    matrix: CompatibilityMatrix | None = None,
    public_root: Path | None = None,
    user_root: Path | None = None,
    weight: str | WeightLevel = WeightLevel.MODERATE,
    use_case: str | None = None,
    use_case_root: Path | None = None,
    humanize: bool = False,
    compact: bool = False,
    style_examples: int = 0,
) -> BlendResult:
    """複数属性をシステムプロンプト注入ブロックに合成する。

    ① 相性マトリクスで conflict を検出した場合は BlendResult.conflicts に格納する
    (ブロックには警告として併記する)。`weight` で強度 (none/mild/moderate/strong)
    を指定し、catchphrases の露出量と強度ガイダンスを調整する。

    Args:
        humanize: True なら response_style_directive に人間味強化セクション
            (削る + 偏らせる) を追加する (P2a of docs/IMPROVEMENT_PLAN_2026-07-11_humanize.md)。
            既定 OFF。compact ↔ standard ↔ humanize のプロファイル軸の一部。
            想定追加コスト +60-90 tok/ターン。
        compact: True なら固定の response_style_directive を意味を保ったまま
            短縮する (sharpen-and-grow A-4。属性本文・catchphrases 等は変えない)。
            既定 False。humanize と併用可 (短縮した基底部 + humanize 節)。
        style_examples: 0 より大きければ、speech > personality > archetype > visual > hobby
            の優先順で attrs の ``examples`` から N 件を few-shot の口調参照として注入する
            (A-6, sharpen-and-grow)。既定 0 (現状維持)。オウム返し防止の一文は
            response_style_directive に集約される (節ごとに directive を増やさない)。
            想定追加コスト +45〜60 tok/属性。
    """
    if not names:
        raise ValueError(tr("core.blend_empty"))

    attrs = [
        load_attribute(n, public_root=public_root, user_root=user_root) for n in names
    ]
    m = matrix or load_matrix(public_root)
    # conflict 判定は非修飾名で行う (修飾名はマトリクスのキーに存在しない)
    base_names = [_split_qualified(n)[1] for n in names]
    conflicts = m.check_blend([n for n in base_names if n in m.attributes])

    result = BlendResult(names=list(names), attributes=attrs, conflicts=conflicts)
    result.prompt = _render_prompt(
        attrs,
        conflicts,
        coerce_level(weight),
        humanize=humanize,
        compact=compact,
        style_examples=style_examples,
    )
    if use_case:
        mode = load_use_case(use_case, root=use_case_root)
        result.prompt = result.prompt + "\n\n" + render_use_case_block(mode).rstrip()
    return result


# --- 内部 ---------------------------------------------------------------


def _render_prompt(
    attrs: list[dict],
    conflicts: list[tuple[str, str]],
    level: WeightLevel,
    humanize: bool = False,
    compact: bool = False,
    style_examples: int = 0,
) -> str:
    """属性群からシステムプロンプト注入ブロックを組み立てる。

    Args:
        humanize: `render_blend(humanize=)` から透過。response_style_directive に
            人間味強化セクションを追加する (P2a)。
        compact: `render_blend(compact=)` から透過。response_style_directive を
            短縮版に切り替える (A-4)。
        style_examples: `render_blend(style_examples=)` から透過。0 より大きければ
            「## Style examples」節を末尾に追加する (A-6)。
    """
    lines: list[str] = ["# hersona attribute blend"]
    display = " + ".join(
        f"{a.get('attribute_category', '?')}/{a.get('attribute_name', '?')}" for a in attrs
    )
    lines.append(f"Respond as a single persona composed from these attributes: {display}")
    lines.append(_language_directive(attrs))

    lang = content_language(attrs)
    # 言語束縛コンテンツ (core_traits / catchphrases / tone) は人格の content_lang へ解決する
    # (W1 Step 2)。content_i18n.<lang> があればネイティブ版を使い、無ければ除外して
    # 当該言語での自前生成を指示する (W1 Step 1 の挙動を内包)。
    core_traits, _ = _resolve_merge(attrs, "core_traits", lang)
    merged_catchphrases, dropped_catchphrases = _resolve_catchphrases(attrs, lang)
    catchphrases = catchphrase_subset(merged_catchphrases, level)
    tones = _resolve_tones(attrs, lang)
    sentence_endings = _merge_list(attrs, "sentence_endings")
    second_person = _first_str(attrs, "second_person")
    first_person = _first_str(attrs, "first_person")
    lexical_markers = _merge_list(attrs, "lexical_markers")
    speech_styles = _merge_str_list(attrs, "speech_style")
    style_example_lines = _collect_style_examples(attrs, lang, style_examples)

    lines.append("")
    lines.append(f"## Intensity: {level}")
    lines.append(WEIGHT_GUIDANCE[level])
    # 自然さ・反復防止・口癖/語尾の使い方を 1 つに統合 (毎ターンの注入コスト削減)。
    # blend ディレクティブは複数属性のときだけ出す (単一属性での固定費削減)。
    lines.append(
        response_style_directive(
            lang,
            has_catchphrases=bool(catchphrases),
            has_sentence_endings=bool(sentence_endings),
            is_blend=len(attrs) > 1,
            humanize=humanize,
            compact=compact,
            has_style_examples=bool(style_example_lines),
        )
    )

    if conflicts:
        lines.append("")
        lines.append("⚠ Conflicts detected (the persona may become incoherent or over-insincere):")
        for a, b in conflicts:
            lines.append(f"  - {a} ⇔ {b}")

    if core_traits:
        lines.append("")
        lines.append("## core_traits")
        lines.extend(f"- {t}" for t in core_traits)
    if second_person:
        lines.append("")
        lines.append(f"## Second person: {second_person}")
    if first_person:
        # measure_intensity は first_person を採点軸に使う。注入して整合させる。
        # 複数 speech 属性の一人称混在は人格を壊すため first-wins (second_person と同様)。
        lines.append("")
        lines.append(f"## First person: {first_person}")
    if sentence_endings:
        lines.append("")
        lines.append("## Sentence endings: " + " / ".join(sentence_endings))
    if lexical_markers:
        # en speech の intensity 主軸。注入して measure と整合させる。
        lines.append("")
        lines.append("## Lexical markers: " + " / ".join(lexical_markers))
    if speech_styles:
        lines.append("")
        lines.append("## speech_style")
        lines.extend(f"- {s}" for s in speech_styles)
    if catchphrases:
        lines.append("")
        lines.append("## catchphrases")
        for c in catchphrases:
            if c["when"]:
                lines.append(f"- {c['phrase']} — {c['when']}")
            else:
                lines.append(f"- {c['phrase']}")
    if dropped_catchphrases:
        lines.append("")
        lines.append(_native_catchphrase_directive(lang))
    if tones:
        lines.append("")
        lines.append("## tone")
        lines.extend(f"- {t}" for t in tones)
    if style_example_lines:
        # A-6: 末尾追加 (キャッシュ prefix を壊さない。A-4 と同じレイアウト規律)。
        lines.append("")
        lines.append("## Style examples (tone reference — never reuse these lines verbatim)")
        lines.extend(f"- {ex}" for ex in style_example_lines)

    return "\n".join(lines)


def _language_directive(attrs: list[dict]) -> str:
    """人格コンテンツの言語に基づく応答言語の指示行を返す (設計書 §3.4)。

    語彙・語尾が言語束縛のため、応答言語をコンテンツ言語に固定する。
    """
    lang = content_language(attrs)
    if lang == "ja":
        return "Respond in Japanese. This persona's vocabulary, sentence endings, and catchphrases are native Japanese style material."
    return f"Respond in English (this persona's content language is '{lang}')."


def _resolve_merge(attrs: list[dict], key: str, lang: str) -> tuple[list[str], bool]:
    """言語拘束 list フィールドを lang に解決し、順序保持で結合する (W1 Step 2)。

    各属性を ``resolve_content_field`` で解決し、ネイティブ版のみ採用する。
    BASE しか無く lang と不一致だった属性があれば ``dropped=True`` を返す。
    """
    out: list[str] = []
    seen: set[str] = set()
    dropped = False
    for a in attrs:
        value, native = resolve_content_field(a, key, lang)
        if not value:
            continue
        if not native:
            dropped = True
            continue
        for item in value:
            if item not in seen:
                seen.add(item)
                out.append(item)
    return out, dropped


def _resolve_catchphrases(attrs: list[dict], lang: str) -> tuple[list[dict], bool]:
    """catchphrases を lang に解決し、正規化した dict リストを返す (B: トリガ注記対応)。

    _resolve_merge の catchphrases 専用版。重複排除は phrase で行う。
    戻り値: ``(normalized_catchphrases, dropped)``
    """
    out: list[dict] = []
    seen: set[str] = set()
    dropped = False
    for a in attrs:
        value, native = resolve_content_field(a, "catchphrases", lang)
        if not value:
            continue
        if not native:
            dropped = True
            continue
        for item in value:
            nc = normalize_catchphrase(item)
            phrase = nc["phrase"]
            if phrase and phrase not in seen:
                seen.add(phrase)
                out.append(nc)
    return out, dropped


def _resolve_tones(attrs: list[dict], lang: str) -> list[str]:
    """tone (str) を lang に解決し、ネイティブ版のみ順序保持で集約する。"""
    out: list[str] = []
    for a in attrs:
        value, native = resolve_content_field(a, "tone", lang)
        if value and native and value not in out:
            out.append(value)
    return out


# A-6 (sharpen-and-grow): examples の few-shot 注入。speech > personality の優先順
# (sample_dialogue.py の既存ロジックと同型)。
_EXAMPLE_CATEGORY_PRIORITY = ("speech", "personality", "archetype", "visual", "hobby")

# examples の authoring 形式は 2 通り混在する:
# 1. 素文形式 (1 要素 = 1 発話。例: kansai_ben, casual_en)
# 2. weight 実演形式 (`# N) ...` コメント + `[user]`/`[assistant]` 対話ブロック。
#    カタログの過半数がこちら) — [assistant] 行のみが「そのキャラの発話」
_ASSISTANT_LINE_RE = re.compile(r"^\s*\[assistant\]\s*(.+)$", re.MULTILINE)


def _extract_example_lines(raw_examples: list[str]) -> list[str]:
    """1 属性の examples から「そのキャラの発話」だけを抽出する (上記 2 形式を吸収)。"""
    lines: list[str] = []
    for raw in raw_examples:
        if not isinstance(raw, str):
            continue
        matches = _ASSISTANT_LINE_RE.findall(raw)
        if matches:
            lines.extend(m.strip() for m in matches if m.strip())
        else:
            text = raw.strip()
            if text:
                lines.append(text)
    return lines


def _collect_style_examples(attrs: list[dict], lang: str, count: int) -> list[str]:
    """ブレンド内の attrs から examples を優先順 (speech > personality > ...) で集め、
    count 件返す (A-6)。lang にネイティブな examples のみ採用する
    (catchphrases / core_traits と同じ「non-native は除外」規律)。
    """
    if count <= 0:
        return []
    by_cat: dict[str, list[dict]] = {c: [] for c in _EXAMPLE_CATEGORY_PRIORITY}
    unknown: list[dict] = []
    for a in attrs:
        cat = a.get("attribute_category", "")
        (by_cat[cat] if cat in by_cat else unknown).append(a)
    ordered = [a for cat in _EXAMPLE_CATEGORY_PRIORITY for a in by_cat[cat]] + unknown

    pool: list[str] = []
    seen: set[str] = set()
    for a in ordered:
        raw, native = resolve_content_field(a, "examples", lang)
        if not raw or not native:
            continue
        for line in _extract_example_lines(raw):
            if line not in seen:
                seen.add(line)
                pool.append(line)
    return pool[:count]


def catchphrase_usage_directive(lang: str) -> str:
    """口癖の整合性優先ルール (A: 会話成立のためのガード)。

    口癖を「丸写しの枕詞」ではなく「場面が合うときだけ使う言い回しの例」として
    扱わせ、会話の意味・流れを口癖より優先させる。状況に合わない口癖を無理に
    挿入して文意や文法を壊すことを防ぐ。
    """
    if lang in ("ja", "en"):
        return (
            "Note on catchphrases: treat the items above as example phrasings of this "
            "persona, not fixed lines to insert verbatim. Use one only when the situation "
            "fits, and skip it otherwise. Always prioritize the meaning and flow of the "
            "conversation; never break grammar or sense to force a catchphrase in."
        )
    return (
        f"Note on catchphrases: use them only when the situation fits, generated natively "
        f"in '{lang}'. Prioritize conversational sense over inserting a catchphrase."
    )


def response_style_directive(
    lang: str,
    *,
    has_catchphrases: bool,
    has_sentence_endings: bool,
    is_blend: bool = True,
    humanize: bool = False,
    compact: bool = False,
    has_style_examples: bool = False,
) -> str:
    """応答スタイルの統合ガイド (自然さ + 反復防止 + 口癖/語尾の使い方)。

    旧 persona_naturalness / sentence_ending_variation / catchphrase_usage の 3 つを
    1 つにまとめ、注入ブロックの毎ターンコストを削減する (会話が重くなる対策)。
    口癖・語尾セクションが無いときは該当節を省く。``is_blend=False`` (単一属性) の
    ときは属性間の口癖適応ルールも省く (単一属性セッションの固定費削減)。個別関数は
    後方互換のため残す (soul.py の SOUL.md 生成等で引き続き使用)。

    Args:
        humanize: True なら §2 の手癖抑制 + 偏り付与の二部構成を末尾に追加する
            (P2a of docs/IMPROVEMENT_PLAN_2026-07-11_humanize.md)。既定 OFF。
            想定追加コスト +60-90 tok/ターン。プロファイル軸:
            compact ↔ standard ↔ humanize。
        compact: True なら同じ 4 つの制約 (自己語り禁止 / 口癖・語尾のレパートリー
            運用 / ブレンド時の適応 / ターン間の反復防止) を保ったまま、より短い
            言い回しに差し替える (sharpen-and-grow A-4。意味を削らず文字数だけ削る)。
            実測: tsundere+keigo ブレンドで 664 文字 → 約 300 文字前後 (-55% 程度)。
            humanize と併用可 (短縮した基底部 + humanize 節)。
        has_style_examples: True なら「## Style examples」節 (A-6, sharpen-and-grow)
            が注入されている旨を踏まえ、オウム返し防止の一文を追加する。
            節ごとに directive を増やさない規律 (CLAUDE.md) に従い、既存の
            response_style_directive に集約する。
    """
    if lang not in ("ja", "en"):
        if compact:
            base = (
                f"Note on response style: embody traits via action, not self-description; "
                f"vary openings/endings across replies in '{lang}'."
            )
        else:
            base = (
                f"Note on response style: embody traits through action, not self-description; "
                f"skip preamble; vary openings and endings across replies in '{lang}'."
            )
        if has_style_examples:
            base += " The style examples are a tone reference only — never reuse their wording."
        if humanize:
            humanize_section = _humanize_directive(lang)
            if humanize_section:
                return base + "\n\n" + humanize_section
        return base

    if compact:
        parts = ["Embody traits via word choice/attitude, not self-narration or preamble."]
        if has_catchphrases and has_sentence_endings:
            parts.append(
                " Treat catchphrases/endings as a repertoire — use only when fitting, "
                "vary them, never force ungrammatically."
            )
        elif has_sentence_endings:
            parts.append(" Treat endings as a repertoire — vary them, don't fix one per sentence.")
        elif has_catchphrases:
            parts.append(" Treat catchphrases as a repertoire — use only when fitting, never forced.")
        if is_blend and (has_catchphrases or has_sentence_endings):
            parts.append(
                " In blends, adapt catchphrases to the speech attribute's register instead "
                "of quoting verbatim."
            )
        if has_style_examples:
            parts.append(
                " Style examples below are tone reference only — never reuse verbatim."
            )
        parts.append(" Vary openings and rhythm across replies.")
        base = "Note on response style: " + "".join(parts)
    else:
        parts = [
            "Embody personality and tone through word choice and attitude; never narrate "
            "your own traits or add preamble like 'I'll now tell you…'."
        ]
        if has_catchphrases and has_sentence_endings:
            parts.append(
                " Treat catchphrases and sentence endings as a repertoire, not fixed lines: "
                "use one only when it fits, don't stamp the same ending on every sentence, and "
                "never break grammar or conversational sense to force one in."
            )
        elif has_sentence_endings:
            parts.append(
                " Treat sentence endings as a repertoire, not fixed lines: use them only when "
                "they fit and don't stamp the same ending on every sentence."
            )
        elif has_catchphrases:
            parts.append(
                " Treat catchphrases as a repertoire, not fixed lines: use one only when it "
                "fits, and never break grammar or conversational sense to force one in."
            )
        if is_blend and (has_catchphrases or has_sentence_endings):
            parts.append(
                " When blending multiple attributes, adapt personality catchphrases to the "
                "speech attribute's pronouns, endings, register, and vocabulary instead of "
                "copying the source phrase verbatim."
            )
        if has_style_examples:
            parts.append(
                " The style examples below are a tone reference only — never reuse their "
                "exact wording and never continue their scenario/topic."
            )
        parts.append(
            " Don't repeat the same opening, phrasing, or rhythm across consecutive replies; "
            "vary with context and emotion."
        )
        base = "Note on response style: " + "".join(parts)

    if humanize:
        humanize_section = _humanize_directive(lang)
        if humanize_section:
            return base + "\n\n" + humanize_section
    return base


def _humanize_directive(lang: str) -> str:
    """`response_style_directive(humanize=True)` で末尾に追加される人間味強化セクション。

    設計書 §3 P2a に基づく二部構成:
    1. 削る (§2-A/B/D の手癖の禁止: 定型句・網羅回答・免責・復唱・箇条書き・一律ヘッジ、
       + 一文目から中身を始める)
    2. 偏らせる (人間味 = 偏り。禁止だけでは均質性に効かないため:
       関心ある話題は長く・どうでもいい話題は短く / 立場の開示 / 変な具体性を 1 つ。
       ただしペルソナの core_traits と会話の文脈に根ざす範囲で控えめに)

    Returns: 言語ごとの指示ブロック文字列 (該当言語向けのみ。空文字 = 追加なし)
    """
    if lang == "ja":
        return (
            "## 人間味 (humanize)\n"
            "### 削る\n"
            "- すべての応答に同じ定型句 (承知いたしました / 参考になれば幸いです 等) を詰めない\n"
            "- 質問の復唱から始めない (相手が言ったことをオウム返しにしない)\n"
            "- 免責・注意書きを会話の中に自動で挿入しない (ご注意ください、専門家にご相談ください 等)\n"
            "- 箇条書き・見出し (## / - / ・) を会話の中で常用しない\n"
            "- 文末を全部「〜かもしれません」にしない (一律ヘッジは不自然)\n"
            "- 一文目を「重要なのは / 結論から言うと / 今日は〜について」で始めない\n"
            "### 偏らせる (人間味 = 偏り)\n"
            "- ペルソナが強い関心を持つ話題は長く・どうでもいい話題は短く (確信と重みにムラ)\n"
            "- 一文だけ、自分の立場や感想を一言入れる (「正直これは / 個人的には」等)\n"
            "- 変な具体性を 1 つだけ入れる (実在の固有名詞・日時・数量など、捏造はしない)\n"
            "- ただし偏りはペルソナの core_traits と会話の文脈に根ざす範囲で控えめに。"
            "過剰演出や架空の経歴は作らない。"
        )
    if lang == "en":
        return (
            "## Humanize\n"
            "### Strip\n"
            "- Don't open with the same boilerplate (Sure! / Great question / I'd be happy to / etc.)\n"
            "- Don't restate the user's question before answering (no parroting)\n"
            "- Don't inject disclaimers (Please consult a specialist / I am not a) into every reply\n"
            "- Don't fall back on bullet lists / headers (## / -) for conversational answers\n"
            "- Don't hedge every sentence with 'might' / 'could' (uniform hedge reads as AI)\n"
            "- Don't open with 'It's important to note' / 'In summary' / 'To answer your question'\n"
            "### Vary (human-ness = asymmetry)\n"
            "- Spend more words on what this persona actually cares about, less on what it doesn't\n"
            "- One short line of stance or opinion is fine (\"Honestly\" / \"For what it's worth\")\n"
            "- Drop in one concrete, real-world specific (a place, a date, a number) — no fabrications\n"
            "- Keep the asymmetry grounded: don't invent backstories, expertise, or experiences "
            "this persona doesn't have. The asymmetry is in *emphasis*, not in *fabrication*."
        )
    return ""


def _native_catchphrase_directive(lang: str) -> str:
    """人格言語のネイティブ・コンテンツが無い属性を除外した際の生成指示行。

    speech は言語認識済み、personality 等は ``content_i18n.<lang>`` があれば使うが、
    無ければ ja 固定コンテンツを注入せず、当該言語での自前生成を指示する。
    """
    if lang == "en":
        return (
            "Note: some attributes above carry catchphrases authored in another language, "
            "which have been omitted. Express those personality traits through catchphrases "
            "and verbal habits generated natively in English (do not translate)."
        )
    if lang == "ja":
        return (
            "Note: some attributes above carry catchphrases authored in another language, "
            "which have been omitted. Express those personality traits through catchphrases "
            "and verbal habits generated natively in Japanese (do not translate)."
        )
    return (
        f"Note: omitted other-language catchphrases. Express those traits through "
        f"catchphrases generated natively in '{lang}'."
    )


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


def _merge_str_list(attrs: list[dict], key: str) -> list[str]:
    """複数属性の str フィールドを順序保持で重複排除して集約する (speech_style 等)。"""
    out: list[str] = []
    seen: set[str] = set()
    for a in attrs:
        value = a.get(key)
        if isinstance(value, str) and value and value not in seen:
            seen.add(value)
            out.append(value)
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
