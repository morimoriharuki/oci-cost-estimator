# SKU リファレンス

Price List API で確認済みの SKU 一覧。

## Price List API

- URL: `https://apexapps.oracle.com/pls/apex/cetools/api/v1/products/?currencyCode=JPY`
- 認証不要・公開 API
- 最終確認: 2026-04-09

## 確認済み SKU 一覧

| サービス | partNumber | 課金単位 |
|---|---|---|
| Compute E4 OCPU | B93113 | OCPU Per Hour |
| Compute E4 Memory | B93114 | Gigabyte Per Hour |
| Compute E5 OCPU | B97384 | OCPU Per Hour |
| Compute E5 Memory | B97385 | Gigabytes Per Hour |
| Block Volume | B91961 | GB Per Month |
| Object Storage | B91628 | GB Per Month |
| Object Storage (低頻度) | B93000 | GB Per Month |
| ADB ATP ECPU | B95702 | ECPU Per Hour |
| ADB ATP Storage | B95706 | GB Per Month |
| ADB ADW ECPU | B95701 | ECPU Per Hour |
| ADB ADW Storage | B95754 | GB Per Month |
| アウトバウンド通信 (APAC) | B93455 | GB Per Month |

## 備考

- OCI Load Balancer: SKU なし（通信量のみ課金）
- E3/A1/A2 Shape: 必要に応じて追加
- SKU は廃止リスクがあるため、`displayName` による動的検索も検討中
