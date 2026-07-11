"""hersona MCP ツールの純粋ロジック (mcp SDK 非依存)。

各関数は JSON 可搬な dict / list / str を返す。``server.py`` がこれらを MCP ツールに
配線するが、本モジュール自体は ``mcp`` を import しないため単体テストできる。
すべて ``hersona.core`` の公開 API を再利用する (殻のみ)。
"""
from __future__ import annotations

from hersona.core.attach import available_attributes, load_attribute, render_blend
from hersona.core.bench import score_transcript
from hersona.core.compatibility import load_matrix
from hersona.core.constants import CATEGORY_ORDER
from hersona.core.export import export_blend
from hersona.core.i18n import resolve_meta
from hersona.core.intensity import content_language, verify
from hersona.core.personas import available_personas, load_persona
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


def recommend_blend(
    answers: dict[str, int],
    *,
    top: int = 1,
    lang: str | None = None,
    export_format: str | None = None,
) -> dict:
    """診断クイズの回答 ({qid: index}) から推薦ブレンドを返す。

    ``export_format`` を指定すると、推薦ブレンドをその形式でエクスポートした
    文字列を ``export`` キーに含める (recommend → export の再入力を不要にする)。
    """
    quiz = quiz_for_lang(lang)
    rec = recommend(answers, top=top, quiz=quiz)
    out: dict[str, object] = {
        "blend": list(rec.blend),
        "summary": rec.summary(),
        "weight_suggestion": rec.weight_suggestion.value,
        "ranked": [{"name": n, "score": s} for n, s in rec.ranked()[:5]],
        "dropped": [{"name": n, "reason": r} for n, r in rec.dropped],
    }
    if export_format and rec.blend:
        out["export"] = export_blend(
            rec.blend, weight=rec.weight_suggestion.value, fmt=export_format
        )
    return out


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


def measure_intensity(text: str, names: list[str], weight: str = "moderate") -> dict:
    """出力テキスト 1 件をブレンドの期待強度バンドと照合し、決定的に採点する。

    LLM は呼ばない (表層指標: 語尾一致率 + 口癖密度 + 一人称命中率)。エージェントが
    自分の直前の応答をその場で自己採点する MCP 経由のループを組めるようにする。
    speech 属性が 1 つも無いブレンド・未対応言語・言語不一致では採点不能
    (``skipped: true`` + ``skip_reason``) を返す。
    """
    from hersona.core.intensity import skip_reason
    from hersona.core.weight import coerce_level

    attrs = [load_attribute(n) for n in names]
    reason = skip_reason(text, attrs)
    if reason is not None:
        return {"skipped": True, "skip_reason": reason}
    report = verify(text, attrs, coerce_level(weight))
    return {
        "skipped": False,
        "score": report.score,
        "band": list(report.band),
        "status": report.status,
        "endings_rate": report.endings_rate,
        "catchphrase_hits": report.catchphrase_hits,
        "first_person_hits": report.first_person_hits,
        "lang": report.lang,
    }


def bench_transcript(
    names: list[str],
    transcript: list[str],
    weight: str = "moderate",
    attack_turns: list[int] | None = None,
) -> dict:
    """会話トランスクリプト全体の人格維持率・ロック耐性率を決定的に採点する。

    ``transcript`` はエージェント自身が生成した応答文字列のリスト (1 ターン =
    1 応答)。``attack_turns`` を渡すと lock_resistance_rate (攻撃ターンだけの
    部分集合維持率) も計算される (``benchmarks/scenarios/`` の攻撃シナリオと同じ
    0 始まりインデックス)。LLM は呼ばない。
    """
    result = score_transcript(
        names, transcript, weight=weight, attack_turns=attack_turns
    )
    return result.to_dict()


def list_personas() -> dict:
    """公開ペルソナパック (personas/*.yaml) をカタログとして列挙する。"""
    packs = available_personas()
    return {
        "total": len(packs),
        "personas": [
            {
                "persona_name": name,
                "display_name": info["display_name"],
                "description": info["description"],
                "weight": info["weight"],
                "use_case": info["use_case"],
                "blend": list(info["blend"]),
            }
            for name, info in sorted(packs.items())
        ],
    }


def install_persona(name: str) -> dict:
    """ペルソナパックの内容をプレビューする (dry-run 相当。ファイル書き込みなし)。

    パックの blend / weight / use_case から注入ブロックをレンダリングして返す
    だけで、SOUL.md / config.yaml への実書き込みは行わない — MCP 経由の呼び出しで
    エージェントが意図せずローカルファイルを書き換えないようにするための安全策。
    実際にインストールするには CLI の ``hersona personas install <name>`` を使う。

    Raises:
        KeyError: パックが見つからない。
        PersonaPackError: スキーマ / 意味検証に失敗。
    """
    pack = load_persona(name)
    weight = pack.get("weight") or "moderate"
    use_case = pack.get("use_case")
    blend_names = list(pack.get("blend", []))
    result = render_blend(blend_names, weight=weight, use_case=use_case)
    return {
        "persona_name": name,
        "display_name": pack.get("display_name", name),
        "blend": blend_names,
        "weight": weight,
        "use_case": use_case,
        "system_prompt": result.prompt,
        "conflicts": [[a, b] for a, b in result.conflicts],
        "note": (
            "preview only — no files were written; "
            "run `hersona personas install " + name + "` via the CLI to install it"
        ),
    }
