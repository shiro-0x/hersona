"""公開属性データ (attributes/ + schema/) をリポジトリから取得して更新する。

wheel/pip でインストールした場合、属性テンプレートとスキーマはビルド時に
`hersona/data/` へ同梱される (hersona.core.paths 参照)。アップストリームに
属性が追加・更新されても、パッケージを再インストールしない限り反映されない。

本モジュールは GitHub リポジトリの最新アーカイブをダウンロードし、`attributes/`
と `schema/` だけを抽出してローカルのデータキャッシュ
(`hersona.core.paths.data_cache_root`) へ原子的に展開する。paths はキャッシュを
同梱データより優先して解決するため、再インストールせずに最新データへ更新できる。

ネットワークは標準ライブラリ (`urllib`) のみで完結し、追加依存を増やさない。

チェックサム検証 (外部レビュー対応 §P2-1):
アーカイブは ``codeload.github.com`` から取得するが、検証用マニフェスト
(``checksums.json``、`scripts/gen_checksums.py` で生成) は別配信経路の
``raw.githubusercontent.com`` から同じ ``ref`` で取得し、展開後のファイルと
突き合わせる。**これは転送経路上の改ざん・破損の検知であり、署名や SLSA
provenance ではない** — アーカイブと manifest は同じコミットツリー由来なので、
リポジトリ / GitHub アカウント自体が侵害された場合は両方とも書き換えられ得る
(`docs/SECURITY.md` に脅威モデルを明記)。manifest が取得できない場合
(未対応の古い ``ref`` 等) は警告のみで検証をスキップする (fail-open)。
"""
from __future__ import annotations

import hashlib
import json
import shutil
import tarfile
import tempfile
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from hersona.core.paths import data_cache_root

#: 既定の取得元リポジトリ (owner/name) と参照。
DEFAULT_REPO = "shiro-0x/hersona"
DEFAULT_REF = "main"

#: 抽出対象のトップレベルディレクトリ。これ以外はアーカイブから展開しない。
DATA_DIRS: tuple[str, ...] = ("attributes", "schema")

_USER_AGENT = "hersona-update"
#: ダウンロードサイズ上限 (アーカイブ展開前の安全弁、bytes)。
_MAX_ARCHIVE_BYTES = 64 * 1024 * 1024

CHECKSUMS_FILENAME = "checksums.json"


class UpdateError(Exception):
    """データ更新処理の汎用エラー。"""


class ChecksumMismatchError(UpdateError):
    """ダウンロードしたデータが checksums.json と一致しなかった場合。"""


@dataclass
class UpdateResult:
    """更新の結果サマリ。"""

    ref: str
    source_url: str
    dest: Path
    updated_dirs: list[str] = field(default_factory=list)
    attribute_files: int = 0
    schema_files: int = 0
    checksum_verified: bool = False  # True なら manifest 突合成功済み


def archive_url(ref: str = DEFAULT_REF, *, repo: str = DEFAULT_REPO) -> str:
    """GitHub codeload の tar.gz URL を返す。

    codeload はブランチ名・タグ名・コミット SHA のいずれの ``ref`` でも解決できる。
    """
    return f"https://codeload.github.com/{repo}/tar.gz/{ref}"


def checksums_url(ref: str = DEFAULT_REF, *, repo: str = DEFAULT_REPO) -> str:
    """``checksums.json`` の raw content URL を返す (codeload とは別経路)。"""
    return f"https://raw.githubusercontent.com/{repo}/{ref}/{CHECKSUMS_FILENAME}"


