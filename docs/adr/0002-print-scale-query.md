# 0002. `?print_scale=noscale` クエリで SumatraPDF の印刷縮尺を動的化する

## ステータス
承認済み

## コンテキスト

Angie の梱包ラベル (box_label) が実機印刷で用紙幅 (80mm) を使い切らず、左右に大きな
余白を持って縮小印刷される事象が報告された。原因は印刷経路の縮尺処理にある。

- Chrome は全ジョブ共通で `--print-to-pdf-paper-width=3.14961` (=80mm) を固定指定し
  (`config.py`)、`--print-to-pdf-paper-height` は ADR 0001 の `paper_height` クエリで
  動的化している。
- 梱包ラベルは受注数依存で可変長のため固定高さを指定できず、`paper_height` 未指定
  (または `auto`、両者は ADR 0001 で「Chrome 引数を渡さない」同一処理) だと Chrome は
  高さをレターサイズ相当 (≒279mm) のページ送りで生成する。
- PDF をプリンタへ送る際 SumatraPDF を `-print-settings 'paper=MKラベル,portrait,fit'`
  (`printer_service.py`) で呼んでいる。`fit` は縦横比を保ってページを用紙フォームに
  収めるため、279mm の縦長 PDF が MKラベル用紙フォーム高さ (固定) に収まるよう**全体が
  縮小**され、結果として**幅も比例して縮み**、左右余白になる。

MKラベル用紙は 80mm 幅・連続ロール紙で、プリンタ側に「末尾の空白部分を削除して印刷」
設定がある。固定高さに収まる他ラベルは `fit` でも等倍 (≒1.0) で印刷され、末尾空白削除で
実長にカットされて問題ない。梱包ラベルだけが可変長ゆえに `fit` の縮小に巻き込まれる。

### 制約

印刷サーバーは 1 インスタンスで全プリンタ・全ジョブ種別を処理し、Chrome 引数も
SumatraPDF の `-print-settings` も**全ジョブ共通のハードコード**で、ジョブ種別・プリンタ
別の分岐を持たない。A4 文書 (出荷明細書・納品書・梱包明細書) も同じ経路・同じ設定を
通る。したがってグローバルに `fit` → `noscale` へ変更すると A4 や他ラベルを壊す。

## 決定

印刷リクエスト URL に **`print_scale` クエリ** を追加し、呼び出し側 (Angie) がジョブ単位で
SumatraPDF の縮尺を制御できるようにする。`paper_height` (高さの軸) とは**独立した軸
(縮尺の軸)** として扱い、意味を二重化しない。

| `print_scale` の値 | SumatraPDF `-print-settings` の組み立て |
|---|---|
| 省略 (未指定)   | `paper=MKラベル,portrait,fit` (現状互換) |
| `fit`           | `paper=MKラベル,portrait,fit` |
| `noscale`       | `paper=MKラベル,portrait,noscale` (等倍印刷) |

梱包ラベルは `?print_scale=noscale` を送る。80mm 幅固定の PDF が等倍で印刷されて用紙
全幅を使い、可変長はプリンタの「末尾空白削除」が実長にカットする。

### バリデーション

- 許容値: `fit` または `noscale` の**完全一致**のみ
- 不正値 (許容外・空文字・複数指定) はジョブを**失敗扱い**とし、`error_message` に
  「invalid print_scale」を記録する。入力起因の恒久エラーであり再試行しても直らないため
  `retryable=False` を返し (ADR 0001 と同方針)、`QueueProcessor` は即 `Failed` に落とす。

### Chrome に渡す URL の扱い

印刷サーバー専用パラメータのため、Chrome に渡す URL からは `print_scale` クエリを
除去する (`print_token` / `paper_height` と同じ扱い)。実装上は `extract_paper_height`
で `paper_height` を除去した後の URL を `extract_print_scale` に通し、双方を除去する。

### ログ

採用した縮尺 (`fit` / `noscale`) をジョブログに残す。

## 理由

- **`paper_height` と別クエリにする**: 高さの軸と縮尺の軸は直交する関心事。`paper_height=auto`
  に「noscale」の意味を兼任させると、将来別ラベルが `auto` を送った際に意図せず縮尺が
  変わる信号汚染が起きる。専用クエリにすれば A4・他ラベルは `print_scale` 未送信で
  従来どおり `fit` のまま完全に不変。
- **未指定 = `fit`**: 現コードのハードコードが `fit` であり、既存の全ジョブ挙動を変えない
  ことを最優先する。
- **完全一致で検証**: 誤送信 (`Noscale`, `shrink` 等) を握りつぶさず明示的に失敗させる。

## 影響

- **後方互換**: 既存の `print_scale` 未指定呼び出しは従来どおり `fit` で動く。A4・他ラベルは
  不変。
- **Angie 側追従**: `PrintQueueService::queueBoxLabel` が梱包ラベル URL に
  `&print_scale=noscale` を付与する。
- **スコープ外**: 受注数がレターサイズ高さ (≒279mm) を超える超大量ケースで Chrome が
  2 ページ化しラベルが 2 枚出る既存課題は本対応では解消しない (本質対応は Angie #2090 の
  `@page: 80mm auto` 連続紙化)。`fit` 以外の縮尺 (`shrink` 等) の追加もスコープ外。
- **実機検証ゲート**: `noscale` は等倍印刷のため、(1) 用紙フォーム幅 80mm と PDF 幅 80mm の
  厳密一致で右端のバーコード/QR/文字が切れないこと、(2) プリンタの「末尾空白削除」が
  有効でレターサイズ高さの縦長 PDF が実長にカットされること、をマージ前にテスト印刷で
  確認する。
