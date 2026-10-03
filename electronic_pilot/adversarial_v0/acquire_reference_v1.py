"""Preserved V0 acquisition stopped on exclusive-write I/O; append-safe V1."""
from pathlib import Path
import urllib.request,datetime
from electronic_pilot.frontend_reference_v0.audit import write,sha
from .acquire_reference import URLS

def main():
    dest=Path('runs/h2_adversarial_v0/reference_acquisition_v1');dest.mkdir(parents=True,exist_ok=False)
    write(dest/'plan.json',dict(source_sha256=sha(__file__),urls=URLS,prior_failure_preserved=True))
    rows=[]
    for name,url in URLS.items():
        row=dict(name=name,requested_url=url,time_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat())
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'H2-numerical-audit/0.1'}),timeout=25) as response:
                data=response.read();row.update(final_url=response.url,status=response.status,content_type=response.headers.get('Content-Type'))
            path=dest/(name+('.pdf' if data.startswith(b'%PDF') else '.html'));path.write_bytes(data)
            row.update(file=str(path),sha256=sha(path),bytes=len(data),acquired=True)
        except Exception as exc:row.update(acquired=False,error=repr(exc))
        rows.append(row);write(dest/(name+'_acquisition.json'),row);print('REFERENCE ACQUIRE',name,row['acquired'],flush=True)
    write(dest/'sources.json',rows)

if __name__=='__main__':main()
