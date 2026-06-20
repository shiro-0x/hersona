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
from hersona.core.i18n import tr
from hersona.core.intensity import content_language, resolve_content_field
from hersona.core.paths import public_attributes_root
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
    raise KeyError(tr("core.attr_not_found", name=name))


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
        raise ValueError(tr("core.blend_empty"))

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

    lines.append("")
    lines.append(f"## 強度: {level}")
    lines.append(WEIGHT_GUIDANCE[level])
    # 自然さ・反復防止・口癖/語尾の使い方を 1 つに統合 (毎ターンの注入コスト削減)。
    lines.append(
        response_style_directive(
            lang,
            has_catchphrases=bool(catchphrases),
            has_sentence_endings=bool(sentence_endings),
        )
    )

    if conflicts:
        lines.append("")
        lines.append("⚠ conflict 検出 (不誠実さ過剰の可能性):")
        for a, b in conflicts:
            lines.append(f"  - {a} ⇔ {b}")

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

    return "\n".join(lines)


def _language_directive(attrs: list[dict]) -> str:
    """人格コンテンツの言語に基づく応答言語の指示行を返す (設計書 §3.4)。

    語彙・語尾が言語束縛のため、応答言語をコンテンツ言語に固定する。
    """
    lang = content_language(attrs)
    if lang == "ja":
        return "応答は日本語で行う（この人格の語彙・語尾・口癖は日本語）。"
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


def catchphrase_usage_directive(lang: str) -> str:
    """口癖の整合性優先ルール (A: 会話成立のためのガード)。

    口癖を「丸写しの枕詞」ではなく「場面が合うときだけ使う言い回しの例」として
    扱わせ、会話の意味・流れを口癖より優先させる。状況に合わない口癖を無理に
    挿入して文意や文法を壊すことを防ぐ。
    """
    if lang == "ja":
        return (
            "※ 口癖の使い方: 上記は決まり文句として丸写しせず、その人格らしい"
            "言い回しの例として扱う。場面が合うときだけ使い、合わなければ使わない。"
            "会話の意味と流れを最優先し、口癖のために文意や文法を壊さないこと。"
        )
    if lang == "en":
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
    lang: str, *, has_catchphrases: bool, has_sentence_endings: bool
) -> str:
    """応答スタイルの統合ガイド (自然さ + 反復防止 + 口癖/語尾の使い方)。

    旧 persona_naturalness / sentence_ending_variation / catchphrase_usage の 3 つを
    1 つにまとめ、注入ブロックの毎ターンコストを削減する (会話が重くなる対策)。
    口癖・語尾セクションが無いときは該当節を省く。個別関数は後方互換のため残す
    (soul.py の SOUL.md 生成等で引き続き使用)。
    """
    if lang == "ja":
        parts = [
            "性格・tone は言葉選びと態度で体現し、自己解説や"
            "「〜をお伝えします」等の前置きをしない。"
        ]
        if has_catchphrases or has_sentence_endings:
            parts.append(
                "口癖・語尾は決まり文句ではなくレパートリー。場面に合うときだけ使い、"
                "全文に同じ語尾を貼らない。"
            )
        parts.append(
            "連続する返答で同じ書き出し・言い回し・リズムを繰り返さず、文脈と感情で変化させる。"
        )
        if has_catchphrases:
            parts.append("会話の意味と流れを最優先し、口癖のために文意・文法を壊さない。")
        return "※ 自然さ最優先: " + "".join(parts)
    if lang == "en":
        parts = [
            "Embody personality and tone through word choice and attitude; never narrate "
            "your own traits or add preamble like 'I'll now tell you…'."
        ]
        if has_catchphrases or has_sentence_endings:
            parts.append(
                " Treat catchphrases and sentence endings as a repertoire, not fixed lines: "
                "use them only when they fit, and don't stamp the same ending on every sentence."
            )
        parts.append(
            " Don't repeat the same opening, phrasing, or rhythm across consecutive replies; "
            "vary with context and emotion."
        )
        if has_catchphrases:
            parts.append(
                " Prioritize conversational sense; never break grammar to force a catchphrase in."
            )
        return "Note on response style: " + "".join(parts)
    return (
        f"Note on response style: embody traits through action, not self-description; "
        f"skip preamble; vary openings and endings across replies in '{lang}'."
    )


def _native_catchphrase_directive(lang: str) -> str:
    """人格言語のネイティブ・コンテンツが無い属性を除外した際の生成指示行。

    speech は言語認識済み、personality 等は ``content_i18n.<lang>`` があれば使うが、
    無ければ ja 固定コンテンツを注入せず、当該言語での自前生成を指示する。
    """
    if lang == "ja":
        return (
            "（一部属性は他言語の口癖を持つため除外した。これらの性格は"
            "日本語の口癖・言い回しで自然に表現すること。翻訳はしない。）"
        )
    if lang == "en":
        return (
            "Note: some attributes above carry catchphrases authored in another language, "
            "which have been omitted. Express those personality traits through catchphrases "
            "and verbal habits generated natively in English (do not translate)."
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
