"""Narrow primary-page crops and second transcription-path checks.

Full PDFs/text/pages stay in raw runs. Crops show only the relevant row,
equation or uncertainty discussion, with source-page hashes and coordinates.
"""
import argparse
import re
from pathlib import Path
from .audit import read, write, sha

CROPS = [
    ('pachucki_2010_v2', 12, 'pachucki_R04_row', [65, 70, 550, 190]),
    ('pachucki_2010_v2', 3, 'pachucki_Hamiltonian', [65, 270, 560, 415]),
    ('sims_hagstrom_2006_published', 5, 'sims_R04_row', [42, 40, 302, 124]),
    ('sims_hagstrom_2006_published', 4, 'sims_uncertainty_scope', [310, 336, 570, 477])
]


def review(acquisition):
    import pdfplumber
    acquisition=Path(acquisition)
    plan=acquisition/'supplemental_review_plan.json'
    write(plan,dict(crops=CROPS,preprint_extra_pages=[9,10],purpose='source review only; not independent numerical computation'))
    crops=[]
    for name,page,label,box in CROPS:
        source=acquisition/(name+'.pdf')
        with pdfplumber.open(source) as pdf:
            target=acquisition/(label+'.png')
            if target.exists():
                raise ValueError('write-once crop already exists')
            pdf.pages[page-1].crop(box).to_image(resolution=180).save(target)
        crops.append(dict(name=target.name,sha256=sha(target),pdf=source.name,
                          pdf_sha256=sha(source),page_one_based=page,box_pdf_points=box))
    with pdfplumber.open(acquisition/'sims_hagstrom_author_preprint.pdf') as pdf:
        for page in (9,10):
            target=acquisition/f'sims_hagstrom_author_preprint_page_{page}.png'
            pdf.pages[page-1].to_image(resolution=140).save(target)
    rows={}
    for name,page in [('pachucki_2010_v2',12),('sims_hagstrom_2006_published',5),('sims_hagstrom_author_preprint',10)]:
        with pdfplumber.open(acquisition/(name+'.pdf')) as pdf:
            lines=(pdf.pages[page-1].extract_text() or '').splitlines()
        matches=[line for line in lines if re.match(r'\s*0\.4(?:0)?\s',line)]
        if len(matches)!=1:
            raise ValueError('R04 text row not unique '+name+repr(matches))
        rows[name]=dict(page_one_based=page,extracted_row=matches[0],
                        compact_row=re.sub(r'\s+','',matches[0]).replace('−','-'))
    if '-0.120230341178823(15)' not in rows['pachucki_2010_v2']['compact_row']:
        raise ValueError('primary Pachucki row text/image transcription disagreement')
    if '-0.1202303411778644' not in rows['sims_hagstrom_2006_published']['compact_row']:
        raise ValueError('primary Sims row text/image transcription disagreement')
    write(acquisition/'review_paths.json',dict(crops=crops,extracted_rows=rows,
          acquisition_source_sha256=sha(acquisition/'acquisition_plan.json'),
          reviewer='implementing agent; relevant primary pages visually reviewed',
          independence='Two transcription mechanisms of the same documents; two calculation lineages total, not three'))
    print('SOURCE REVIEW',len(crops),'crops, 3 row extractions; no AO/CI calls',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--acquisition',required=True)
    args=parser.parse_args();review(args.acquisition)
