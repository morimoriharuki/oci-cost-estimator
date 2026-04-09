# OCI Cost Estimator

YAML で OCI 構成を定義し、OCI Price List API から単価を取得して CSV 見積りを生成するツール。

## 概要

- 認証不要（Price List API は公開 API）
- OCI SDK 不要（`requests` のみ使用）
- YAML で構成定義 → CSV で見積り出力

## ディレクトリ構成

```
oci-cost-estimator/
├── README.md
├── requirements.txt       # 依存パッケージ
├── estimate.py            # メインスクリプト
├── sku_map.yaml           # サービス種別 → SKU 対応表
├── example.yaml           # 構成定義サンプル
├── skill.md               # Claude Code スキル定義
└── docs/
    └── sku_reference.md   # SKU 一覧・調査メモ
```

## 使い方

```bash
# 依存パッケージのインストール
pip install -r requirements.txt

# 見積り生成
python estimate.py example.yaml

# 出力先: output/estimate_<timestamp>.csv
```

## YAML 構成定義フォーマット

```yaml
project: "プロジェクト名"
currency: JPY
hours_per_month: 744  # 31日 × 24時間

resources:
  - name: "Web サーバー"
    type: compute_e4
    ocpus: 4
    memory_gb: 32
    count: 2

  - name: "ブロックボリューム"
    type: block_volume
    size_gb: 500
    count: 2

  - name: "Autonomous DB (ATP)"
    type: autonomous_db_atp
    ecpus: 4
    storage_gb: 1024

  - name: "オブジェクトストレージ"
    type: object_storage
    size_gb: 1000

  - name: "アウトバウンド通信"
    type: outbound_transfer_apac
    size_gb: 100
```

## 対応サービス

| サービス | type キー |
|---|---|
| Compute E4 | `compute_e4` |
| Compute E5 | `compute_e5` |
| Block Volume | `block_volume` |
| Object Storage | `object_storage` |
| Object Storage (低頻度) | `object_storage_ia` |
| Autonomous DB ATP | `autonomous_db_atp` |
| Autonomous DB ADW | `autonomous_db_adw` |
| アウトバウンド通信 (APAC) | `outbound_transfer_apac` |

## 対応通貨

現在 JPY のみ対応。`currency` フィールドで変更可能（USD 等）。

## 開発状況

- [x] 設計・SKU 調査
- [ ] `estimate.py` 実装
- [ ] テスト
- [ ] ドキュメント整備
