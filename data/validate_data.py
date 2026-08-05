# -*- coding: utf-8 -*-
"""recipes.csv / ingredients.csv の整合性チェック

CSVを編集したら必ず実行する。
    python validate_data.py
エラーが1件でもあれば終了コード1を返すので、コミット前のフックにも使える。
"""
import csv, sys, os, collections

HERE = os.path.dirname(os.path.abspath(__file__))
SEP = ";"
errors, warns = [], []


def load(fn):
    path = os.path.join(HERE, fn)
    if not os.path.exists(path):
        print(f"[致命] {fn} が見つかりません")
        sys.exit(1)
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


ing_rows = load("ingredients.csv")
rec_rows = load("recipes.csv")

# ---------- 食材マスタ ----------
master, alias_owner = {}, {}
for r in ing_rows:
    name = (r["name"] or "").strip()
    if not name:
        errors.append("ingredients.csv: name が空の行がある")
        continue
    if name in master:
        errors.append(f"ingredients.csv: 食材名の重複 '{name}'")
    if r["is_seasoning"] not in ("TRUE", "FALSE"):
        errors.append(f"ingredients.csv: {name} の is_seasoning が TRUE/FALSE でない ('{r['is_seasoning']}')")
    if not (r["en_label"] or "").strip():
        errors.append(f"ingredients.csv: {name} の en_label が空(画像認識に使えない)")
    master[name] = r["is_seasoning"] == "TRUE"
    for a in [x.strip() for x in (r["aliases"] or "").split(SEP) if x.strip()]:
        if a in alias_owner:
            errors.append(f"ingredients.csv: エイリアス '{a}' が {alias_owner[a]} と {name} で重複")
        alias_owner[a] = name

for a, owner in alias_owner.items():
    if a in master:
        errors.append(f"ingredients.csv: エイリアス '{a}'({owner}) が正式名と衝突している")

# ---------- レシピ ----------
CATS = collections.Counter()
ids, names, used = set(), set(), set()
for r in rec_rows:
    rid, name = (r["id"] or "").strip(), (r["name"] or "").strip()
    tag = f"id={rid} {name}"
    if not rid.isdigit():
        errors.append(f"{tag}: id が数値でない")
    elif rid in ids:
        errors.append(f"{tag}: id の重複")
    ids.add(rid)
    if not name:
        errors.append(f"id={rid}: name が空")
    elif name in names:
        errors.append(f"{tag}: レシピ名の重複")
    names.add(name)
    CATS[r["category"]] += 1

    for col in ("ingredients", "amounts", "steps"):
        if "；" in (r[col] or ""):
            errors.append(f"{tag}: {col} に全角セミコロン「；」が混入している")

    ing_list = [x.strip() for x in (r["ingredients"] or "").split(SEP) if x.strip()]
    amt_list = [x.strip() for x in (r["amounts"] or "").split(SEP) if x.strip()]
    if not ing_list:
        errors.append(f"{tag}: ingredients が空")
    if amt_list and len(amt_list) != len(ing_list):
        errors.append(f"{tag}: ingredients {len(ing_list)}件 と amounts {len(amt_list)}件 が不一致")
    if len(set(ing_list)) != len(ing_list):
        dup = [k for k, v in collections.Counter(ing_list).items() if v > 1]
        errors.append(f"{tag}: 同じ食材が重複 {dup}")

    for i in ing_list:
        used.add(i)
        if i not in master:
            hint = f" (エイリアス '{i}' → '{alias_owner[i]}' を正式名に直す)" if i in alias_owner else ""
            errors.append(f"{tag}: マスタに無い食材 '{i}'{hint}")

    if ing_list and not [i for i in ing_list if i in master and not master[i]]:
        errors.append(f"{tag}: 主材料(調味料以外)が0件。合致率が計算できない")

    if not (r["minutes"] or "").strip().isdigit():
        errors.append(f"{tag}: minutes が数値でない")
    if len([x for x in (r["steps"] or "").split(SEP) if x.strip()]) < 2:
        warns.append(f"{tag}: 手順が2未満")

for n in master:
    if n not in used:
        warns.append(f"マスタの '{n}' はどのレシピにも登場しない(選べるが必ずヒットしない)")

# ---------- 画像 ----------
imgdir = os.path.join(HERE, "data", "images")
missing_img, blank_img = [], 0
for r in rec_rows:
    f = (r.get("image") or "").strip()
    if not f:
        blank_img += 1
    elif not os.path.exists(os.path.join(imgdir, f)):
        missing_img.append(f"{r['name']} → {f}")
img_done = len(rec_rows) - len(missing_img) - blank_img
IMG_PROGRESS = (f"画像 {img_done}/{len(rec_rows)} 配置済み"
                + (f" / 未配置 {len(missing_img)}" if missing_img else "")
                + (f" / image列が空 {blank_img}" if blank_img else "")
                + ("  ※未配置分はカテゴリ画像で代替されます" if (missing_img or blank_img) else ""))
for c in CATS:
    if not os.path.exists(os.path.join(imgdir, "category", f"{c}.jpg")):
        errors.append(f"カテゴリ画像 category/{c}.jpg が無い。フォールバックできない")

# ---------- 出力 ----------
print(f"レシピ {len(rec_rows)}件 / 食材 {len(master)}件"
      f"(調味料 {sum(master.values())} / 画像認識の候補 {len(master)-sum(master.values())})")
print("カテゴリ別:", dict(CATS))
print(IMG_PROGRESS)
if missing_img:
    print("  未配置の先頭5件:", "  /  ".join(missing_img[:5]))
if errors:
    print(f"\n■ エラー {len(errors)}件 — 直さないとアプリが正しく動きません")
    for e in errors:
        print("  -", e)
if warns:
    print(f"\n□ 警告 {len(warns)}件")
    for w in warns[:40]:
        print("  -", w)
    if len(warns) > 40:
        print(f"  ... 他 {len(warns)-40}件")
if not errors and not warns:
    print("\nデータの問題なし")
sys.exit(1 if errors else 0)
