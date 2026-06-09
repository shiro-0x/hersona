"""相性マトリクス (hersona.core.compatibility) の回帰テスト (ROADMAP ①)。

- conflicts が対称関係として扱われる (対称閉包)
- compatible が双方向和集合として扱われる
- conflict が compatible より優先される
- check_blend が conflict ペアを列挙する
- to_dict が機械可読な正規化済みマトリクスを返す
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hersona.core.compatibility import (
    Attribute,
    CompatibilityMatrix,
    Relation,
    load_matrix,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
ATTRIBUTES_DIR = REPO_ROOT / "attributes"


def _toy_matrix() -> CompatibilityMatrix:
    """片側だけ宣言された conflict / compatible を含む最小マトリクス。"""
    attrs = {
        "a": Attribute("a", "personality", frozenset({"b"}), frozenset({"c"})),
        "b": Attribute("b", "personality", frozenset(), frozenset()),
        "c": Attribute("c", "speech", frozenset(), frozenset()),
        "d": Attribute("d", "speech", frozenset(), frozenset({"a"})),
    }
    return CompatibilityMatrix(attrs)


def test_conflict_is_symmetric() -> None:
    m = _toy_matrix()
    # a→c は宣言済み。c→a は未宣言だが対称閉包で成立する。
    assert m.conflicts("a", "c")
    assert m.conflicts("c", "a")
    # d→a も同様に対称化される。
    assert m.conflicts("a", "d")
    assert m.conflicts("d", "a")


def test_compatible_is_bidirectional() -> None:
    m = _toy_matrix()
    assert m.is_compatible("a", "b")
    assert m.is_compatible("b", "a")


def test_conflict_takes_precedence_over_compatible() -> None:
    # 同じペアが両方に現れた場合、conflict が優先され compatible からは除外される。
    attrs = {
        "x": Attribute("x", "personality", frozenset({"y"}), frozenset({"y"})),
        "y": Attribute("y", "personality", frozenset(), frozenset()),
    }
    m = CompatibilityMatrix(attrs)
    assert m.conflicts("x", "y")
    assert not m.is_compatible("x", "y")
    assert m.relation("x", "y") is Relation.CONFLICT


def test_relation_three_states() -> None:
    m = _toy_matrix()
    assert m.relation("a", "c") is Relation.CONFLICT
    assert m.relation("a", "b") is Relation.COMPATIBLE
    assert m.relation("b", "c") is Relation.NEUTRAL


def test_check_blend_lists_conflict_pairs() -> None:
    m = _toy_matrix()
    pairs = m.check_blend(["a", "b", "c"])
    assert ("a", "c") in pairs
    assert ("a", "b") not in pairs  # compatible
    # ペアは (a, b) で a < b に正規化される
    assert all(a < b for a, b in pairs)


def test_unknown_reference_is_ignored_in_graph() -> None:
    attrs = {
        "a": Attribute("a", "personality", frozenset(), frozenset({"ghost"})),
    }
    m = CompatibilityMatrix(attrs)
    assert m.conflicts_of("a") == set()  # 未知参照はグラフに入れない


def test_unknown_name_raises() -> None:
    m = _toy_matrix()
    with pytest.raises(KeyError):
        m.conflicts("a", "nonexistent")


def test_asymmetries_detects_one_sided_declarations() -> None:
    m = _toy_matrix()
    asym = m.asymmetries()
    assert ("a", "c") in asym["conflicts"]  # a が c を挙げるが c は挙げない
    assert ("a", "b") in asym["compatible"]
    assert ("a", "ghost") not in asym["dangling"]  # toy には ghost なし


def test_to_dict_is_normalized_and_sorted() -> None:
    m = _toy_matrix()
    d = m.to_dict()
    assert set(d["attributes"]) == {"a", "b", "c", "d"}
    assert d["attributes"]["c"]["conflicts"] == ["a"]  # 対称化済み
    assert d["attributes"]["a"]["conflicts"] == ["c", "d"]  # ソート済み


# --- 実データに対する統合テスト -----------------------------------------


def test_load_real_matrix_has_26_attributes() -> None:
    m = load_matrix(ATTRIBUTES_DIR)
    assert len(m.names()) == 26


def test_real_matrix_conflicts_fully_symmetric() -> None:
    """対称閉包後、実データの conflict は完全対称になる。"""
    m = load_matrix(ATTRIBUTES_DIR)
    for name in m.names():
        for other in m.conflicts_of(name):
            assert name in m.conflicts_of(other), (
                f"{name} は {other} と conflict だが逆が成立していない"
            )


def test_real_matrix_no_dangling_references() -> None:
    """実データに未知の attribute_name 参照がない。"""
    m = load_matrix(ATTRIBUTES_DIR)
    assert m.asymmetries()["dangling"] == []


def test_real_tsundere_rival_compatible() -> None:
    m = load_matrix(ATTRIBUTES_DIR)
    assert m.is_compatible("tsundere", "rival")
    assert not m.conflicts("tsundere", "rival")


def test_real_genki_kuudere_conflict() -> None:
    m = load_matrix(ATTRIBUTES_DIR)
    assert m.conflicts("genki", "kuudere")
