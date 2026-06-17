"""ブレンドプリセット (blend preset) のローカル保存 (ROADMAP C: `hersona save`)。

ブレンドは「複数属性 + 強度」の組み合わせであり、単一カテゴリの属性スキーマには
収まらない。そこで気に入ったブレンドを **プリセット (レシピ)** として
ユーザー名前空間に保存し、後から名前一つで呼び出せるようにする core ロジック。

設計方針 (authoring.py と整合):
- **保存先の分離**: プリセットは属性 (`~/.hermes/attributes/`) とは別に
  `~/.hermes/presets/` (既定) に置く。環境変数 `HERSONA_PRESETS_DIR` で明示指定可。
  未指定時は属性ルート (`HERSONA_USER_DIR`) の兄弟ディレクトリ `presets/` を使うため、
  属性側の隔離設定 (テスト等) をそのまま継承する。
- **属性の実在チェックは呼び出し側 (CLI)**: core はプリセット名・属性名リストの
  形式のみ検証する (属性の存在解決は attach.load_attribute に委ねる)。
- **薄い殻**: 保存は YAML 1 ファイル。読み出しは `load_preset` で `Preset` を返すだけ。
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

from hersona.core.authoring import user_attributes_root
from hersona.core.i18n import tr

# プリセット名は属性名と同じ snake_case 規約 (ASCII 小文字始まり)。
_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class PresetError(Exception):
    """プリセット処理の汎用エラー。"""


def intensity_baseline_to_dict(report: object) -> dict:
    """IntensityReport をプリセット保存用 dict に直列化する。"""
    from dataclasses import asdict

    from hersona.core.intensity import IntensityReport

    if not isinstance(report, IntensityReport):
        raise TypeError(f"expected IntensityReport, got {type(report).__name__}")
    data = asdict(report)
    data["band"] = list(data["band"])
    return data


def intensity_baseline_from_dict(data: dict) -> object:
    """プリセット dict から IntensityReport を復元する。"""
    from hersona.core.intensity import IntensityReport

    band = data.get("band") or (0, 100)
    if isinstance(band, list):
        band = tuple(band)
    return IntensityReport(
        score=float(data.get("score", 0.0)),
        endings_rate=float(data.get("endings_rate", 0.0)),
        catchphrase_hits=int(data.get("catchphrase_hits", 0)),
        sentence_count=int(data.get("sentence_count", 0)),
        band=(int(band[0]), int(band[1])),
        status=str(data.get("status", "")),
        lang=str(data.get("lang", "ja")),
        first_person_hits=int(data.get("first_person_hits", 0)),
    )


@dataclass
class Preset:
    """保存されたブレンドプリセット。"""

    name: str
    attributes: list[str]
    weight: str = "moderate"
    note: str = ""
    created: str = ""
    tags: list[str] = field(default_factory=list)
    intensity_baseline: dict | None = None

    def to_dict(self) -> dict:
        """YAML 出力用の dict (空フィールドは省略)。"""
        data: dict[str, object] = {
            "preset_name": self.name,
            "attributes": list(self.attributes),
            "weight": self.weight,
        }
        if self.note:
            data["note"] = self.note
        if self.created:
            data["created"] = self.created
        if self.tags:
            data["tags"] = list(self.tags)
        if self.intensity_baseline is not None:
            data["intensity_baseline"] = dict(self.intensity_baseline)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> Preset:
        if not isinstance(data, dict):
            raise PresetError(tr("preset.bad_format", detail=type(data).__name__))
        name = data.get("preset_name") or ""
        attrs = data.get("attributes") or []
        if not isinstance(attrs, list) or not all(isinstance(a, str) for a in attrs):
            raise PresetError(tr("preset.bad_format", detail="attributes"))
        baseline = data.get("intensity_baseline")
        if baseline is not None and not isinstance(baseline, dict):
            raise PresetError(tr("preset.bad_format", detail="intensity_baseline"))
        return cls(
            name=str(name),
            attributes=[str(a) for a in attrs],
            weight=str(data.get("weight") or "moderate"),
            note=str(data.get("note") or ""),
            created=str(data.get("created") or ""),
            tags=[str(t) for t in (data.get("tags") or [])],
            intensity_baseline=dict(baseline) if baseline is not None else None,
        )


def presets_root() -> Path:
    """プリセットの保存ルート。

    環境変数 ``HERSONA_PRESETS_DIR`` があればそれを、なければ属性ルート
    (``user_attributes_root()``) の兄弟ディレクトリ ``presets/`` を使う。
    既定では ``~/.hermes/presets``。
    """
    env = os.environ.get("HERSONA_PRESETS_DIR")
    if env:
        return Path(env).expanduser()
    return user_attributes_root().parent / "presets"


def _validate_name(name: str) -> None:
    if not name or not _NAME_RE.match(name):
        raise PresetError(tr("preset.bad_name", name=name))


def save_preset(
    name: str,
    attributes: list[str],
    *,
    weight: str = "moderate",
    note: str = "",
    tags: list[str] | None = None,
    intensity_baseline: object | None = None,
    root: Path | None = None,
    overwrite: bool = False,
) -> Path:
    """ブレンドプリセットを YAML として保存する。

    保存先: ``<presets_root>/<name>.yaml``。同名が存在し ``overwrite=False`` なら拒否。
    属性名リストの実在は検証しない (CLI 側で attach.load_attribute により解決済み前提)。
    """
    _validate_name(name)
    if not attributes:
        raise PresetError(tr("preset.empty", name=name))

    baseline_dict: dict | None = None
    if intensity_baseline is not None:
        baseline_dict = intensity_baseline_to_dict(intensity_baseline)

    preset = Preset(
        name=name,
        attributes=list(attributes),
        weight=weight,
        note=note,
        created=date.today().isoformat(),
        tags=list(tags or []),
        intensity_baseline=baseline_dict,
    )
    base = root or presets_root()
    base.mkdir(parents=True, exist_ok=True)
    dest = base / f"{name}.yaml"
    if dest.exists() and not overwrite:
        raise PresetError(tr("preset.exists", dest=dest))

    with open(dest, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            preset.to_dict(),
            f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )
    return dest


def load_preset(name: str, *, root: Path | None = None) -> Preset:
    """名前からプリセットを読み込む。見つからなければ ``PresetError``。"""
    base = root or presets_root()
    dest = base / f"{name}.yaml"
    if not dest.exists():
        raise PresetError(tr("preset.not_found", name=name))
    with open(dest, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    preset = Preset.from_dict(data)
    # ファイル名を正とし、preset_name 欠落時はファイル名で補完する。
    if not preset.name:
        preset.name = name
    return preset


def list_presets(root: Path | None = None) -> list[Preset]:
    """保存済みプリセットを名前昇順で列挙する。"""
    base = root or presets_root()
    if not base.exists():
        return []
    out: list[Preset] = []
    for yml in sorted(base.glob("*.yaml")):
        try:
            with open(yml, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            preset = Preset.from_dict(data)
            if not preset.name:
                preset.name = yml.stem
            out.append(preset)
        except (PresetError, yaml.YAMLError):
            continue
    return out


def delete_preset(name: str, *, root: Path | None = None) -> Path:
    """プリセットを削除し、削除したパスを返す。無ければ ``PresetError``。"""
    base = root or presets_root()
    dest = base / f"{name}.yaml"
    if not dest.exists():
        raise PresetError(tr("preset.not_found", name=name))
    dest.unlink()
    return dest
