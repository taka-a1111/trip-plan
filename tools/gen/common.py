"""make_<旅名>.py が共通で使う小さな部品（行・食事候補・費用の計算）。"""
import json
import re

A = lambda s: '<span class="amn">%s</span>' % s

PEACH_MANAGE = "https://manage.flypeach.com/jp/manage/retrieve-booking"
NGO = {"n": "中部国際空港", "lat": 34.8584, "lon": 136.8148, "k": "spot", "q": "中部国際空港 第1ターミナル", "official": "https://www.centrair.jp/"}


def mv(name, dur, plan=None, toll=None, note=None, badges=None):
    r = {"type": "move", "name": name, "dur": dur}
    if plan: r["plan"] = plan
    if toll: r["toll"] = toll
    if note:
        r["note"] = note
        r["keep_note"] = True
    if badges: r["badges"] = badges
    return r


def meal(name, q, bg, rv, hr, off, ft, la, lo, kind, br=None):
    d = {"name": name, "q": q, "bg": bg, "rv": rv, "hr": hr, "off": off, "ft": ft, "la": la, "lo": lo, "kind": kind}
    if br: d["br"] = br
    return d


def rain(n, q, la, lo, rv, fam, hr, off, note, official):
    return {"n": n, "q": q, "la": la, "lo": lo, "rv": rv, "fam": fam, "hr": hr, "off": off, "note": note, "official": official}


def flight(key, flno, dep, arr, t1, t2, plan, deadline, fee, note, intl=False):
    """飛行機のカード（未予約の候補）。"""
    f = [["航空会社", "Peach（ピーチ）"], ["便名", "%s　%s %s → %s %s" % (flno, dep, t1, arr, t2)],
         ["予約", "未予約。ピーチポイントで払う（搭乗者にポイントの名義人が入っていること）"],
         ["荷物", "機内持ち込みは1人7kgまで（2個）。預ける荷物は有料"],
         ["締切", deadline]]
    return {"type": "spot", "key": key, "cat": "move", "cat_lbl": "飛行機", "time": "%s → %s" % (t1, t2), "plan": plan,
            "badges": [["b-reserve", "未予約"]], "fee": fee, "note": note, "fields": f}


f = lambda n: format(n, ',')


def km_total(days, car_days=None):
    return sum(int(m.group(1).replace(',', '')) for dy in days if (car_days is None or dy['id'] in car_days)
               for r in dy['rows'] if r['type'] == 'move' for m in [re.search(r'約([\d,]+)km', r['name'])] if m)


def save(name, data):
    open('trips/%s.json' % name, 'w', encoding='utf-8').write(json.dumps(data, ensure_ascii=False, indent=1))


# セントレア4階の店（口コミ件数と営業時間は2026-10-29にGoogleマップで確認）
YABATON = meal("矢場とん 中部国際空港店", "矢場とん 中部国際空港店", "1,800円ほど", "★4.0・1,182件", "10:00–21:00", "無休", "名古屋のみそかつ。出発前の4階", 34.8585151, 136.8148075, "ご当地", "矢場とん")
MARUHA = meal("まるは食堂 中部国際空港店", "まるは食堂 中部国際空港店", "2,000円ほど", "★3.9・684件", "10:00–21:00", "無休", "大きなエビフライ。展望デッキの近く", 34.85925, 136.8137361, "海鮮")


def ngo_lunch(plan, note, label="昼"):
    """出発前にセントレアで食べる行（label は 昼 か 夕飯）。"""
    return {"type": "spot", "key": "ngo", "cat": "food", "cat_lbl": "グルメ", "time": "店ごとに異なる", "plan": plan,
            "badges": [["b-open", label]], "note": note,
            "fields": [["営業", "矢場とん・まるは食堂 10:00–21:00"], ["定休", "なし"]]}


PACK_COMMON = [
 {"t": "貴重品・書類", "c": "var(--gold)", "items": [["cash", "現金・クレジットカード"], ["insurance", "健康保険証・母子手帳"], ["resv", "予約の控え（ピーチ・宿）"]]},
 {"t": "電子機器", "c": "var(--slate)", "items": [["phone", "スマホ・充電ケーブル"], ["power", "モバイルバッテリー"], ["camera", "カメラ"]]},
 {"t": "衣類・洗面", "c": "var(--coral)", "items": [["clothes", "着替え（1泊ぶん）"], ["under", "下着・靴下"], ["tooth", "歯ブラシ・歯みがき"], ["med", "常備薬・絆創膏"], ["wipe", "ウェットティッシュ"]]},
 {"t": "子ども・移動", "c": "var(--gold)", "items": [["snack", "おやつ・飲み物"], ["sick", "酔い止め"], ["play", "飛行機と電車の暇つぶし"]]},
]


PEACH_POINTS = 100000  # 持っているピーチポイント（円）


def cost_with_points(items, total, air, note="", sub="食費とおみやげは含みません（変動するため）"):
    """費用欄を作る。航空券はピーチポイントを全部使って払うので、合計に入れない（items の航空券の行は参考として残す）。"""
    items = [(["航空券", "（%s）" % it[1], "合計に入れない。ピーチポイント%s円を全部使って払う。%s" % (f(PEACH_POINTS), it[2])] if it[0] == "航空券" else it) for it in items]
    return {"items": items, "total": "約%s円" % f(total - air),
            "total_sub": "航空券を除いた、現金で払う額。%s" % sub,
            "note": note}
