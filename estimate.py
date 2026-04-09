#!/usr/bin/env python3
"""
OCI Cost Estimator
OCI Price List API から最新価格を取得し、CSV 見積りを生成するスクリプト。

使い方:
    python estimate.py --resources '[{"name":"Webサーバー","type":"compute_e4","ocpus":4,"memory_gb":32,"count":2}]'
    python estimate.py --resources resources.json
    python estimate.py --resources -   # stdin から JSON を読み込む
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
SKU_MAP_PATH = Path(__file__).parent / "sku_map.yaml"
OUTPUT_DIR = Path(__file__).parent / "output"


def fetch_price_list(currency: str = "JPY") -> dict:
    """OCI Price List API から全 SKU の価格を取得する。"""
    print(f"[INFO] OCI Price List API から最新価格を取得中... (通貨: {currency})", file=sys.stderr)
    resp = requests.get(PRICE_LIST_URL, params={"currencyCode": currency}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("items", [])

    price_map = {}
    for item in items:
        part_number = item.get("partNumber")
        if not part_number:
            continue
        # 価格を取得
        price = None
        for loc in item.get("currencyCodeLocalizations", []):
            if loc.get("currencyCode") == currency:
                prices = loc.get("prices", [])
                if prices:
                    price = prices[0].get("value")
                break
        price_map[part_number] = {
            "displayName": item.get("displayName", ""),
            "metricName": item.get("metricName", ""),
            "price": price,
        }
    print(f"[INFO] {len(price_map)} SKU の価格を取得しました。", file=sys.stderr)
    return price_map


def load_sku_map() -> dict:
    """sku_map.yaml を読み込む。"""
    with open(SKU_MAP_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def calculate_resource(resource: dict, sku_map: dict, price_map: dict, hours_per_month: int, currency: str) -> list:
    """
    1リソースの月額を計算し、CSV 行のリストで返す。
    1リソースが複数の課金項目（OCPU + Memory など）を持つ場合は複数行になる。
    """
    rtype = resource.get("type")
    name = resource.get("name", rtype)
    count = resource.get("count", 1)

    if rtype not in sku_map:
        print(f"[WARN] 未対応のリソースタイプ: {rtype}（スキップ）", file=sys.stderr)
        return []

    rows = []
    sku_entries = sku_map[rtype]

    for component, sku_info in sku_entries.items():
        part_number = sku_info["partNumber"]
        unit = sku_info["unit"]

        if part_number not in price_map:
            print(f"[WARN] SKU {part_number} の価格が見つかりません。", file=sys.stderr)
            unit_price = None
        else:
            unit_price = price_map[part_number]["price"]

        # 数量の決定
        if component == "ocpu":
            qty = resource.get("ocpus", 0)
            total_qty = qty * count
            billing_unit = f"OCPU × {hours_per_month}h × {count}台"
            monthly = round(unit_price * qty * hours_per_month * count, 2) if unit_price else None
        elif component == "memory":
            qty = resource.get("memory_gb", 0)
            total_qty = qty * count
            billing_unit = f"{qty}GB × {hours_per_month}h × {count}台"
            monthly = round(unit_price * qty * hours_per_month * count, 2) if unit_price else None
        elif component == "ecpu":
            qty = resource.get("ecpus", 0)
            total_qty = qty * count
            billing_unit = f"ECPU × {hours_per_month}h × {count}台"
            monthly = round(unit_price * qty * hours_per_month * count, 2) if unit_price else None
        elif component == "storage":
            qty = resource.get("storage_gb", resource.get("size_gb", 0))
            total_qty = qty * count
            billing_unit = f"{qty}GB × {count}"
            monthly = round(unit_price * qty * count, 2) if unit_price else None
        elif component == "transfer":
            qty = resource.get("size_gb", 0)
            total_qty = qty * count
            billing_unit = f"{qty}GB × {count}"
            monthly = round(unit_price * qty * count, 2) if unit_price else None
        else:
            continue

        label = name if len(sku_entries) == 1 else f"{name}（{component.upper()}）"

        rows.append({
            "リソース名": label,
            "タイプ": rtype,
            "SKU": part_number,
            "数量": total_qty,
            "課金単位": billing_unit,
            f"単価({currency})": unit_price if unit_price is not None else "取得失敗",
            f"月額({currency})": monthly if monthly is not None else "計算不可",
        })

    return rows


def generate_estimate(resources: list, currency: str = "JPY", hours_per_month: int = HOURS_PER_MONTH_DEFAULT) -> tuple:
    """見積りを計算して (rows, total) を返す。"""
    sku_map = load_sku_map()
    price_map = fetch_price_list(currency)

    all_rows = []
    for resource in resources:
        rows = calculate_resource(resource, sku_map, price_map, hours_per_month, currency)
        all_rows.extend(rows)

    # 合計
    total = 0
    for row in all_rows:
        v = row.get(f"月額({currency})")
        if isinstance(v, (int, float)):
            total += v

    return all_rows, round(total, 2)


def export_csv(rows: list, total: float, currency: str, project: str = "") -> Path:
    """CSV ファイルに出力して保存先パスを返す。"""
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"estimate_{timestamp}.csv"
    filepath = OUTPUT_DIR / filename

    if not rows:
        print("[WARN] 出力する行がありません。", file=sys.stderr)
        return None

    fieldnames = list(rows[0].keys())

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

        # 合計行
        total_row = {k: "" for k in fieldnames}
        total_row["リソース名"] = "【合計】"
        total_row[f"月額({currency})"] = total
        writer.writerow(total_row)

    return filepath


def print_summary(rows: list, total: float, currency: str, project: str = ""):
    """見積り結果をターミナルに表示する。"""
    if project:
        print(f"\n{'='*60}")
        print(f"  プロジェクト: {project}")
    print(f"{'='*60}")
    print(f"{'リソース名':<30} {'月額':>15}")
    print(f"{'-'*60}")
    for row in rows:
        name = row["リソース名"]
        monthly = row.get(f"月額({currency})", "-")
        if isinstance(monthly, float):
            monthly = f"{monthly:,.0f} {currency}"
        print(f"{name:<30} {str(monthly):>15}")
    print(f"{'='*60}")
    print(f"{'合計':<30} {total:>14,.0f} {currency}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="OCI Cost Estimator")
    parser.add_argument(
        "--resources", "-r", required=True,
        help="リソース定義 JSON（文字列、ファイルパス、または - で stdin）"
    )
    parser.add_argument("--currency", default="JPY", help="通貨コード（デフォルト: JPY）")
    parser.add_argument("--hours", type=int, default=HOURS_PER_MONTH_DEFAULT, help="月あたり稼働時間（デフォルト: 744）")
    parser.add_argument("--project", default="", help="プロジェクト名")
    parser.add_argument("--no-csv", action="store_true", help="CSV を出力しない")
    args = parser.parse_args()

    # リソース定義の読み込み
    if args.resources == "-":
        raw = sys.stdin.read()
    elif os.path.isfile(args.resources):
        with open(args.resources, encoding="utf-8") as f:
            raw = f.read()
    else:
        raw = args.resources

    try:
        resources = json.loads(raw)
        if isinstance(resources, dict):
            # YAML 形式の辞書（project, resources キーを持つ場合）に対応
            if "resources" in resources:
                args.project = resources.get("project", args.project)
                args.currency = resources.get("currency", args.currency)
                args.hours = resources.get("hours_per_month", args.hours)
                resources = resources["resources"]
    except json.JSONDecodeError:
        # JSON でなければ YAML として試みる
        try:
            data = yaml.safe_load(raw)
            if isinstance(data, dict) and "resources" in data:
                args.project = data.get("project", args.project)
                args.currency = data.get("currency", args.currency)
                args.hours = data.get("hours_per_month", args.hours)
                resources = data["resources"]
            else:
                resources = data
        except Exception as e:
            print(f"[ERROR] リソース定義の解析に失敗しました: {e}", file=sys.stderr)
            sys.exit(1)

    # 見積り計算
    rows, total = generate_estimate(resources, currency=args.currency, hours_per_month=args.hours)

    # 結果表示
    print_summary(rows, total, args.currency, args.project)

    # CSV 出力
    if not args.no_csv:
        filepath = export_csv(rows, total, args.currency, args.project)
        if filepath:
            print(f"[INFO] CSV を保存しました: {filepath}", file=sys.stderr)

    # AI が結果を使いやすいよう JSON でも出力
    result = {
        "project": args.project,
        "currency": args.currency,
        "total_monthly": total,
        "rows": rows,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
