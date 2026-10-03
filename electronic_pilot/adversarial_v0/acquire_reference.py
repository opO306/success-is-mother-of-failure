"""Acquire discovered primary-source URLs, preserving refusals separately."""
from pathlib import Path
import urllib.request,datetime
from electronic_pilot.frontend_reference_v0.audit import write,sha

URLS={
 'h2solv':'https://users.fuw.edu.pl/~krp/papers/h2solv.pdf',
 'FC_LSE_2018':'https://www.qcri.or.jp/lab/wp-content/uploads/2018/12/J.Chem.Phys._149_244116_2018.pdf',
 'FC_variational_landing':'https://pubs.rsc.org/en/content/articlelanding/2019/cp/c8cp05949g',
 'Ndeke_landing':'https://edoc.hu-berlin.de/handle/18452/30005',
 'qcri_publications':'https://www.qcri.or.jp/en/publications/'}

def main():
    dest=Path('runs/h2_adversarial_v0/reference_acquisition_v0');dest.mkdir(parents=True,exist_ok=False)
    write(dest/'plan.json',dict(source_sha256=sha(__file__),urls=URLS,not_all_sources_independent=True))
    rows=[]
    for name,url in URLS.items():
        row=dict(name=name,requested_url=url,time_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat())
        try:
            request=urllib.request.Request(url,headers={'User-Agent':'H2-numerical-audit/0.1'})
            with urllib.request.urlopen(request,timeout=25) as response:
                data=response.read();row.update(final_url=response.url,status=response.status,content_type=response.headers.get('Content-Type'))
            ext='.pdf' if data.startswith(b'%PDF') else '.html';path=dest/(name+ext);path.write_bytes(data)
            row.update(file=str(path),sha256=sha(path),bytes=len(data),acquired=True)
        except Exception as exc:row.update(acquired=False,error=repr(exc))
        rows.append(row);write(dest/'sources.json',rows);print('REFERENCE ACQUIRE',name,row['acquired'],flush=True)

if __name__=='__main__':main()
