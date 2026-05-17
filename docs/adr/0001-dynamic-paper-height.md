# 0001. `?paper_height=auto` クエリで Chrome の `--print-to-pdf-paper-height` を動的化する

## ステータス
承認済み

## コンテキスト

Angie の Issue #2087 (梱包ラベル複数受注対応) で、1 箱に複数受注が紐づく場合に
全受注分の注文番号・貴社特記をラベルに縦に列挙する仕様を実装した。設計上は
`@page { size: 80mm auto; }` で連続紙に流したかったが、当時の印刷サーバーは
Chrome に対し用紙サイズを固定値で渡しており、CSS の `size: auto` を無効化して
しまうため紙面下端で切れる懸念があった。

短期対応として Angie 側で `@page { size: 80mm 250mm; }` の余裕値固定で吸収し
(Angie PR #2095 / Issue #2087)、後続課題として印刷サーバー側の動的化を
Angie の Issue #2090 で追っている。本 ADR は Angie #2090 の上流対応となる
本リポジトリ Issue #1 の決定事項を記録するもの。

### 現状の挙動 (本リポジトリ)

`config.py` の `CHROME_ARGS` で次のように用紙幅のみ固定指定されている。

```python
CHROME_ARGS = [
    ...,
    '--print-to-pdf-paper-width=3.14961'  # = 80mm をインチ換算
]
```

`--print-to-pdf-paper-height` は未設定のため、現状は Chrome のデフォルト挙動
(レターサイズ相当のページ送り) に従っている。印刷リクエスト URL のクエリは
`print_token` のみで、用紙寸法を呼び出し側から制御する手段がない。

## 決定

印刷リクエスト URL に **`paper_height` クエリ** を追加し、Chrome の
`--print-to-pdf-paper-height` を動的に切り替えられるようにする。

| `paper_height` の値 | Chrome 引数の組み立て |
|---|---|
| 省略 (未指定)       | `--print-to-pdf-paper-height` を渡さない (現状互換) |
| `auto`              | `--print-to-pdf-paper-height` を渡さない (CSS `@page size` に従わせる) |
| 整数 (例: `250`)    | mm→inch 換算した値で `--print-to-pdf-paper-height=<inch>` を渡す |

### 単位と換算

- URL クエリは **mm 単位の整数** で受け取る (Angie 側 Blade の `@page` 表記と揃える)
- Chrome に渡す際は `mm / 25.4` で **inch 値** に換算する
- 既存の `paper_width=3.14961` (= 80mm) と整合するよう、内部で同じ換算ロジックを通す

### バリデーション

- 許容値: `auto` または `1 ≦ N ≦ 3000` の整数
- 不正値 (数値以外・負数・ゼロ・上限超過) はジョブを **失敗扱い** とし、
  `print_queue.error_message` に「invalid paper_height」を記録する
- 入力起因の恒久エラーであり、URL が変わらない限り再試行しても直らないため、
  `PrinterService.print_web_url` の戻り値で `retryable=False` を返し、
  `QueueProcessor` 側はリトライ上限を待たずに即 `Failed` ステータスに落とす

### Chrome に渡す URL の扱い

印刷サーバー専用パラメータのため、Chrome に渡す URL からは `paper_height`
クエリを除去する。Laravel 側の Blade ページが `paper_height` を解釈する
必要はなく、未知クエリで挙動が変わる事故を防ぐ。

### ログ

採用した `--print-to-pdf-paper-height` の最終値、または「省略した事実」と
その理由 (`auto` か `未指定` か) をジョブログに残す。

## 理由

- **mm 単位で受ける**: Issue 起票時の表記、および Angie 側 Blade の `@page size`
  指定が mm ベースのため、API 境界も mm に揃えるのが呼び出し側の認知負荷が低い。
  inch 換算は印刷サーバー内部の Chrome 都合なので、サーバー側に閉じ込める。
- **未指定 = 引数省略**: 現コードでは `--print-to-pdf-paper-height` がそもそも
  指定されていない。Issue 本文の「既定値 50mm」は誤認であり、現場で稼働中の
  挙動を変えないことを優先する。
- **`auto` を別値として扱う**: 未指定との挙動は同じだが、呼び出し側の意図
  (「CSS の `@page size: 80mm auto;` を尊重させたい」) をログ・コードレベルで
  明示できる利点があるため、`paper_height` クエリ仕様としては別値として
  受け付け、内部処理で同じ分岐に合流させる。
- **Chrome に渡す URL から除去**: 印刷サーバーで完結する制御パラメータが
  Laravel 側に漏れると将来の予期せぬ干渉を生む。`print_token` と同じ扱いに
  する。

## 影響

- **後方互換**: 既存の `paper_height` 未指定呼び出しは従来通り動く。
- **Angie 側追従**: 本対応マージ後、Angie 側で `@page size: 80mm auto;`
  に戻して `?paper_height=auto` 付きで enqueue する PR を別途立てる
  (Angie #2090 のクローズ条件)。
- **スコープ外**: `paper_width` の動的化、URL クエリの追加認証、Angie 側
  Blade の `@page` 修正は本対応に含めない。
