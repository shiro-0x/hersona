"""属性相性マトリクス (ROADMAP ① 相性マトリクス整備)。

`attributes/<category>/<name>.yaml` 群から `compatible_archetypes` /
`conflicts_with` を読み取り、機械可読な相性マトリクスを構築する。
このマトリクスは multi モードの conflict 自動チェックと、② 推薦エンジンの
適合度算出の燃料になる。

設計方針:
- **conflicts は対称関係**として扱う。A が B を `conflicts_with` に挙げていれば、
  B が A を挙げていなくても両者は conflict とみなす（対称閉包を計算）。
  これにより 25 個の YAML を手編集して両側に記載する必要がない
  (YAML は `scripts/_oneoff/gen_v1_attributes.py` を SSOT とし直接編集を避ける方針)。
- **compatible も双方向の和集合**として扱う。compatible は「併用提案」であり、
  どちらか一方が挙げていれば併用候補とみなす。
- conflict は compatible より優先される (両方に現れた場合は conflict と判定)。

CLI として実行すると JSON でマトリクスをダンプする::

    python -m hersona.core.compatibility            # 人間可読サマリ
    python -m hersona.core.compatibility --json     # 機械可読 JSON
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import yaml

from hersona.core.i18n import tr
from hersona.core.paths import public_attributes_root

ATTRIBUTES_ROOT = public_attributes_root()


class Relation(StrEnum):
    """2 属性間の関係。"""

    CONFLICT = "conflict"
    COMPATIBLE = "compatible"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class Attribute:
    """1 属性の相性関連メタデータ (生の宣言値)。"""

    name: str
    category: str
    compatible: frozenset[str]
    conflicts: frozenset[str]
    content_lang: str = "ja"


class CompatibilityMatrix:
    """全属性の相性関係を集約した機械可読マトリクス。

    conflicts は対称閉包、compatible は双方向和集合として正規化済み。
    """

    def __init__(self, attributes: dict[str, Attribute]) -> None:
        self.attributes: dict[str, Attribute] = dict(attributes)
        self._conflicts: dict[str, set[str]] = {n: set() for n in attributes}
        self._compatible: dict[str, set[str]] = {n: set() for n in attributes}
        self._build()

    def _build(self) -> None:
        """宣言値から対称な関係グラフを構築する (未知の参照先は無視)。"""
        names = set(self.attributes)
        for name, attr in self.attributes.items():
            for other in attr.conflicts:
                if other in names:
                    self._conflicts[name].add(other)
                    self._conflicts[other].add(name)  # 対称閉包
            for other in attr.compatible:
                if other in names:
                    self._compatible[name].add(other)
                    self._compatible[other].add(name)  # 双方向和集合
        # conflict は compatible より優先: 両方に現れたら compatible から除外
        for name in self.attributes:
            self._compatible[name] -= self._conflicts[name]

    # --- 主要 API -------------------------------------------------------

    def names(self) -> list[str]:
        return sorted(self.attributes)

    def conflicts(self, a: str, b: str) -> bool:
        """a と b が conflict 関係にあるか (対称)。

        宣言された conflict に加え、**コンテンツ言語が異なる speech 属性同士**は
        構造的に conflict とみなす (1 人格に ja/en の話法を混在させない、設計書 §4.1)。
        """
        self._require(a)
        self._require(b)
        if b in self._conflicts[a]:
            return True
        return self._cross_lang_speech_conflict(a, b)

    def _cross_lang_speech_conflict(self, a: str, b: str) -> bool:
        """両者が speech かつ content_lang が異なれば True。"""
        na, nb = self.attributes[a], self.attributes[b]
        return (
            na.category == "speech"
            and nb.category == "speech"
            and na.content_lang != nb.content_lang
        )

    def is_compatible(self, a: str, b: str) -> bool:
        """a と b が明示的に compatible として宣言されているか (対称)。

        conflict 関係の場合は常に False。
        """
        self._require(a)
        self._require(b)
        return b in self._compatible[a]

    def relation(self, a: str, b: str) -> Relation:
        """a と b の関係を 3 値で返す (conflict / compatible / neutral)。"""
        if self.conflicts(a, b):
            return Relation.CONFLICT
        if self.is_compatible(a, b):
            return Relation.COMPATIBLE
        return Relation.NEUTRAL

    def conflicts_of(self, name: str) -> set[str]:
        """name と conflict する属性名の集合 (対称閉包後)。"""
        self._require(name)
        return set(self._conflicts[name])

    def compatible_of(self, name: str) -> set[str]:
        """name と compatible な属性名の集合 (双方向和集合後)。"""
        self._require(name)
        return set(self._compatible[name])

    def check_blend(self, names: list[str]) -> list[tuple[str, str]]:
        """ブレンド対象の属性リストから conflict ペアを列挙する。

        multi モード / recommend の適用前チェックで使う。
        戻り値は (a, b) のソート済みペアのリスト (a < b)。
        """
        for n in names:
            self._require(n)
        pairs: set[tuple[str, str]] = set()
        for i, a in enumerate(names):
            for b in names[i + 1 :]:
                if self.conflicts(a, b):
                    pairs.add(tuple(sorted((a, b))))  # type: ignore[arg-type]
        return sorted(pairs)

    # --- データ衛生 (双方向整合の検証用) --------------------------------

    def asymmetries(self) -> dict[str, list[tuple[str, str]]]:
        """宣言値の非対称を検出する (validate.py の警告に使う)。

        戻り値::
            {
              "conflicts":  [(a, b), ...],   # a が b を挙げるが b が a を挙げない
              "compatible": [(a, b), ...],
              "dangling":   [(a, ref), ...], # 未知の attribute_name 参照
            }
        """
        names = set(self.attributes)
        out: dict[str, list[tuple[str, str]]] = {
            "conflicts": [],
            "compatible": [],
            "dangling": [],
        }
        for name, attr in self.attributes.items():
            for ref in attr.conflicts:
                if ref not in names:
                    out["dangling"].append((name, ref))
                elif name not in self.attributes[ref].conflicts:
                    out["conflicts"].append((name, ref))
            for ref in attr.compatible:
                if ref not in names:
                    out["dangling"].append((name, ref))
                elif name not in self.attributes[ref].compatible:
                    out["compatible"].append((name, ref))
        for key in out:
            out[key].sort()
        return out

    # --- エクスポート ---------------------------------------------------

    def to_dict(self) -> dict:
        """正規化後の対称マトリクスを機械可読 dict として返す。"""
        return {
            "attributes": {
                name: {
                    "category": attr.category,
                    "conflicts": sorted(self._conflicts[name]),
                    "compatible": sorted(self._compatible[name]),
                }
                for name, attr in sorted(self.attributes.items())
            }
        }

    # --- 内部 -----------------------------------------------------------

    def _require(self, name: str) -> None:
        if name not in self.attributes:
            raise KeyError(tr("core.unknown_attr_name", name=name))


def load_matrix(attributes_root: Path | None = None) -> CompatibilityMatrix:
    """attributes/ 配下を読み込み、相性マトリクスを構築する。"""
    root = attributes_root or ATTRIBUTES_ROOT
    attributes: dict[str, Attribute] = {}
    for yml in sorted(root.rglob("*.yaml")):
        with open(yml, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict) or "attribute_name" not in data:
            continue
        name = data["attribute_name"]
        attributes[name] = Attribute(
            name=name,
            category=data.get("attribute_category", ""),
            compatible=frozenset(data.get("compatible_archetypes", []) or []),
            conflicts=frozenset(data.get("conflicts_with", []) or []),
            content_lang=data.get("content_lang") or "ja",
        )
    return CompatibilityMatrix(attributes)


def _main(argv: list[str]) -> int:
    matrix = load_matrix()
    if "--json" in argv:
        print(json.dumps(matrix.to_dict(), ensure_ascii=False, indent=2))
        return 0

    print(f"属性数: {len(matrix.names())}")
    asym = matrix.asymmetries()
    print(f"\n非対称 conflict 宣言: {len(asym['conflicts'])} 件 (core で対称閉包済み)")
    for a, b in asym["conflicts"]:
        print(f"  - {a} → {b} (片側のみ宣言)")
    print(f"\n非対称 compatible 宣言: {len(asym['compatible'])} 件")
    for a, b in asym["compatible"]:
        print(f"  - {a} → {b} (片側のみ宣言)")
    if asym["dangling"]:
        print(f"\n未知参照: {len(asym['dangling'])} 件")
        for a, ref in asym["dangling"]:
            print(f"  - {a} → {ref} (存在しない attribute_name)")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
