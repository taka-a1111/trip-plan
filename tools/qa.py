# -*- coding: utf-8 -*-
"""しおりQA:  python3 tools/qa.py kiso.html [index.html ...]
1000/430/380px で開き、横スクロール・Leaflet地図数・JSエラーを確認し、
tools/qa_out/ にスクリーンショットを保存する。"""
import asyncio
import os
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "tools", "qa_out")


async def check(files):
    os.makedirs(OUT, exist_ok=True)
    ok = True
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for f in files:
            path = os.path.join(ROOT, f)
            for w in (1000, 430, 380):
                pg = await b.new_page(viewport={"width": w, "height": 900})
                errs = []
                pg.on("pageerror", lambda e: errs.append(str(e)))
                await pg.goto("file://" + path)
                await pg.wait_for_timeout(2500)
                await pg.evaluate("document.querySelectorAll('.reveal').forEach(e=>e.classList.add('visible'))")
                ov = await pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                maps = await pg.evaluate("document.querySelectorAll('.leaflet-container').length")
                name = os.path.basename(f).replace(".html", "")
                await pg.screenshot(path=os.path.join(OUT, "%s_%d.png" % (name, w)))
                status = "OK" if ov == 0 and not errs else "NG"
                if status == "NG":
                    ok = False
                print("%s %spx overflow=%d maps=%d errors=%s -> %s" % (f, w, ov, maps, errs, status))
                await pg.close()
        await b.close()
    return ok


if __name__ == "__main__":
    files = sys.argv[1:] or ["kiso.html", "index.html"]
    sys.exit(0 if asyncio.run(check(files)) else 1)
