# レシピ提案アプリ データセット

日本の家庭料理 150 件と食材マスタ 135 件。アプリに同梱して使う参照データです。

## ファイル

| ファイル | 内容 |
|---|---|
| `recipes.csv` | レシピ 150 件 |
| `ingredients.csv` | 食材マスタ 135 件（調味料 34 / 画像認識の候補 101） |
| `image_manifest.csv` | 料理画像の収集作業リスト |
| `validate_data.py` | 整合性チェック。**CSV を編集したら必ず実行** |
| `data/images/category/*.jpg` | カテゴリ別プレースホルダ画像 8 枚 |

## recipes.csv

| 列 | 必須 | 例 | 用途 |
|---|---|---|---|
| `id` | ✔ | `1` | 主キー |
| `name` | ✔ | `親子丼` | 表示。外部リンクの検索語にも使う |
| `category` | ✔ | `丼物` | 絞り込み・画像フォールバック |
| `ingredients` | ✔ | `鶏もも肉;卵;玉ねぎ` | **照合・合致率・不足食材の算出対象** |
| `amounts` | — | `200g;3個;1個` | 表示専用。`ingredients` と同数・同順 |
| `minutes` | ✔ | `20` | ソート・絞り込み |
| `servings` | — | `2` | 表示専用 |
| `steps` | ✔ | `玉ねぎを薄切りにする;...` | 手順表示 |
| `image` | — | `oyakodon.jpg` | `data/images/` 配下のファイル名 |

カテゴリ内訳: 主菜 45 / 副菜 30 / 麺類 18 / 汁物 15 / 丼物 15 / ご飯物 12 / 鍋物 8 / サラダ 7

## ingredients.csv

| 列 | 例 | 用途 |
|---|---|---|
| `name` | `玉ねぎ` | 正式表記。入力欄の候補ラベル |
| `en_label` | `onion` | 画像認識モデルに渡す英語ラベル |
| `is_seasoning` | `FALSE` | `TRUE` は合致率の計算から除外 |
| `aliases` | `玉葱;たまねぎ;オニオン` | 表記ゆれ。入力時に `name` へ変換 |

このファイル 1 つで **候補ラベルの供給・英語変換・調味料判定・表記の正規化** を兼ねます。

## 編集ルール

1. **区切り文字は半角 `;`。** 全角 `；` は動きません（`validate_data.py` が検出します）
2. **編集は Google Sheets で行い、CSV エクスポートしてコミット。** 4 人が同じ CSV を直接触るとコンフリクトで壊れます
3. **`ingredients` に書く食材名は必ず `ingredients.csv` の `name` に存在させる。** マスタに無い名前は照合時に無視されます
4. **マスタに食材を足したら、その食材を使うレシピも 1 件以上足す。** 選べるのにヒットしない選択肢になります
5. **`amounts` を書くなら `ingredients` と個数を揃える。** 揃えられないなら空欄に

## 画像

`image` 列には 150 件すべてにファイル名が入っていますが、**画像ファイル自体は未配置**です。
`data/images/` に置いたものから順に反映され、無いものはカテゴリ画像で代替されます。

```python
import os
path = f"data/images/{row['image']}" if row.get("image") else ""
if not path or not os.path.exists(path):
    path = f"data/images/category/{row['category']}.jpg"
```

`os.path.exists` は必須です。CSV にファイル名があるのに画像を置き忘れても落ちません。

`image_manifest.csv` の `status` / `source_url` / `license` を埋めながら作業してください。
**出典を記録しないと公開時にライセンスを確認できなくなります。**

## 合致率と不足食材

```python
main = {i for i in row["ingredients"].split(";") if not is_seasoning[i]}
rate    = len(main & have) / len(main)   # 合致率
missing = main - have                    # 不足食材
```

調味料を除外するのが要点です。除外しないと「醤油がないので作れません」が量産されます。

## 検証

```bash
python validate_data.py
```

エラーがあれば終了コード 1 を返します。チェック内容は、食材名の重複、エイリアスの衝突、
全角セミコロンの混入、`ingredients` と `amounts` の個数不一致、マスタに無い食材、
主材料 0 件、`minutes` の型、画像の配置漏れ、未使用のマスタ食材です。
