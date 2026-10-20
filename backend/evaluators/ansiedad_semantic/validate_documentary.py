"""Independent field-by-field audit against DOCX XML (no contract reader imports)."""
from pathlib import Path
from zipfile import ZipFile
from hashlib import sha256
import xml.etree.ElementTree as ET
import json


def validate(source, directory):
    source, directory = Path(source), Path(directory)
    with ZipFile(source) as z:
        tree = ET.fromstring(z.read("word/document.xml"))
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    original = ["".join(n.text or "" for n in p.iter(ns+"t")) for p in tree.iter(ns+"p")]
    digest = sha256(source.read_bytes()).hexdigest()
    errors, seen, intervals = [], set(), []
    for path in sorted(directory.glob("*.json")):
        family = json.loads(path.read_text(encoding="utf-8"))
        if family["source_sha256"] != digest: errors.append(str(path)+": source identity")
        for c in family["contracts"]:
            code=c["code"]
            if code in seen: errors.append(code+": duplicate")
            seen.add(code)
            start,end=c["paragraph_start_zero_based"],c["paragraph_end_exclusive"]
            block=original[start:end]
            intervals.append((start,end))
            if block != c["paragraphs_literal"]: errors.append(code+": literal paragraphs")
            if not block or c["official_heading"] != block[0]: errors.append(code+": heading")
            if not c["official_heading"].startswith(code+" "): errors.append(code+": code")
            gates=[x for x in block if x.startswith(("General:","Condicional:","Aplicabilidad:"))]
            if gates != [c["applicability_literal"]]: errors.append(code+": gate")
            for level in range(4):
                markers=[i for i,x in enumerate(block) if x==str(level)]
                if len(markers)!=1 or block[markers[0]+1] != c["levels"][str(level)]: errors.append(code+": level "+str(level))
    intervals.sort()
    if any(a[1]!=b[0] for a,b in zip(intervals,intervals[1:])): errors.append("gaps/overlaps")
    for path in directory.glob("*.json"):
        family=json.loads(path.read_text(encoding="utf-8"))
        if family["preamble_literal"] != original[:intervals[0][0]]:errors.append(str(path)+": preamble")
    expected={f"{f}{i}" for f,n in {"AF":8,"GD":8,"PS":10,"PA":8,"ND":8,"CP":8,"IR":8,"EM":13,"CE":10}.items() for i in range(1,n+1)}
    if seen!=expected:errors.append("indicator identity coverage")
    if intervals[-1][1]!=len(original):errors.append("trailing content missing")
    return {"indicators":len(seen),"families":len(list(directory.glob("*.json"))),"source_sha256":digest,"errors":errors,"documentary_integrity":not errors,"clinical_validation":False}

if __name__ == "__main__":
    import sys
    result=validate(sys.argv[1],sys.argv[2])
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(bool(result["errors"]))
