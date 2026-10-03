"""Write-once authoritative H basis acquisition; no AO or energy evaluation."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

BASES=['cc-pVDZ','cc-pVTZ','cc-pVQZ','cc-pV5Z']


def save(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,indent=2);stream.write('\n')


def acquire(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    urls={name:'https://www.basissetexchange.org/api/basis/'+name.lower()+'/format/json/?elements=1' for name in BASES}
    save(output/'plan.json',dict(urls=urls,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         physics_calls=0,old_basis_not_read=True))
    records=[]
    for name,url in urls.items():
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'H2-adversarial-audit/1.0'}),timeout=40) as response:
                data=response.read();final_url=response.geturl()
            parsed=json.loads(data)
            if set(parsed['elements'])!={'1'}: raise ValueError('unexpected elements')
            with (output/(name+'.json')).open('xb') as stream:stream.write(data)
            record=dict(name=name,url=url,final_url=final_url,status='ACQUIRED',bytes=len(data),
                        sha256=hashlib.sha256(data).hexdigest(),version=parsed['version'])
        except Exception as exc:
            record=dict(name=name,url=url,status='ACQUISITION_ERROR_PRESERVED',error=repr(exc))
        records.append(record);save(output/(name+'_provenance.json'),record)
        print(name,record['status'],record.get('version',record.get('error')),flush=True)
    save(output/'sources.json',dict(records=records,AO_calls=0,energy_calls=0))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args();acquire(args.output)
