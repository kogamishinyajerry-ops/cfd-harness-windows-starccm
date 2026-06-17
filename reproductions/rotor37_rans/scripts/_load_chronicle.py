# -*- coding: utf-8 -*-
"""Extract the chronicle object from the agent-workflow output file and write
chronicle.json for gen_html_report.py to consume."""
import json, os

SRC = r"C:\Users\Kogami\AppData\Local\Temp\claude\C--Users-Kogami\7dab487a-8272-405a-87db-43e53e71d5aa\tasks\w137bibp9.output"
DST = r"D:\CFD-harness-Windows-StarCCM\reproductions\rotor37_rans\chronicle.json"

with open(SRC, encoding="utf-8") as f:
    data = json.load(f)

chron = data.get("result", {}).get("chronicle") or data.get("chronicle") or data
n_cast = len(chron.get("cast", []))

# consistency: intro said "八个特工" but roster has 9 (8 specialists + director)
intro = chron.get("intro", "")
intro = intro.replace("八个特工各有绝活", "八位特工各有绝活，再加上一位幕后统筹的总指挥")
chron["intro"] = intro

with open(DST, "w", encoding="utf-8") as f:
    json.dump({"chronicle": chron}, f, ensure_ascii=False, indent=2)

print("wrote", DST)
print("cast:", n_cast, "| acts:", len(chron.get("acts", [])),
      "| quotes:", len(chron.get("pull_quotes", [])))
