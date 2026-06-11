"""hersona core 共有定数。

属性カテゴリの正準順序を 1 か所に集約する。list / create / recommend など
カテゴリ列を扱う箇所はすべて本定数を参照し、新カテゴリ追加時の取りこぼし
(例: 一覧に出ない / 作成できない) を防ぐ。

`schema/attribute.schema.json` の `attribute_category` enum と一致させること。
"""
from __future__ import annotations

#: 属性カテゴリの正準順序 (表示・選択肢の並び順)。
CATEGORY_ORDER: tuple[str, ...] = (
    "personality",
    "speech",
    "archetype",
    "visual",
    "hobby",
)
