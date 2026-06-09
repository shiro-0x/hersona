---
about: バグ報告（YAML生成ミス・validate.py 偽陰性・schema 違反等）
title: '[BUG] '
labels: bug
assignees: ''
---

## バグの概要

## 再現手順

- OS:
- Python バージョン: `python -V` の出力
- hersona バージョン: `git describe --tags` の出力
- 該当ファイル: `attributes/<category>/<name>.yaml` の attribute_name

## 期待動作

## 実際動作

## 最小 YAML 再現例

```yaml
# 該当部分のみ抜粋
```

## validate.py 出力

```
python scripts/validate.py の出力（raw 貼り付け）
```

## pytest 出力 (該当テストがある場合)

```
pytest tests/test_attributes.py -k <attribute_name> の出力
```

## スクリーンショット・エラーログ

## 関連 Issue

Closes # / refs #
