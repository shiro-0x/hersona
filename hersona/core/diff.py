"""2 属性の差分比較 (B1: hersona diff)。

`load_attribute` で 2 つの属性 YAML を解決し、相性マトリクスの relation と
フィールド単位の差分 (共通 / 片側のみ) を構造化して返す純粋ロジック。
CLI / 将来の Web 殻はこの結果を描画するだけにする。

list 系フィールド (core_traits / catchphrases ...) は共通・片側のみに分解し、
scalar 系 (tone / second_person ...) は左右並置で返す。
"""
from __future__ import annotations

from dataclasses import dataclass

from hersona.core.attach import load_attribute
from hersona.core.compatibility import CompatibilityMatrix, Relation, load_matrix
from hersona.core.i18n import resolve_meta

# 共通/片側に分解する list フィールド (順序を保って差分を取る)。
LIST_FIELDS: tuple[str, ...] = (
    "core_traits",
    "catchphrases",
    "sentence_endings",
    "lexical_markers",
    "tags",
)

# 左右並置で見せる scalar フィールド。
SCALAR_FIELDS: tuple[str, ...] = (
    "weight_dimension",
    "second_person",
    "register",
    "typical_value_range",
    "tone",
)


@dataclass(frozen=True)
class FieldDiff:
    """list フィールド 1 つの共通 / 片側のみ分解。"""

    field: str
    common: list[str]
    only_a: list[str]
    only_b: list[str]


@dataclass(frozen=True)
class ScalarDiff:
    """scalar フィールド 1 つの左右値。"""

    field: str
    a: str
    b: str


@dataclass(frozen=True)
class AttributeDiff:
    """2 属性の差分比較結果。"""

    name_a: str
    name_b: str
    category_a: str
    category_b: str
    # relation は両者が公開マトリクスに存在するときのみ。user 属性等は None。
    relation: Relation | None
    scalars: list[ScalarDiff]
    lists: list[FieldDiff]


def _as_str_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    return []


def _split(a: list[str], b: list[str]) -> tuple[list[str], list[str], list[str]]:
    """順序を保ったまま common / only_a / only_b に分ける。"""
    set_a, set_b = set(a), set(b)
    common = [x for x in a if x in set_b]
    only_a = [x for x in a if x not in set_b]
    only_b = [x for x in b if x not in set_a]
    return common, only_a, only_b


def diff_attributes(
    name_a: str,
    name_b: str,
    *,
    matrix: CompatibilityMatrix | None = None,
    lang: str | None = None,
) -> AttributeDiff:
    """2 属性名を解決し、差分比較結果を返す。

    Args:
        name_a / name_b: 比較する属性名 (user 名前空間も解決可)
        matrix: 相性判定用。None ならロード
        lang: display_name / description の表示言語

    Returns:
        ``AttributeDiff``。relation は両者が公開マトリクスにあるときのみ算出。
    """
    da = load_attribute(name_a)
    db = load_attribute(name_b)
    m = matrix or load_matrix()

    # user 属性などマトリクス未収録なら relation は None。
    relation: Relation | None = None
    if name_a in m.attributes and name_b in m.attributes:
        relation = m.relation(name_a, name_b)

    scalars: list[ScalarDiff] = []
    # display_name / description は i18n 解決して並置。
    for field in ("display_name", "description"):
        va = resolve_meta(da, field, lang)
        vb = resolve_meta(db, field, lang)
        if va or vb:
            scalars.append(ScalarDiff(field=field, a=va, b=vb))
    for field in SCALAR_FIELDS:
        va, vb = da.get(field), db.get(field)
        if va or vb:
            scalars.append(ScalarDiff(field=field, a=str(va or ""), b=str(vb or "")))

    lists: list[FieldDiff] = []
    for field in LIST_FIELDS:
        la, lb = _as_str_list(da.get(field)), _as_str_list(db.get(field))
        if not la and not lb:
            continue
        common, only_a, only_b = _split(la, lb)
        lists.append(FieldDiff(field=field, common=common, only_a=only_a, only_b=only_b))

    return AttributeDiff(
        name_a=name_a,
        name_b=name_b,
        category_a=da.get("attribute_category", ""),
        category_b=db.get("attribute_category", ""),
        relation=relation,
        scalars=scalars,
        lists=lists,
    )
