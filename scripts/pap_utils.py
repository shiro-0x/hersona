"""persona_attach_prompt (pap) セクションへの安全な dict アクセス共通化

`persona_attach_prompt` 配下のキーは将来のスキーマ追加・型変更で
アクセスパターンが変動するため、ここに集約して安全アクセスを共通化する。

設計方針:
- キーが存在しない／途中で非 dict になった場合は default を返す
- pap_get_list / pap_get_dict は「指定キーの値が想定型である」ことを保証する
  薄いラッパ。None や型違いは空 list / 空 dict に正規化される
"""
from __future__ import annotations


def pap_get(ap: dict, *keys: str, default=None):
    """persona_attach_prompt 内の指定キーを安全に辿る (reviewer_cli._pap_section の移植)"""
    cur: object = ap
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    return cur if cur is not None else default


def pap_get_list(ap: dict, *keys: str) -> list:
    """pap_get で取得した値が list であることを保証 (None/未設定は空 list)"""
    v = pap_get(ap, *keys, default=[])
    return v if isinstance(v, list) else []


def pap_get_dict(ap: dict, *keys: str) -> dict:
    """pap_get で取得した値が dict であることを保証"""
    v = pap_get(ap, *keys, default={})
    return v if isinstance(v, dict) else {}
