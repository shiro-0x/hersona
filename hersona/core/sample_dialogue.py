"""派生候補ブレンドのサンプル会話 (sample_dialogue) 生成器 (v1.3.0 新規)。

責務:
- ``Recommendation.candidates`` の各 blend に対し ``count`` 個のサンプル文を返す
- LLM 非依存の **テンプレ方式** (決定的、テスト可能、i18n 容易) を既定とする
- ユーザー定義の ``SampleGenerator`` callable を差し込んで LLM 実装に拡張可能

設計判断 (前ターンまでの議論):
- hersona は PyPI 配布ライブラリ、LLM SDK 依存を持たない
- サンプル文の "種" は各属性 YAML の ``catchphrases`` を使う
  → 人格の一貫性が YAML 定義から自動担保される
- speech > personality > archetype > visual > hobby の優先順で採用
- ``lang`` (en/ja) 切替対応: ``content_i18n.<lang>`` からネイティブ catchphrases を取得
"""
from __future__ import annotations

import random
from collections.abc import Callable
from typing import TYPE_CHECKING

from hersona.core.attach import load_attribute
from hersona.core.compatibility import load_matrix

if TYPE_CHECKING:
    from hersona.core.recommend import CompatibilityMatrix


# カテゴリ優先順位: 強い人格特徴ほどサンプル文の核に採用
_CATEGORY_PRIORITY = ("speech", "personality", "archetype", "visual", "hobby")


def _resolve_catchphrases(attr_data: dict, lang: str) -> list[str]:
    """属性 YAML dict から lang に対応する catchphrases リストを返す。

    優先:
    1. ``content_i18n.<lang>.catchphrases`` (指定言語のネイティブ版)
    2. ``catchphrases`` (BASE、en 想定)
    3. 空リスト
    """
    content_i18n = attr_data.get("content_i18n") or {}
    if isinstance(content_i18n, dict):
        localized = content_i18n.get(lang) or {}
        if isinstance(localized, dict) and isinstance(localized.get("catchphrases"), list):
            return [str(s) for s in localized["catchphrases"]]
    base = attr_data.get("catchphrases")
    if isinstance(base, list):
        return [str(s) for s in base]
    return []


def _attribute_category(name: str, matrix: CompatibilityMatrix) -> str:
    """属性名から category を返す (見つからなければ空文字)。"""
    info = matrix.attributes.get(name)
    return info.category if info else ""


def _generate_template_samples(
    blend: list[str],
    *,
    count: int,
    lang: str,
    matrix: CompatibilityMatrix | None = None,
) -> list[str]:
    """blend の各属性 catchphrases を優先順で集めて count 個返す (テンプレ方式)。

    Args:
        blend: 採用属性名のリスト (例: ``["kuudere", "reading", "rival", ...]``)
        count: 返却するサンプル文数
        lang: ``"en"`` / ``"ja"`` などの表示言語
        matrix: ``CompatibilityMatrix`` (カテゴリ判定用)。None ならロード

    Returns:
        サンプル文のリスト。要素数 <= ``count`` (catchphrases が少なければ少ない)
    """
    if count <= 0 or not blend:
        return []
    m = matrix or load_matrix()

    # 属性を category 別に分類
    by_cat: dict[str, list[dict]] = {c: [] for c in _CATEGORY_PRIORITY}
    unknown: list[dict] = []
    for name in blend:
        cat = _attribute_category(name, m)
        try:
            data = load_attribute(name)
        except (KeyError, FileNotFoundError):
            continue
        entry = {"name": name, "data": data, "phrases": _resolve_catchphrases(data, lang)}
        if cat in by_cat:
            by_cat[cat].append(entry)
        else:
            unknown.append(entry)

    # 優先順位に従ってフレーズを連結
    pool: list[str] = []
    for cat in _CATEGORY_PRIORITY:
        for entry in by_cat[cat]:
            pool.extend(entry["phrases"])
    for entry in unknown:
        pool.extend(entry["phrases"])

    if not pool:
        return []

    # 重複排除 (順序保持)
    seen: set[str] = set()
    deduped: list[str] = []
    for p in pool:
        if p in seen:
            continue
        seen.add(p)
        deduped.append(p)

    return deduped[:count]


# 公開型: 差し込み可能なサンプル生成器
SampleGenerator = Callable[[list[str], int, str | None], list[str]]


def default_generator(
    blend: list[str],
    count: int,
    lang: str | None = None,
    *,
    matrix: CompatibilityMatrix | None = None,
    seed: int | None = None,
) -> list[str]:
    """既定のテンプレ方式サンプル生成器。

    公開関数 ``generate_samples`` から ``count`` 件のサンプル文を返す。
    順序を少し散らすオプション (``seed``) を提供、テスト時の再現性用。
    """
    if lang is None:
        lang = "en"
    samples = _generate_template_samples(blend, count=count, lang=lang, matrix=matrix)
    if seed is not None and len(samples) > 1:
        rng = random.Random(seed)
        rng.shuffle(samples)
    return samples


def generate_samples(
    blend: list[str],
    *,
    count: int = 3,
    lang: str | None = None,
    generator: SampleGenerator | None = None,
    matrix: CompatibilityMatrix | None = None,
) -> list[str]:
    """派生候補ブレンドのサンプル文を生成する公開 API。

    Args:
        blend: 採用属性名のリスト
        count: 返却するサンプル文数 (既定 3)
        lang: 表示言語 (``"en"`` / ``"ja"``)。``None`` なら ``"en"``
        generator: 差し込み用カスタム生成器。``None`` なら ``default_generator``
        matrix: カテゴリ判定用 matrix。``None`` ならロード

    Returns:
        サンプル文のリスト。要素数 <= ``count``
    """
    if not blend:
        return []
    if count <= 0:
        return []
    if generator is None:
        return default_generator(blend, count, lang, matrix=matrix)
    return generator(blend, count, lang)
