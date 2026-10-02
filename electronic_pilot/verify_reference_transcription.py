"""Check the manually transcribed numeric dataset against the archived PDF.

Requires pypdf only for source acquisition; never imported by the executor.
"""
import csv
import hashlib
import json
import re
import sys
from decimal import Decimal
from pathlib import Path
from pypdf import PdfReader


def main():
    pdf = Path(sys.argv[1])
    text = PdfReader(pdf).pages[11].extract_text()
    text = re.sub(r"\s*\.\s*", ".", text)
    # pypdf produces groups of 3 digits; layout is also checked visually.
    pattern = r"(?<!\d)(\d+\.\d{2})\s+([−-]?\d\.\d{3}(?:\s+\d{3})+\s*\d{0,2})(?:\((\d+)\))?"
    extracted = {}
    for r,e,u in re.findall(pattern,text):
        e = e.replace("−","-").replace(" ","").replace("\n","")
        extracted[Decimal(r)] = (Decimal(e),u)
    with Path(sys.argv[2]).open(newline="",encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    problems=[]
    for row in rows:
        r=Decimal(row["R_bohr"])
        if r not in extracted or extracted[r][0] != Decimal(row["total_energy_hartree"]):
            problems.append(dict(R=str(r),csv=row["total_energy_hartree"],pdf=str(extracted.get(r))))
        elif row["published_uncertainty_hartree"]:
            value, u=extracted[r]
            if not u or Decimal(u)*Decimal(10)**value.as_tuple().exponent != Decimal(row["published_uncertainty_hartree"]):
                problems.append(dict(R=str(r),error="uncertainty mismatch"))
    result=dict(pdf_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),
                checked_rows=len(rows),extracted_rows=len(extracted),problems=problems,
                source="https://arxiv.org/pdf/1007.0322v2",pdf_page_1based=12,
                uncertainty_note="No parenthesized uncertainty printed for R=16,20; not treated as zero")
    Path(sys.argv[3]).write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))
    if problems:
        raise SystemExit(1)


if __name__=="__main__":
    main()
