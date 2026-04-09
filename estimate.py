#!/usr/bin/env python3
"""
OCI Cost Estimator
OCI Price List API から最新価格を取得し、CSV 見積りを生成するスクリプト。

【設計方針】
  AI（Claude Code / Cline / Codex 等）が services/*.yaml から partNumber を特定し、
  このスクリプトに渡す。スクリプトは partNumber で API を引いて最新価格を取得する。
  → スクリプト側に SKU の知識が不要。新サービスが増えても変更不要。

【使い方】
  # リソース定義 JSON を渡して見積り
  python estimate.py --resources '[
    {"name": "WebサーバーOCPU", "partNumber": "B93113", "qty": 8, "unit_type": "hourly"},
    {"name": "WebサーバーMem",  "partNumber": "B93114", "qty": 64, "unit_type": "hourly"},
    {"name": "ADB ATP ECPU",   "partNumber": "B95702", "qty": 4,  "unit_type": "hourly"},
    {"name": "ADB ATP Storage","partNumber": "B95706", "qty": 1024,"unit_type": "monthly"}
  ]'

  # YAML / JSON ファイルを渡す
  python estimate.py --resources example.yaml

  # SKU を検索する（AI がサービスを調べる用）
  python estimate.py --search "load balancer"
  python estimate.py --search "E5 OCPU"

  # 全 SKU 一覧を表示
  python estimate.py --list-skus
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
import yaml

PRICE_LIST_URL = "https://apexapps.oracle.com/pls/apex/cetools/api/v1/products/"
HOURS_PER_MONTH_DEFAULT = 744  # 31日 × 24時間
SERVICES_DIR = Path(__file__).parent / "services"
OUTPUT_DIR = Path(__file__).parent / "output"


# ---------------------------------------------------------------------------
# Price List API
# ---------------------------------------------------------------------------

def fetch_price_list(currency: str = "JPY") -> dict:
    """OCI Price List API から全 SKU の最新価格を取得する。"""
    print(f"[INFO] OCI Price List API から最新価格を取得中... (通貨: {currency})", file=sys.stderr)
    resp = requests.get(PRICE_LIST_URL, params={"currencyCode": currency}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("items", [])

    price_map = {}
    for item in items:
        pn = item.get("partNumber")
        if not pn:
            continue
        price = None
        for loc in item.get("currencyCodeLocalizations", []):
            if loc.get("currencyCode") == currency:
                prices = loc.get("prices", [])
                if prices:
                    price = prices[0].get("value")
                break
        price_map[pn.upper()] = {
            "displayName": item.get("displayName", ""),
            "metricName": item.get("metricName", ""),
            "serviceCategory": item.get("serviceCategory", ""),
            "price": price,
        }

    print(f"[INFO] {len(price_map)} SKU の価格を取得しました。", file=sys.stderr)
    return price_map


# ---------------------------------------------------------------------------
# SKU 検索（AI 支援用）
# ---------------------------------------------------------------------------

def search_skus(keyword: str, currency: str = "JPY") -> list:
    """displayName にキーワードを含む SKU を検索して返す。"""
    price_map = fetch_price_list(currency)
    keyword_lower = keyword.lower()
    results = []
    for pn, info in price_map.items():
        if keyword_lower in info["displayName"].lower():
            results.append({
                "partNumber": pn,
                "displayName": info["displayName"],
                "metricName": info["metricName"],
                "serviceCategory": info["serviceCategory"],
                "price": info["price"],
            })
    results.sort(key=lambda x: x["displayName"])
    return results


def list_all_skus(currency: str = "JPY") -> list:
    """全 SKU 一覧を返す。"""
    price_map = fetch_price_list(currency)
    results = [
        {
            "partNumber": pn,
            "displayName": info["displayName"],
            "serviceCategory": info["serviceCategory"],
            "price": info["price"],
            "metricName": info["metricName"],
        }
        for pn, info in price_map.items()
    ]
    results.sort(key=lambda x: (x["serviceCategory"], x["displayName"]))
    return results


# ---------------------------------------------------------------------------
# 見積り計算
# ---------------------------------------------------------------------------

def calculate_monthly(item: dict, price_jpy: float, hours_per_month: int) -> float:
    """1行分の月額を計算する。"""
    qty = item.get("qty", 0)
    unit_type = item.get("unit_type", "monthly")

    if unit_type == "hourly":
        return round(price_jpy * qty * hours_per_month, 2)
    elif unit_type in ("monthly", "request"):
        return round(price_jpy * qty, 2)
    elif unit_type == "free":
        return 0.0
    else:
        return round(price_jpy * qty, 2)


def generate_estimate(
    resources: list,
    currency: str = "JPY",
    hours_per_month: int = HOURS_PER_MONTH_DEFAULT,
) -> tuple:
    """
    見積りを計算して (rows, total) を返す。

    resources の各要素:
      - name        : 表示名（任意）
      - partNumber  : OCI SKU（例: B93113）
      - qty         : 数量（OCPU 数、GB 数など）
      - unit_type   : "hourly" / "monthly" / "request" / "free"
      - note        : 備考（任意）
    """
    price_map = fetch_price_list(currency)
    rows = []

    for item in resources:
        pn = item.get("partNumber", "").upper()
        name = item.get("name", pn)
        qty = item.get("qty", 0)
        unit_type = item.get("unit_type", "monthly")
        note = item.get("note", "")

        if not pn:
            print(f"[WARN] partNumber が未指定のリソースをスキップ: {name}", file=sys.stderr)
            continue

        if pn not in price_map:
            print(f"[WARN] SKU {pn} が Price List に見つかりません。", file=sys.stderr)
            rows.append({
                "リソース名": name,
                "partNumber": pn,
                "数量": qty,
                "課金タイプ": unit_type,
                f"単価({currency})": "取得失敗",
                f"月額({currency})": "計算不可",
                "備考": note,
            })
            continue

        info = price_map[pn]
        unit_price = info["price"]
        display_name = info["displayName"]

        if unit_type == "free" or unit_price is None or unit_price == 0:
            monthly = 0.0
            unit_price_display = "無料"
        else:
            monthly = calculate_monthly(item, unit_price, hours_per_month)
            unit_price_display = unit_price

        rows.append({
            "リソース名": name,
            "partNumber": pn,
            "SKU名称": display_name,
            "数量": qty,
            "課金タイプ": unit_type,
            f"単価({currency})": unit_price_display,
            f"月額({currency})": monthly,
            "備考": note,
        })

    total = sum(
        r[f"月額({currency})"]
        for r in rows
        if isinstance(r.get(f"月額({currency})"), (int, float))
    )
    return rows, round(total, 2)


# ---------------------------------------------------------------------------
# 出力
# ---------------------------------------------------------------------------

def print_summary(rows: list, total: float, currency: str, project: str = ""):
    """ターミナルに見積り結果を表示する。"""
    if project:
        print(f"\n{'='*65}")
        print(f"  プロジェクト: {project}")
    print(f"{'='*65}")
    print(f"{'リソース名':<35} {'月額':>15}")
    print(f"{'-'*65}")
    for row in rows:
        name = row["リソース名"][:34]
        monthly = row.get(f"月額({currency})", "-")
        if isinstance(monthly, float):
            monthly_str = f"{monthly:>14,.0f} {currency}"
        else:
            monthly_str = str(monthly)
        print(f"{name:<35} {monthly_str:>15}")
    print(f"{'='*65}")
    print(f"{'合計':<35} {total:>14,.0f} {currency}")
    print(f"{'='*65}\n")


def export_csv(rows: list, total: float, currency: str, project: str = "") -> Path:
    """CSV ファイルに出力して保存先パスを返す。"""
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_project = project.replace(" ", "_").replace("/", "_") if project else "estimate"
    filename = f"{safe_project}_{timestamp}.csv"
    filepath = OUTPUT_DIR / filename

    if not rows:
        print("[WARN] 出力する行がありません。", file=sys.stderr)
        return None

    fieldnames = list(rows[0].keys())
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        total_row = {k: "" for k in fieldnames}
        total_row["リソース名"] = "【合計】"
        total_row[f"月額({currency})"] = total
        writer.writerow(total_row)

    return filepath


def print_search_results(results: list, currency: str):
    """SKU 検索結果をターミナルに表示する。"""
    if not results:
        print("該当する SKU が見つかりませんでした。")
        return
    print(f"\n{'partNumber':<12} {'価格':>10} {'課金単位':<30} {'displayName'}")
    print("-" * 100)
    for r in results:
        price = f"{r['price']:>10.3f}" if r["price"] else "      無料"
        print(f"{r['partNumber']:<12} {price} {r['metricName']:<30} {r['displayName']}")
    print(f"\n{len(results)} 件見つかりました。")
    # JSON でも出力（AI が使いやすい）
    print(json.dumps(results, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# 入力パース
# ---------------------------------------------------------------------------

def parse_resources(raw: str) -> tuple:
    """
    文字列から (resources, project, currency, hours_per_month) を返す。
    JSON / YAML 両対応。
    """
    project = ""
    currency = "JPY"
    hours = HOURS_PER_MONTH_DEFAULT

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        try:
            data = yaml.safe_load(raw)
        except Exception as e:
            print(f"[ERROR] 入力の解析に失敗しました: {e}", file=sys.stderr)
            sys.exit(1)

    if isinstance(data, dict):
        project = data.get("project", project)
        currency = data.get("currency", currency)
        hours = data.get("hours_per_month", hours)
        resources = data.get("resources", [])
    elif isinstance(data, list):
        resources = data
    else:
        print("[ERROR] 入力は JSON 配列または resources キーを持つ辞書形式にしてください。", file=sys.stderr)
        sys.exit(1)

    return resources, project, currency, hours


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="OCI Cost Estimator - partNumber を指定して最新価格で見積りを生成",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--resources", "-r", help="リソース定義（JSON文字列 / ファイルパス / - でstdin）")
    mode.add_argument("--search", "-s", metavar="KEYWORD", help="SKU をキーワード検索（例: 'E5 OCPU'）")
    mode.add_argument("--list-skus", action="store_true", help="全 SKU 一覧を表示")

    parser.add_argument("--currency", default="JPY", help="通貨コード（デフォルト: JPY）")
    parser.add_argument("--hours", type=int, default=HOURS_PER_MONTH_DEFAULT, help="月あたり稼働時間（デフォルト: 744）")
    parser.add_argument("--project", default="", help="プロジェクト名")
    parser.add_argument("--no-csv", action="store_true", help="CSV を出力しない")

    args = parser.parse_args()

    # --- SKU 検索モード ---
    if args.search:
        results = search_skus(args.search, args.currency)
        print_search_results(results, args.currency)
        return

    # --- 全 SKU 一覧モード ---
    if args.list_skus:
        results = list_all_skus(args.currency)
        print_search_results(results, args.currency)
        return

    # --- 見積りモード ---
    if args.resources == "-":
        raw = sys.stdin.read()
    elif os.path.isfile(args.resources):
        with open(args.resources, encoding="utf-8") as f:
            raw = f.read()
    else:
        raw = args.resources

    resources, project, currency, hours = parse_resources(raw)
    project = project or args.project
    currency = currency or args.currency
    hours = hours or args.hours

    rows, total = generate_estimate(resources, currency=currency, hours_per_month=hours)
    print_summary(rows, total, currency, project)

    if not args.no_csv:
        filepath = export_csv(rows, total, currency, project)
        if filepath:
            print(f"[INFO] CSV を保存しました: {filepath}", file=sys.stderr)

    result = {
        "project": project,
        "currency": currency,
        "hours_per_month": hours,
        "total_monthly": total,
        "rows": rows,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
