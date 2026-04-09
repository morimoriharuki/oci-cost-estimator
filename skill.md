# OCI Cost Estimator スキル

Claude Code がこのプロジェクトで作業する際の参照ドキュメント。

## プロジェクト概要

YAML で OCI 構成を定義し、OCI Price List API から単価を取得して CSV 見積りを生成するツール。

## 重要ファイル

| ファイル | 役割 |
|---|---|
| `estimate.py` | メインスクリプト |
| `sku_map.yaml` | サービス種別 → SKU 対応表 |
| `example.yaml` | 構成定義サンプル |
| `docs/sku_reference.md` | SKU 調査メモ・Price List API 仕様 |

## Price List API

- URL: `https://apexapps.oracle.com/pls/apex/cetools/api/v1/products/?currencyCode=JPY`
- 認証不要、JSON 形式
- 主要フィールド:
  - `partNumber` — SKU
  - `displayName` — 表示名
  - `metricName` — 課金単位
  - `currencyCodeLocalizations[].prices[].value` — 単価

## 月額計算ロジック

```
# 時間課金（Compute OCPU/Memory）
月額 = 単価 × 数量 × hours_per_month × count

# 月額課金（Storage, Transfer）
月額 = 単価 × 数量 × count
```

## CSV 出力形式

```
リソース名, タイプ, 数量, 単位, 単価(JPY), 月額(JPY)
...
合計, , , , , ZZZ
```

## 開発ルール

- コミットメッセージは1行の日本語でシンプルに
- SKU は `sku_map.yaml` で一元管理
- 新しいサービス追加は `sku_map.yaml` と `README.md` の対応表を両方更新
