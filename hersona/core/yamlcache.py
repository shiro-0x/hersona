"""YAML 読み込みの共有キャッシュ (mtime キー) と libyaml 高速経路。

属性カタログは 346 ファイル規模あり、`attach.load_attribute` は名前 1 つを
解決するたびにカタログ全体を走査する。キャッシュが無いと 1 回の
`render_blend`(属性 2 つ) で 700 回超の YAML parse が走り、CLI 1 コマンドで
1.6 秒、`pytest` 全体で 20 分を消費していた。

本モジュールは (mtime_ns, size) をキーにパース結果を再利用する。ファイルが
書き換わればキーが変わるため、`hersona update` によるデータ差し替えや
テストの一時ディレクトリ書き込みでも古い結果は返らない。

`yaml.CSafeLoader` (libyaml) があれば使い、無ければ純 Python の
`SafeLoader` にフォールバックする。libyaml 環境では単体 parse がさらに
数倍速くなる。
"""
from __future__ import annotations

import copy
from pathlib import Path

import yaml

try:  # libyaml があれば数倍速い C 実装を使う
    from yaml import CSafeLoader as _Loader
except ImportError:  # pragma: no cover - libyaml 無しビルドでのフォールバック
    from yaml import SafeLoader as _Loader  # type: ignore[assignment]

#: 使用中のローダ名 (診断用。libyaml の有無を確認できる)
LOADER_NAME = _Loader.__name__

# path -> ((mtime_ns, size), parsed)
_CACHE: dict[Path, tuple[tuple[int, int], object]] = {}


def load_yaml(path: str | Path, *, default: object = None, copy_result: bool = True) -> object:
    """``path`` を YAML として読み、(mtime_ns, size) キーでキャッシュする。

    Args:
        path: 読み込むファイル。
        default: ファイルが無い / YAML エラー時に返す値。
        copy_result: True なら deepcopy を返す (呼び出し側の変更が
            キャッシュを汚染しないようにする)。カタログ走査のような
            読み取り専用用途では False にすると 1 ファイル 50us 節約できる。

    Returns:
        パース結果、または ``default``。
    """
    p = Path(path)
    try:
        st = p.stat()
    except OSError:
        _CACHE.pop(p, None)
        return default
    key = (st.st_mtime_ns, st.st_size)
    hit = _CACHE.get(p)
    if hit is not None and hit[0] == key:
        data = hit[1]
    else:
        try:
            with open(p, encoding="utf-8") as f:
                data = yaml.load(f, Loader=_Loader)
        except (OSError, yaml.YAMLError):
            _CACHE.pop(p, None)
            return default
        _CACHE[p] = (key, data)
    if data is None:
        return default
    return copy.deepcopy(data) if copy_result else data


def clear_cache() -> None:
    """キャッシュを空にする (テスト・`hersona update` 後の明示クリア用)。"""
    _CACHE.clear()


def cache_size() -> int:
    """キャッシュ済みファイル数 (診断用)。"""
    return len(_CACHE)
