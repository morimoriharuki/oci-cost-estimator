# OCI Cost Estimator

OCI の構成見積りを自動生成するツール。  
**常に最新の OCI 公式価格表を取得**して CSV 見積りを出力します。

## 特徴

- 認証不要・API キー不要（OCI Price List API は公開 API）
- OCI SDK 不要（`pyyaml` と `requests` のみ）
- 対話形式でも Excel ファイルからでも見積り可能
- Claude Code / Cline / Codex などの AI アシスタントと連携して使える

---

## セットアップ

```bash
git clone https://github.com/morimoriharuki/oci-cost-estimator.git
cd oci-cost-estimator
pip install -r requirements.txt
```

以上で完了です。

---

## 使い方

### AI アシスタントと連携する場合（推奨）

Claude Code・Cline・Codex などの AI アシスタントに以下のように話しかけるだけです。

```
「OCI の見積りを作って。Compute E4 を 4OCPU×2台、ADB ATP を 4ECPU で。」
「この Excel を見積もって。」（Excel ファイルを添付）
```

AI アシスタントが `skill.md` を参照して自動的にスクリプトを実行します。

### スクリプトを直接実行する場合

#### JSON でリソースを指定

```bash
python estimate.py --resources '[
  {"name": "Webサーバー", "type": "compute_e4", "ocpus": 4, "memory_gb": 32, "count": 2},
  {"name": "Autonomous DB", "type": "autonomous_db_atp", "ecpus": 4, "storage_gb": 1024}
]'
```

#### YAML ファイルを指定

```bash
python estimate.py --resources example.yaml
```

#### オプション

| オプション | 説明 | デフォルト |
|---|---|---|
| `--currency` | 通貨コード | JPY |
| `--hours` | 月あたり稼働時間 | 744（31日×24時間） |
| `--project` | プロジェクト名 | （空） |
| `--no-csv` | CSV 出力を省略 | false |

---

## 出力

- ターミナルに見積り結果を表示
- `output/estimate_<timestamp>.csv` に CSV を保存

---

## 対応サービス

| サービス | type キー |
|---|---|
| Compute E4 | `compute_e4` |
| Compute E5 | `compute_e5` |
| Block Volume | `block_volume` |
| Object Storage（標準） | `object_storage` |
| Object Storage（低頻度） | `object_storage_ia` |
| Autonomous DB ATP | `autonomous_db_atp` |
| Autonomous DB ADW | `autonomous_db_adw` |
| アウトバウンド通信（APAC） | `outbound_transfer_apac` |

---

## ディレクトリ構成

```
oci-cost-estimator/
├── README.md
├── skill.md               # AI アシスタント向けスキル定義
├── estimate.py            # メインスクリプト
├── sku_map.yaml           # SKU 対応表
├── example.yaml           # 構成定義サンプル
├── requirements.txt
├── .gitignore
└── docs/
    └── sku_reference.md   # SKU 一覧・Price List API 仕様
```

---

## 開発状況

- [x] 設計・SKU 調査
- [x] `estimate.py` 実装
- [x] `skill.md` 整備（対話モード・Excel モード）
- [ ] テスト
- [ ] 対応サービス追加（E3、A1、A2 など）
