"""hersona MCP ツールの純粋ロジック (mcp SDK 非依存)。

各関数は JSON 可搬な dict / list / str を返す。``server.py`` がこれらを MCP ツールに
配線するが、本モジュール自体は ``mcp`` を import しないため単体テストできる。
すべて ``hersona.core`` の公開 API を再利用する (殻のみ)。
"""
from __future__ import annotations

from hersona.core.attach import available_attributes, load_attribute, render_blend
from hersona.core.compatibility import load_matrix
from hersona.core.constants import CATEGORY_ORDER
from hersona.core.export import export_blend
from hersona.core.i18n import resolve_meta
from hersona.core.intensity import content_language
from hersona.core.recommend import quiz_for_lang, recommend

# show / blend の応答に含める属性フィールド (人格を再構成できる最小集合)。
_LIST_FIELDS = ("core_traits", "catchphrases", "sentence_endings", "lexical_markers", "tags")
_SCALAR_FIELDS = ("second_person", "first_person", "register", "tone", "speech_style")
_REL_FIELDS = ("compatible_archetypes", "conflicts_with")


def list_attributes() -> dict:
    """利用可能な属性 (public + user) をカテゴリ別に列挙する。"""
    attrs = available_attributes()
    by_cat: dict[str, list[dict]] = {cat: [] for cat in CATEGORY_ORDER}
    for name, meta in sorted(attrs.items()):
        by_cat.setdefault(meta["category"], []).append(
            {"name": name, "source": meta["source"]}
        )
    return {
        "total": len(attrs),
        "categories": {cat: items for cat, items in by_cat.items() if items},
    }


def show_attribute(name: str) -> dict:
    """属性 1 件の詳細を返す (i18n 解決済みの display_name / description 含む)。"""
    data = load_attribute(name)
    out: dict[str, object] = {
        "name": data.get("attribute_name", name),
        "category": data.get("attribute_category", ""),
        "display_name": resolve_meta(data, "display_name"),
        "description": resolve_meta(data, "description"),
    }
    for key in ("weight_dimension", "typical_value_range", "content_lang"):
        if data.get(key):
            out[key] = data[key]
    for key in _LIST_FIELDS + _REL_FIELDS:
        if data.get(key):
            out[key] = list(data[key])
    for key in _SCALAR_FIELDS:
        if data.get(key):
            out[key] = data[key]
    return out


def blend(names: list[str], weight: str = "moderate") -> dict:
    """複数属性を注入ブロックに合成し、system_prompt と conflict を返す。"""
    result = render_blend(names, weight=weight)
    return {
        "names": list(result.names),
        "weight": weight,
        "content_lang": content_language(result.attributes),
        "conflicts": [[a, b] for a, b in result.conflicts],
        "system_prompt": result.prompt,
    }


def export(names: list[str], weight: str = "moderate", fmt: str = "json") -> str:
    """ブレンドを可搬形式 (json / messages / markdown) でエクスポートする。"""
    return export_blend(names, weight=weight, fmt=fmt)


def recommend_blend(answers: dict[str, int], *, top: int = 1, lang: str | None = None) -> dict:
    """診断クイズの回答 ({qid: index}) から推薦ブレンドを返す。"""
    quiz = quiz_for_lang(lang)
    rec = recommend(answers, top=top, quiz=quiz)
    return {
        "blend": list(rec.blend),
        "summary": rec.summary(),
        "weight_suggestion": rec.weight_suggestion.value,
        "ranked": [{"name": n, "score": s} for n, s in rec.ranked()[:5]],
        "dropped": [{"name": n, "reason": r} for n, r in rec.dropped],
    }


def compatibility(name: str | None = None) -> dict:
    """相性マトリクスを返す。name 指定時はその属性の conflict / compatible のみ。"""
    matrix = load_matrix()
    if name is not None:
        return {
            "name": name,
            "conflicts_with": sorted(matrix.conflicts_of(name)),
            "compatible_with": sorted(matrix.compatible_of(name)),
        }
    return matrix.to_dict()
