# OCI Cost Estimator スキル

Claude Code / Cline / Codex がこのプロジェクトを使う際の参照ドキュメント。

## 概要

OCI の見積りを2つのモードで実行できる。

| モード | 使い方 |
|---|---|
| **対話モード** | ユーザーと会話しながらリソース要件を聞き出して見積る |
| **Excel モード** | ユーザーが提供した Excel ファイルを読んで見積る |

どちらのモードも最終的に `estimate.py` を呼び出して計算・CSV 出力する。

---

## 対話モード

### ユーザーから聞き出す情報

以下を順番に確認する。必要ないものはスキップしてよい。

```
1. プロジェクト名（任意）
2. 通貨（デフォルト: JPY）
3. 月あたり稼働時間（デフォルト: 744h = 31日×24時間）
4. リソース一覧:
   - Compute: Shape（E4/E5）、OCPU 数、メモリ GB、台数
   - Block Volume: サイズ GB、本数
   - Object Storage: サイズ GB（標準 or 低頻度）
   - Autonomous DB: ATP or ADW、ECPU 数、ストレージ GB
   - アウトバウンド通信: GB/月
```

### 質問例

```
見積りを作成します。以下を教えてください。

1. プロジェクト名は何ですか？
2. Compute が必要ですか？（Shape、OCPU 数、メモリ、台数）
3. データベースは必要ですか？（Autonomous DB ATP / ADW）
4. ストレージは必要ですか？（Block Volume / Object Storage）
5. アウトバウンド通信量の目安はありますか？
```

---

## Excel モード

### 手順

1. ユーザーから Excel ファイルを受け取る
2. ファイルを読んで以下を抽出する:
   - サービス名（Compute、ADB など）
   - スペック（OCPU 数、メモリ、ECPU 数、ストレージ容量など）
   - 台数・数量
3. 対応する `type` キーに変換する（下記 対応サービス一覧 参照）
4. JSON を組み立てて `estimate.py` を呼び出す

### 注意

- 列名はお客さんによって異なる。内容を見て柔軟に解釈すること
- 単位に注意（TB → GB 変換など）
- 不明なサービスは無視せずユーザーに確認する

---

## estimate.py の呼び方

### 基本

```bash
python estimate.py --resources '<JSON>'
```

### JSON フォーマット（リソース配列）

```json
[
  {"name": "Webサーバー", "type": "compute_e4", "ocpus": 4, "memory_gb": 32, "count": 2},
  {"name": "ブロックボリューム", "type": "block_volume", "size_gb": 500, "count": 2},
  {"name": "Autonomous DB", "type": "autonomous_db_atp", "ecpus": 4, "storage_gb": 1024},
  {"name": "オブジェクトストレージ", "type": "object_storage", "size_gb": 1000},
  {"name": "アウトバウンド通信", "type": "outbound_transfer_apac", "size_gb": 100}
]
```

### YAML ファイルを渡す場合

```bash
python estimate.py --resources example.yaml
```

### オプション

| オプション | 説明 | デフォルト |
|---|---|---|
| `--currency` | 通貨コード | JPY |
| `--hours` | 月あたり稼働時間 | 744 |
| `--project` | プロジェクト名 | （空） |
| `--no-csv` | CSV 出力を省略 | false |

### 出力

- ターミナル: 見積り結果の表示
- `output/estimate_<timestamp>.csv`: CSV ファイル
- 標準出力: JSON（AI が結果を使う場合に利用）

---

## 対応サービス一覧

| サービス | type キー | 必要パラメータ |
|---|---|---|
| Compute E4 | `compute_e4` | `ocpus`, `memory_gb`, `count` |
| Compute E5 | `compute_e5` | `ocpus`, `memory_gb`, `count` |
| Block Volume | `block_volume` | `size_gb`, `count` |
| Object Storage（標準） | `object_storage` | `size_gb` |
| Object Storage（低頻度） | `object_storage_ia` | `size_gb` |
| Autonomous DB ATP | `autonomous_db_atp` | `ecpus`, `storage_gb` |
| Autonomous DB ADW | `autonomous_db_adw` | `ecpus`, `storage_gb` |
| アウトバウンド通信（APAC） | `outbound_transfer_apac` | `size_gb` |

---

## 結果の伝え方

見積り結果は以下の形式でユーザーに伝える。

```
プロジェクト: ○○システム

| リソース名          | 月額（JPY）   |
|---------------------|--------------|
| Webサーバー（OCPU） | 12,345 円    |
| Webサーバー（MEM）  | 3,456 円     |
| ...                 | ...          |
| 合計                | XX,XXX 円    |

CSV を output/ に保存しました。
```

---

## セットアップ（同僚向け）

```bash
git clone https://github.com/morimoriharuki/oci-cost-estimator.git
cd oci-cost-estimator
pip install -r requirements.txt
```

これだけで使えます。API キー不要。
