"""Fetch primary-source PDFs unchanged; render relevant pages for visual review.

Read-only source acquisition. Whole source PDFs remain in raw runs, outside Git.
No existing CSV is read, and no numerical electronic calculation is performed.
"""
import argparse
import hashlib
import json
import time
import urllib.request
from pathlib import Path

SOURCES = [
    dict(name='pachucki_2010_v2', url='https://arxiv.org/pdf/1007.0322v2', pages=[2,11]),
    dict(name='sims_hagstrom_2006_published', url='https://www.nist.gov/system/files/documents/2017/05/09/sims-h2.pdf', pages=[0,3,4]),
    dict(name='sims_hagstrom_author_preprint', url='https://math.nist.gov/mcsd/savg/papers/h2.pdf', pages=[7,17])
]


def write(path, value):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2,allow_nan=False)
        stream.write('\n')


def acquire(directory):
    import pdfplumber
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=False)
    write(directory/'acquisition_plan.json',dict(sources=SOURCES,old_CSV_not_read=True,
          acquisition_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          evidence_scope='primary source retrieval and relevant page review, not blinded numerical validation'))
    records=[]
    for source in SOURCES:
        started=time.perf_counter()
        path=directory/(source['name']+'.pdf')
        try:
            request=urllib.request.Request(source['url'],headers={'User-Agent':'H2-reference-provenance-audit/1.0'})
            with urllib.request.urlopen(request,timeout=40) as response:
                data=response.read()
                final_url=response.geturl()
                headers=dict(response.headers.items())
            if not data.startswith(b'%PDF'):
                raise ValueError('response is not PDF')
            with path.open('xb') as stream:
                stream.write(data)
            with pdfplumber.open(path) as pdf:
                texts=[page.extract_text(layout=True) or '' for page in pdf.pages]
                with (directory/(source['name']+'.txt')).open('x',encoding='utf-8') as stream:
                    for index,text in enumerate(texts):
                        stream.write('\nPAGE '+str(index+1)+'\n'+text+'\n')
                rendered=[]
                for index in source['pages']:
                    name=source['name']+'_page_'+str(index+1)+'.png'
                    pdf.pages[index].to_image(resolution=140).save(directory/name)
                    rendered.append(name)
                records.append(dict(**source,status='ACQUIRED',final_url=final_url,headers=headers,
                     bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),page_count=len(texts),
                     rendered=rendered,seconds=time.perf_counter()-started))
            print('ACQUIRED',source['name'],len(data),'bytes',flush=True)
        except Exception as exc:
            records.append(dict(**source,status='ACQUISITION_ERROR_PRESERVED',error=repr(exc),seconds=time.perf_counter()-started))
            print('ACQUISITION ERROR',source['name'],repr(exc),flush=True)
        write(directory/(source['name']+'_acquisition.json'),records[-1])
    write(directory/'sources.json',dict(records=records,independent_author_groups=2,
         author_preprint_not_a_third_independent_reference=True,AO_calls=0,CI_calls=0))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True)
    args=parser.parse_args();acquire(args.directory)