def update_data(
    ref: str = DEFAULT_REF,
    *,
    repo: str = DEFAULT_REPO,
    dest: Path | None = None,
    opener: Callable[[urllib.request.Request], object] | None = None,
    verify_checksums: bool = True,
) -> UpdateResult:
    """最新の attributes/ と schema/ をダウンロードしてキャッシュへ展開する。

    ``dest`` 省略時は :func:`hersona.core.paths.data_cache_root` を使う。
    ``opener`` は ``urllib.request.urlopen`` 互換の callable で、テスト時に
    ネットワークを差し替えるために注入できる。

    ``verify_checksums=True`` (既定) の場合、``checksums.json`` を別経路から
    取得して展開結果と突き合わせる。不一致なら :class:`ChecksumMismatchError`
    を送出しインストールを中止する。manifest 自体が取得できない場合は
    警告のみで続行する (fail-open; 古い ``ref`` には manifest が無いため)。
    """
    target = dest or data_cache_root()
    if target is None:
        raise UpdateError("データキャッシュの保存先を解決できませんでした")

    url = archive_url(ref, repo=repo)
    with tempfile.TemporaryDirectory(prefix="hersona-update-") as tmp:
        tmp_path = Path(tmp)
        archive = tmp_path / "archive.tar.gz"
        _download(url, archive, opener=opener)
        extracted = _extract_data_dirs(archive, tmp_path / "extracted")

        verified = False
        if verify_checksums:
            manifest = _fetch_checksums(ref, repo=repo, opener=opener)
            if manifest is not None:
                _verify_checksums(extracted, manifest)
                verified = True

        result = _install(extracted, target, ref=ref, url=url)
        result.checksum_verified = verified
        return result


def clear_data_cache(dest: Path | None = None) -> list[str]:
    """ダウンロード済みデータキャッシュを削除し、同梱データへ戻す。

    削除した data ディレクトリ名のリストを返す (無ければ空)。
    """
    target = dest or data_cache_root()
    removed: list[str] = []
    if target is None or not target.exists():
        return removed
    for name in DATA_DIRS:
        path = target / name
        if path.exists():
            shutil.rmtree(path)
            removed.append(name)
    return removed


# --- 内部 ---------------------------------------------------------------


def _download(
    url: str,
    dest: Path,
    *,
    opener: Callable[[urllib.request.Request], object] | None = None,
) -> None:
    """``url`` を ``dest`` にダウンロードする (サイズ上限つき)。"""
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    open_fn = opener or urllib.request.urlopen
    try:
        with open_fn(request) as response, open(dest, "wb") as out:  # type: ignore[union-attr]
            written = 0
            while True:
                chunk = response.read(64 * 1024)  # type: ignore[union-attr]
                if not chunk:
                    break
                written += len(chunk)
                if written > _MAX_ARCHIVE_BYTES:
                    raise UpdateError(
                        f"アーカイブが大きすぎます (> {_MAX_ARCHIVE_BYTES} bytes): {url}"
                    )
                out.write(chunk)
    except urllib.error.HTTPError as e:
        raise UpdateError(f"ダウンロードに失敗しました ({e.code} {e.reason}): {url}") from e
    except urllib.error.URLError as e:
        raise UpdateError(f"ネットワークエラーで取得できませんでした: {e.reason} ({url})") from e
    except OSError as e:
        raise UpdateError(f"アーカイブの保存に失敗しました: {e}") from e


#: checksums.json 自体のサイズ上限 (安全弁、bytes)。属性数が増えても数十 KB 程度の想定。
_MAX_MANIFEST_BYTES = 4 * 1024 * 1024


def _fetch_checksums(
    ref: str,
    *,
    repo: str,
    opener: Callable[[urllib.request.Request], object] | None = None,
) -> dict | None:
    """``checksums.json`` を取得してパースする。

    取得できない・パースできない場合は ``None`` を返す (fail-open;
    呼び出し側は「検証スキップ」として扱う)。ネットワークエラーは
    「manifest が存在しない」と区別しない — 古い ``ref`` を指定した場合との
    見分けがユーザー視点では重要でないため。
    """
    url = checksums_url(ref, repo=repo)
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    open_fn = opener or urllib.request.urlopen
    try:
        with open_fn(request) as response:  # type: ignore[union-attr]
            raw = response.read(_MAX_MANIFEST_BYTES + 1)  # type: ignore[union-attr]
    except (urllib.error.HTTPError, urllib.error.URLError, OSError):
        return None
    if len(raw) > _MAX_MANIFEST_BYTES:
        return None
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("files"), dict):
        return None
    return data


