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

### 手順（重要）

1. ユーザーが必要なサービスを伝える
2. **該当カテゴリの `services/*.yaml` を読んで `partNumber` を特定する**
3. `estimate.py --resources` に partNumber を渡して実行する

### 基本

```bash
# JSON 文字列で渡す
python estimate.py --resources '<JSON>'

# YAML / JSON ファイルで渡す
python estimate.py --resources example.yaml

# SKU をキーワード検索（サービスが不明なとき）
python estimate.py --search "E5 OCPU"
python estimate.py --search "network firewall"

# 全 SKU 一覧を表示
python estimate.py --list-skus
```

### JSON フォーマット（partNumber 指定方式）

```json
[
  {
    "name": "Webサーバー OCPU (E4×4OCPU×2台)",
    "partNumber": "B93113",
    "qty": 8,
    "unit_type": "hourly"
  },
  {
    "name": "Webサーバー Memory (E4×32GB×2台)",
    "partNumber": "B93114",
    "qty": 64,
    "unit_type": "hourly"
  },
  {
    "name": "ADB ATP ECPU",
    "partNumber": "B95702",
    "qty": 4,
    "unit_type": "hourly"
  },
  {
    "name": "ADB ATP Storage (1TB)",
    "partNumber": "B95706",
    "qty": 1024,
    "unit_type": "monthly"
  }
]
```

### unit_type の選び方

| unit_type | 計算式 | 使うサービス例 |
|---|---|---|
| `hourly` | 単価 × qty × hours_per_month | Compute OCPU/Memory、ADB ECPU |
| `monthly` | 単価 × qty | Storage GB、ADB Storage GB |
| `request` | 単価 × qty | API Gateway（100万リクエスト単位）|
| `free` | 0円 | Always Free 対象サービス |

### オプション

| オプション | 説明 | デフォルト |
|---|---|---|
| `--currency` | 通貨コード | JPY |
| `--hours` | 月あたり稼働時間 | 744 |
| `--project` | プロジェクト名 | （空） |
| `--no-csv` | CSV 出力を省略 | false |

### 出力

- ターミナル: 見積り結果の表示
- `output/<project>_<timestamp>.csv`: CSV ファイル
- 標準出力: JSON（AI が結果を使う場合に利用）

---

## カテゴリ別 SKU ファイル

見積り対象サービスに応じて、該当ファイルを参照すること。**必要なカテゴリだけ読む**（トークン節約）。

| カテゴリ | ファイル | 主なサービス |
|---|---|---|
| Compute | `services/compute.yaml` | E3/E4/E5/E6/A1/A2/A4/X9/GPU/BM/Secure Desktop |
| Database | `services/database.yaml` | ADB(ATP/ADW/JSON/APEX)/MySQL HeatWave/NoSQL/Redis/Oracle DB/PostgreSQL/GoldenGate |
| Storage | `services/storage.yaml` | Block Volume/Object Storage/Archive/低頻度/File Storage/Lustre/ZFS |
| Network | `services/network.yaml` | LB/FastConnect/WAF/DNS/Network Firewall/転送量/Health Check |
| Container | `services/container.yaml` | OKE/Functions/API Gateway/Streaming/Queue/Batch |
| AI & Analytics | `services/ai.yaml` | Gen AI（Cohere/Llama/Grok/Gemini/OpenAI）/Language/Vision/Speech/OAC/Data Integration/OpenSearch |
| Security | `services/security.yaml` | Vault(KMS)/Cloud Guard/Data Safe/IAM/Access Governance/DR |
| Operations | `services/operations.yaml` | Logging/Monitoring/Log Analytics/Ops Insights/Notifications/Fleet Management |
| Developer | `services/developer.yaml` | Visual Builder/OIC/SOA/Blockchain/WebLogic/WebCenter |

## 対応サービス一覧（主要）

| サービス | カテゴリファイル | partNumber 例 |
|---|---|---|
| Compute E4 | compute.yaml | B93113(OCPU), B93114(Mem) |
| Compute E5 | compute.yaml | B97384(OCPU), B97385(Mem) |
| GPU H100 | compute.yaml | B98415 |
| ADB ATP | database.yaml | B95702(ECPU), B95706(Storage) |
| ADB ADW | database.yaml | B95701(ECPU), B95754(Storage) |
| MySQL HeatWave | database.yaml | B108030(ECPU), B96626(HW) |
| Block Volume | storage.yaml | B91961 |
| Object Storage | storage.yaml | B91628（無料枠あり） |
| FastConnect 10G | network.yaml | B88326 |
| Network Firewall | network.yaml | B95403 |
| OKE Enhanced | container.yaml | B96545 |
| Gen AI Llama 4 | ai.yaml | B111035/B111036 |
| Gen AI Grok 4 | ai.yaml | B111438/B111439 |
| Vault Private | security.yaml | B90328 |
| Log Analytics | operations.yaml | B95634 |
| OIC Standard | developer.yaml | B89639 |

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
