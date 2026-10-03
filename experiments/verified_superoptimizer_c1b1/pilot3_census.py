"""Fraction call-site census with temporary original-operation wrappers.

The SQLite table stores exact observed values for counting, never runtime answers.
Profile timing excludes the callback itself; it is not an uninstrumented benchmark.
"""
from __future__ import annotations
from collections import Counter
from fractions import Fraction as Q
import argparse
import fractions
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import sys
import time
import threading

from . import evidence as E

ROOT = Path(__file__).resolve().parents[2]
FRACTIONS_FILE = Q.__new__.__code__.co_filename
CREATORS = {'__new__': 'new', '_from_coprime_ints': 'coprime'}


def integer_bytes(v):
    return v.to_bytes(max(1, (v.bit_length()+8)//8), 'big', signed=True)


class Census:
    def __init__(self, database):
        database = Path(database)
        if database.exists():
            raise FileExistsError(database)
        self.db = sqlite3.connect(database)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('CREATE TABLE vals(site INTEGER, n BLOB, d BLOB, count INTEGER, PRIMARY KEY(site,n,d)) WITHOUT ROWID')
        self.sites = {}
        self.rows = []
        self.values = Counter()
        self.stack = []
        self.overhead_ns = 0
        self.step_cpu_ns = 0
        self.active = False
        self.site_keys = {}

    def site(self, frame):
        caller = frame.f_back
        while caller is not None and caller.f_code.co_filename in (FRACTIONS_FILE, __file__):
            caller = caller.f_back
        if caller is None:
            key = ('<unknown>', '<unknown>', 0)
        else:
            address=(caller.f_code,caller.f_lineno)
            if address in self.site_keys:
                return self.site_keys[address]
            file = Path(caller.f_code.co_filename)
            try:
                file = file.relative_to(ROOT).as_posix()
            except ValueError:
                file = str(file)
            key = (file, caller.f_code.co_name, caller.f_lineno)
        if key not in self.sites:
            self.sites[key] = len(self.rows)
            self.rows.append(dict(file=key[0], function=key[1], line=key[2], new=0,
                coprime=0, mul=0, forward=0, gcd=0, exclusive_ns=0,
                n_bits_min=None, n_bits_max=0, d_bits_min=None, d_bits_max=0,
                n_bits_sum=0, d_bits_sum=0, denominator_shapes=Counter(),
                fraction_functions=Counter()))
        result=self.sites[key]
        if caller is not None:
            self.site_keys[address]=result
        return result

    def wrapped(self,fn,name):
        def observe(*args,**kwargs):
            begin=time.thread_time_ns()
            site=self.site(sys._getframe())
            row=self.rows[site]
            record=[site,0,0]
            self.stack.append(record)
            row['fraction_functions'][name]+=1
            if name=='_mul':row['mul']+=1
            if name=='forward' or (name=='_mul' and fn.__code__.co_name=='forward'):row['forward']+=1
            if name=='gcd':
                row['gcd']+=1
                operand_bits=[abs(v).bit_length() for v in args if type(v) is int]
                row['gcd_operand_bits_max']=max(row.get('gcd_operand_bits_max',0),*operand_bits)
            start=time.thread_time_ns()
            try:
                value=fn(*args,**kwargs)
            except BaseException:
                finish=time.thread_time_ns()
                self._finish_wrapper(record,begin,start,finish)
                raise
            finish=time.thread_time_ns()
            if name in CREATORS and type(value) is Q:
                row[CREATORS[name]]+=1
                self._value(site,value)
            self._finish_wrapper(record,begin,start,finish)
            return value
        return observe

    def _finish_wrapper(self,record,begin,start,finish):
        assert self.stack[-1] is record
        function_cpu=finish-start-record[2]
        exclusive=function_cpu-record[1]
        assert exclusive>=0,'negative wrapper CPU attribution'
        self.rows[record[0]]['exclusive_ns']+=exclusive
        self.stack.pop()
        overhead=time.thread_time_ns()-begin-function_cpu
        if self.stack:
            self.stack[-1][1]+=function_cpu
            self.stack[-1][2]+=overhead
        else:
            self.overhead_ns+=overhead

    def _value(self, site, result):
        if type(result) is not Q:
            return
        n, d = result.numerator, result.denominator
        row = self.rows[site]
        nb, db = abs(n).bit_length(), d.bit_length()
        for field, bits in [('n', nb), ('d', db)]:
            low = row[field+'_bits_min']
            row[field+'_bits_min'] = bits if low is None else min(low, bits)
            row[field+'_bits_max'] = max(row[field+'_bits_max'], bits)
            row[field+'_bits_sum'] += bits
        row['denominator_shapes']['power_of_two' if d & (d-1) == 0 else 'general'] += 1
        self.values[site, integer_bytes(n), integer_bytes(d)] += 1
        if len(self.values) >= 32768:
            self.flush()

    def flush(self):
        self.db.executemany('INSERT INTO vals VALUES(?,?,?,?) ON CONFLICT(site,n,d) DO UPDATE SET count=count+excluded.count',
            [(s,n,d,c) for (s,n,d),c in self.values.items()])
        self.db.commit()
        self.values.clear()

    def __enter__(self):
        if sys.getprofile() is not None or self.active:
            raise RuntimeError('census requires no existing profile hook')
        if threading.active_count()!=1:
            raise RuntimeError('temporary Fraction wrappers require a single-thread process')
        self.active = True
        self.descriptors={}
        for name in ('__new__','_from_coprime_ints','__mul__','__rmul__',
                     '__add__','__radd__','__sub__','__rsub__','__truediv__','__rtruediv__'):
            original=Q.__dict__[name]
            self.descriptors[name]=original
            if name=='__new__':replacement=staticmethod(self.wrapped(Q.__new__,'__new__'))
            elif name=='_from_coprime_ints':replacement=classmethod(self.wrapped(original.__func__,'_from_coprime_ints'))
            else:
                kind='_mul' if name in ('__mul__','__rmul__') else original.__code__.co_name
                replacement=self.wrapped(original,kind)
            setattr(Q,name,replacement)
        self.original_gcd=math.gcd
        math.gcd=self.wrapped(math.gcd,'gcd')
        self.begin_ns = time.thread_time_ns()
        self.begin_overhead = self.overhead_ns
        return self

    def __exit__(self, *exc):
        self.step_cpu_ns += time.thread_time_ns()-self.begin_ns-(self.overhead_ns-self.begin_overhead)
        math.gcd=self.original_gcd
        for name,descriptor in self.descriptors.items():setattr(Q,name,descriptor)
        self.active = False
        assert not self.stack

    def summary(self):
        self.flush()
        out = []
        for i, original in enumerate(self.rows):
            row = dict(original)
            distinct, total = self.db.execute('SELECT count(*),coalesce(sum(count),0) FROM vals WHERE site=?',(i,)).fetchone()
            assert total == row['new']+row['coprime']
            denoms = self.db.execute('SELECT count(*) FROM (SELECT DISTINCT d FROM vals WHERE site=?)',(i,)).fetchone()[0]
            row.update(distinct_values=distinct,repeat_creations=total-distinct,
                repeat_percent=100*(total-distinct)/total if total else None,
                distinct_denominators=denoms,exclusive_cpu_seconds=row.pop('exclusive_ns')/1e9,
                observed_creation_count=total)
            row['whole_step_cpu_percent']=100*row['exclusive_cpu_seconds']/(self.step_cpu_ns/1e9) if self.step_cpu_ns else 0
            row['common_values']=[dict(n=int.from_bytes(n,'big',signed=True),d=int.from_bytes(d,'big',signed=True),count=k)
                for n,d,k in self.db.execute('SELECT n,d,count FROM vals WHERE site=? ORDER BY count DESC LIMIT 8',(i,))]
            out.append(row)
        return dict(sites=out,step_cpu_seconds=self.step_cpu_ns/1e9,
            callback_cpu_seconds=self.overhead_ns/1e9,counts={k:sum(r[k] for r in out) for k in ['new','coprime','mul','forward','gcd']},
            timing_scope='original-operation wrapper CPU excluding nested observed operations and measured wrapper bookkeeping; unwrapped Fraction accessors/dispatch remain within original operation; not an uninstrumented benchmark')


def campaign(out):
    from a_reference import c1b1_runtime as R
    from . import combined_promotion as P, integration_stages as I
    out.mkdir(parents=True,exist_ok=False)
    protocol=json.loads((ROOT/'runs/c1b1_pilot3_v1/observation_protocol_v2.json').read_bytes())
    source=E.inventory()
    E.write(out/'manifest.json',dict(schema='pilot3-baseline-census-v1',source=source,
        source_hash=E.digest(source),protocol=protocol,protocol_hash=E.digest(protocol),
        stdlib_fraction_sha256=E.sha(FRACTIONS_FILE),python=sys.version))
    c=Census(out/'values.sqlite')
    rows=[]
    for item in protocol['cases']:
        run=P.make_run(item['spec']);ex=R.bind(run,mode='fast_combined')
        h=hashlib.sha256()
        for _ in range(item['steps']):
            with c:
                ex.step()
            h.update(E.canonical(P.plain(I.raw(run))))
        final=E.digest(P.plain(I.raw(run)))
        # Prior campaign uses its canonical writer (ensure_ascii=False).
        assert P.digest(P.plain(I.raw(run)))==item['prior_final_sha256'],item['spec']['id']
        row=dict(id=item['spec']['id'],steps=run.t_steps,final_hash=final,all_state_hash=h.hexdigest())
        rows.append(row)
        E.write(out/(row['id']+'.json'),row)
        print(json.dumps(row),flush=True)
    assert E.inventory()==source,'source changed during baseline census'
    result=c.summary();result.update(trajectories=rows,source_hash=E.digest(source),protocol_hash=E.digest(protocol))
    E.write(out/'census.json',result)
    c.db.close()
    E.write(out/'closure.json',dict(status='PASS',source_hash=E.digest(source),
        outputs={p.name:E.sha(p) for p in out.iterdir() if p.is_file() and p.name!='closure.json'}))
    print(json.dumps(result['counts']),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True)
    campaign(Path(parser.parse_args().out))