def _verify_checksums(extracted: Path, manifest: dict) -> None:
    """展開済みディレクトリを manifest (sha256) と突き合わせる。

    不一致・欠損があれば :class:`ChecksumMismatchError` を送出する。
    """
    files: dict[str, str] = manifest["files"]
    mismatches: list[str] = []
    for name in DATA_DIRS:
        root = extracted / name
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(extracted).as_posix()
            expected = files.get(rel)
            if expected is None:
                mismatches.append(f"{rel}: manifest に記載なし")
                continue
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != expected:
                mismatches.append(f"{rel}: checksum 不一致")
    if mismatches:
        preview = "\n".join(f"  - {m}" for m in mismatches[:10])
        more = f"\n  ...他 {len(mismatches) - 10} 件" if len(mismatches) > 10 else ""
        raise ChecksumMismatchError(
            f"ダウンロードしたデータが checksums.json と一致しませんでした "
            f"({len(mismatches)} 件):\n{preview}{more}\n"
            "ネットワーク経路の改ざん・破損の可能性があります。"
            "再実行しても解消しない場合は --no-verify を検討してください。"
        )


def _strip_top(name: str) -> str | None:
    """アーカイブ内パスの先頭コンポーネント (例 'hersona-main/') を除去する。

    GitHub のアーカイブは全エントリが ``<repo>-<ref>/`` 配下に入る。先頭を外した
    相対パスを返し、トップレベルしか無いエントリは None を返す。
    """
    cleaned = name.lstrip("/")
    parts = cleaned.split("/", 1)
    if len(parts) != 2 or not parts[1]:
        return None
    return parts[1]


def _is_unsafe(rel: str) -> bool:
    """パストラバーサル等の危険なメンバーパスを弾く。"""
    parts = Path(rel).parts
    return ".." in parts or Path(rel).is_absolute()


def _extract_data_dirs(archive: Path, into: Path) -> Path:
    """アーカイブから DATA_DIRS 配下のみを ``into`` へ安全に展開する。"""
    into.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(archive, "r:gz") as tar:
            members = []
            for member in tar.getmembers():
                if not (member.isreg() or member.isdir()):
                    continue  # symlink / device 等は展開しない
                rel = _strip_top(member.name)
                if rel is None or _is_unsafe(rel):
                    continue
                top = rel.split("/", 1)[0]
                if top not in DATA_DIRS:
                    continue
                member.name = rel  # 先頭コンポーネントを外して展開
                members.append(member)
            if not members:
                raise UpdateError(
                    "アーカイブに attributes/ も schema/ も見つかりませんでした"
                )
            try:
                tar.extractall(into, members=members, filter="data")
            except TypeError:
                # filter 引数は Python 3.11.4+ / 3.12+。古い実装では手動検証済み。
                tar.extractall(into, members=members)
    except tarfile.TarError as e:
        raise UpdateError(f"アーカイブの展開に失敗しました: {e}") from e
    return into


def _install(extracted: Path, target: Path, *, ref: str, url: str) -> UpdateResult:
    """展開済みデータを ``target`` へ原子的に設置する。"""
    target.mkdir(parents=True, exist_ok=True)
    result = UpdateResult(ref=ref, source_url=url, dest=target)
    for name in DATA_DIRS:
        src = extracted / name
        if not src.exists():
            continue
        dst = target / name
        backup = target / f".{name}.bak"
        if backup.exists():
            shutil.rmtree(backup)
        if dst.exists():
            dst.rename(backup)
        try:
            shutil.move(str(src), str(dst))
        except OSError:
            # 失敗時は退避を巻き戻す
            if backup.exists() and not dst.exists():
                backup.rename(dst)
            raise
        if backup.exists():
            shutil.rmtree(backup)
        result.updated_dirs.append(name)
        if name == "attributes":
            result.attribute_files = sum(1 for _ in dst.rglob("*.yaml"))
        elif name == "schema":
            result.schema_files = sum(1 for _ in dst.rglob("*.json"))
    return result
