"""Post-acquisition packaging only. Sealed numerical checker remains unchanged."""
from copy import deepcopy
import datetime
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
from .checker import CASES,DOC,RAW,decimal,dyadic,sha,write
from .run import verify

def val(p,d=10):return decimal(dyadic(int(p[0]),p[1]),d) if p else 'UNAVAILABLE'
def small(x,d=9):
    from mpmath import mp
    with mp.workdps(260):return mp.nstr(mp.mpf(x),d) if x is not None else 'UNAVAILABLE'

def compact(r):
    r=deepcopy(r)
    path=RAW/'cases'/r['name']/'result.json'
    r['full_result_path']=path.as_posix();r['full_result_sha256']=sha(path)
    def factor_meta(f):
        f=deepcopy(f);p=f.pop('pivots');f['pivot_count']=len(p)
        f['minimum_resolved_positive_lower']=min((dyadic(int(x['lower_pair'][0]),x['lower_pair'][1])
            for x in p if x['sign']==1),default=None)
        if f['minimum_resolved_positive_lower'] is not None:f['minimum_resolved_positive_lower']=decimal(f['minimum_resolved_positive_lower'],25)
        f['last_pivot']=p[-1] if p else None
        f.pop('direction_pairs')
        return f
    def ladder_meta(l):
        return dict(matrix_sha256=l['matrix_sha256'],attempts=[dict(decimal_digits=a['decimal_digits'],bits=a['bits'],
            result=factor_meta(a['result'])) for a in l['attempts']],final=factor_meta(l['final']))
    r['SPD']=ladder_meta(r['SPD']);r['fault_indefinite']['result']=ladder_meta(r['fault_indefinite']['result'])
    if r['initial_inertia']:r['initial_inertia']=ladder_meta(r['initial_inertia'])
    for trace in r['root'].get('trace',[]):trace['ladder']=ladder_meta(trace['ladder'])
    return r

def package():
    path=DOC/'evidence/table.json';original=json.loads(path.read_text())
    if original.get('compact_metadata'):raise ValueError('already packaged; never repeat acquisition')
    write(RAW/'table.full.json',original)
    rows=original['cases'];table=deepcopy(original);table['compact_metadata']=True
    table['cases']=[compact(r) for r in rows]
    table['full_table_path']=(RAW/'table.full.json').as_posix();table['full_table_sha256']=sha(RAW/'table.full.json')
    write(path,table)
    for r in table['cases']:write(DOC/'evidence/cases'/r['name']/'result.json',r)
    proto=json.loads((DOC/'evidence/protocol.json').read_text());verify(proto['protected_sha256']);verify(proto['implementation_sha256'])
    write(DOC/'evidence/protected_after.json',dict(files=len(proto['protected_sha256']),unchanged=True,
        verification='current rehash of all protected paths, not inference from commit status'))
    entries=[dict(path=p.as_posix(),sha256=sha(p),bytes=p.stat().st_size) for p in RAW.rglob('*') if p.is_file()]
    write(DOC/'evidence/raw_inventory.json',dict(grade='LOCAL_BYTE_PROVENANCE_NOT_EXTERNAL_AUDIT',entries=entries))
    for name in ('execution.log','execution.stderr'):
        (DOC/'evidence'/name).write_bytes((RAW/name).read_bytes())
    write(DOC/'evidence/git_entry.json',dict(source='live git tool check before first edit; reconfirmed in git_start.json after new untracked analysis creation',
        HEAD='ab3569b29f436df28a49369c0f126af719d26294',branch='codex/h2-representation-pilot1',dirty=False,untracked=[],
        origin_master='0f7b744cf754450424a63c47f305e0327c5b37c1',origin_Pilot='264f5880ee1dedd5a97b008c29dd8d67057664b9',ahead=3,behind=0,
        fetch=False,push=False,merge=False,rebase=False))
    print('Packaged exact raw proof objects with compact Git metadata. '+str(len(entries))+' raw entries.')

def report():
    t=json.loads((DOC/'evidence/table.json').read_text());rows=[json.loads(Path(r['full_result_path']).read_text()) for r in t['cases']]
    proto=json.loads((DOC/'evidence/protocol.json').read_text());v=json.loads((DOC/'evidence/verification.json').read_text())
    labels=['H–He⁺','JC symmetric','H₂ symmetric','JC asymmetric','General']
    text=['# H2SOLV Stored-Matrix Lowest-Root Audit V1','',
        '**H2SOLV_LOWEST_ROOT_UNRESOLVED / STOP / NOT_CERTIFIED / NOT_PRODUCTION_APPROVED.**',
        '이번5개 전체의 lowest-root 승격은 실패했다. 수렴 분기 통과와 최저 고유값은 다른 조건이다.',
        '아래 결과는 실제 저장 H/S의 finite numerical pencil에 한정하며 원래 물리 적분이나 NMAX 정확성의 판정이 아니다.','',
        '## GIT STATE','',
        '작업 시작 HEAD `ab3569b29f436df28a49369c0f126af719d26294`, branch `codex/h2-representation-pilot1`.',
        '수정 전 dirty/untracked0. live origin/master `0f7b744cf754450424a63c47f305e0327c5b37c1`,',
        'origin/Pilot `264f5880ee1dedd5a97b008c29dd8d67057664b9`; ahead3/behind0. local commit 후4/0.',
        'Git entry와 prepare 이후 새 분석 untracked 상태는 [git_entry](evidence/git_entry.json)·[git_start](evidence/git_start.json).',
        'fetch/merge/rebase/push 없음. 마지막 commit hash·postcommit clean 상태는 완료 응답과 Git history를 참조한다.','',
        '## INPUT / MATRIX PROVENANCE','',
        '이전 AUDIT의 `invsg` 직전 H/S 및 반환 직후 E/v를 그대로 읽었다. 추가 계측판·vendor 재실행0.',
        '원본 archive/source/VENDOR/AUDIT binaries 및 과거 봉인 파일 **660개 binding 전후 hash 일치**.',
        '[입력 전체 해시·metadata·actual EN/WA1](evidence/protocol.json), [전후 검증](evidence/protected_after.json).',
        'H/S320 bits, 반환 E/v384 bits. int64 little endian9word dyadic record, lower triangle row order.',
        'Mirror는 저장 형식 복원이다. 평균 대칭화, rank cutoff, diagonal shift, 원래 행렬 수정 없음.',
        'S symmetry는 복원된 저장 행렬에 대해 정확하다. 독립 upper triangle이 없어 원래 generator의 양쪽 계산 비교는 불가능하다.',
        '대형 H/S/E/v·정확 pivot endpoint·proof 방향·intermediate factor inputs는 Git 밖 runs에 보존했다.',
        'Git의 compact metadata는 원본 proof object 경로/hash를 포함한다. [새 raw inventory](evidence/raw_inventory.json).','',
        '## INDEPENDENT CHECKER CONTRACT','',
        '[실행 전 PLAN](PLAN.md). 독립 parser + 새 C++ interval unpivoted LDL^T + 별도 Python exact qform.',
        'H2SOLV invsg/leq1s/avms/WA1 numerical code·이전 parser/residual evaluator import/reuse0.',
        '기존 MPFR4.2.1/GMP6.3.0을 이용했고 새 수치 library 설치0. g++ -O2, 단일 native process.',
        'MPFR RNDD/RNDU 연산의 inclusion property와 Sylvester congruence가 신뢰 기반이다.',
        '입력도 양 끝으로 반올림한다. 낮은 precision의 중간값만으로 원래320bit 값을 교체하지 않는다.',
        '부호가 확정되지 않는 pivot은 UNCERTAIN, 다음 사전 rung, 마지막까지 닫히지 않으면 STOP.',
        '이 checker는 pivot 교체/2×2 pivot을 구현하지 않아 비특이 [[0,1],[1,0]]도 거부한다.',
        '따라서 UNCERTAIN은 특이성 증명이 아니다. 코드 자체의 machine/formal proof 또는 외부기관 감사도 아니다.',
        '전체5개를 기록하기 위해 각 case의 S 실패는 그 case의 후속 root/rho를 막고 다른 승인 case 검사를 완료했다.',
        'aggregate 실패 후 승인 범위를 확대하지 않았다. 이 처리 순서는 실행 전에 명시·봉인됐다.',
        'protocol SHA256 `'+sha(DOC/'evidence/protocol.json')+'`.','',
        '## S SPD / interval sign / smallest-direction margin','',
        '사전 ladder80/120/160/240 decimal →266/399/532/798 bits. first resolved rung에서 종료.',
        '각 pivot의 exact dyadic interval endpoint는 raw proof에 있다. negative witness의 x^TSx는 정수로 정확히 재계산했다.',
        'min pivot은 최소 고유값이 아니다. SPD 전역 하한과 Schur 방향의 RQ 상한을 별도로 제시한다.',
        '', '| case | size | ladder result | resolved prefix min positive lower 또는 negative upper | lambda_min global lower | exact direction RQ | rank |',
        '|---|---:|---|---:|---:|---:|---|']
    for lab,r in zip(labels,rows):
        f=r['SPD']['final'];p=f['pivots']
        margin=min((dyadic(int(x['lower_pair'][0]),x['lower_pair'][1]) for x in p if x['sign']==1),default=None)
        if f['status']=='NOT_SPD':margin=dyadic(int(p[-1]['upper_pair'][0]),p[-1]['upper_pair'][1])
        ladder=' → '.join(str(a['decimal_digits'])+':'+a['result']['status'] for a in r['SPD']['attempts'])
        text.append(f"| {lab} | {r['dimension']} | {ladder} | {decimal(margin,10) if margin is not None else 'UNRESOLVED'} | {val(f['lambda_min_lower_pair'])} | {small(r['exact_direction']['direction_RQ']) if r['exact_direction'] else 'UNRESOLVED'} | {r['rank'] or 'UNRESOLVED'} |")
    text+=['','`STORED_S_SPD_CERTIFIED`는 모든 interval pivot이 양수로 닫힌 저장 S에만 쓴다.',
        'H–He⁺는112번째 pivot에서 음의 부호가 닫혔고 exact 방향의 RQ는 약−1.042163689e−20이다.',
        'General은80/120/160/240자리에서 각각290/422/541/791번째 pivot이 UNCERTAIN이었다.',
        '최종791번째 pivot interval은 약[−4.997706286e−20, +2.490439498e−19]로0을 포함한다.',
        '790개 leading positive pivot은 확인했지만 남은2개 및 full rank/SPD는 미확정이다.',
        '방향 RQ는 lambda_min의 상한이지 lambda_min 실측값이 아니다. 전역 lower는 매우 보수적이라 condition estimate로 쓰지 않는다.',
        'H–He⁺는 음의 방향을 정확히 확인했으나 전체 rank/inertia를 확정하지 않았다. General은 음의 방향 여부도 미확정이다.',
        'SPD 위반 원인이 NMAX/recurrence/양자화/저장 전 생성 중 어디인지는 이번 검사로 분리되지 않는다.','',
        '## WA(1) AUDIT','',
        'source h2solv.f:2553 shift H-EN*S,2560–2561 양 행렬 diagonal congruence scaling, EPSKOR=0.',
        'leq1s:2877 음의1×1,2908 indefinite2×2의 음의1개,2967 마지막 음의 pivot 집계;',
        'invsg:2621 `wa(1)=wa(ndet+n)`. S>0이고 factorization이 정확할 때만 초기 EN 아래 root 수다.',
        'actual initial_EN은 REAL*16→문자열→MPFR로 입력된 native dyadic이며 input literal과 정확히 같다고 가정하지 않았다.',
        '비교에는 actual EN을 사용했고 전체180자리 값/정확 pair는 protocol에 있다.',
        '', '| case | actual initial EN (간략 표시) | independent negative | observed WA1 | 판정 |',
        '|---|---:|---:|---:|---|']
    for lab,r in zip(labels,rows):
        ii=r['initial_inertia'];count=ii['final']['negative'] if ii and ii['final']['status']=='COMPLETE' else 'NOT_EXECUTED'
        text.append(f"| {lab} | {small(r['initial_EN'],35)} | {count} | {r['WA1']} | {r['WA1_status']} |")
    text+=['','전체 WA1 등급: **'+t['WA1_classification']+'**. 미실행을 일치 또는 불일치로 세지 않았다.',
        'WA1 일치가 반환 E의 lowest identity를 보장하지 않는다. root endpoint count는 별도 계산이다.','',
        '## LOWEST ROOT ENCLOSURE / 각5개','',
        '반환 E±2^-64에서 시작, count0/1일 때만 bisection8회 또는 width<=2^-70.',
        'reference를 읽거나 결과를 보고 구간 폭·precision을 바꾸지 않았다.',
        '표의 decimal은 표시용 반올림이다. exact endpoint dyadic pair는 case metadata에 보존했다.',
        '', '| case | E_returned (간략) | sigma_low | count_low | sigma_high | count_high | width | 판정 |',
        '|---|---:|---:|---:|---:|---:|---:|---|']
    for lab,r in zip(labels,rows):
        a=r['root'];lc=a.get('inertia_low');hc=a.get('inertia_high')
        text.append(f"| {lab} | {small(r['residual']['E_returned'],32)} | {a.get('low') or 'NOT_EXECUTED'} | {lc if lc is not None else 'NOT_EXECUTED'} | {a.get('high') or 'NOT_EXECUTED'} | {hc if hc is not None else 'NOT_EXECUTED'} | {small(a.get('width'))} | {a['status']} |")
    text+=['','전 endpoint 및 bisection은 resolved final interval inertia로 판정했다. 실패 rung의 UNCERTAIN도 trace에 보존했다.',
        '성공 구간은 첫 generalized eigenvalue 하나를 엄밀하게 격리하고 exact 반환 E를 포함한다.',
        '이는 E라는 유한 소수가 정확한 eigenvalue와 같다는 주장이 아니다. E/v의 연결은 아래 transformed residual 측정으로 별도 확인한다.',
        'count_low>0이면 sigma_low<E 아래에 이미 root가 있으므로 E가 lowest라는 주장은 반박된다.',
        '1→2이면 그 좁은 구간에 두 번째 root 하나가 있다. 첫 root의 에너지 자체는 구하지 않았다.',
        'SPD가 실패한 case는 ordered SPD generalized spectrum 경로를 적용하지 않았다.',
        '최저 구간 확인은2/5이므로 전체 SUPPORTED/CERTIFIED 승격은 하지 않았다.','',
        '## SECOND ROOT','',
        '독립 λ1/λ2 양쪽 energy enclosure를 찾는 추가 spectral search는 사전 비용 제한으로 미실행.',
        '실패 case의 1→2 count가 확보된 경우에는 해당 반환 E 주변이 두 번째 root 구간이라는 좁은 사실만 기록한다.',
        '다른 case에 이 사실을 일반화하지 않는다.','',
        '## GENERALIZED RESIDUAL / nS / RQ','',
        '독립 mpmath1.3.0,240 decimal에서 실제 저장 H/S/E/v를 다시 계산했다. 이전160자리 값을 답으로 재사용하지 않았다.',
        'S SPD일 때만 새 HP Cholesky solve로 r^TS^-1r를 구했다. native factor/정규화값을 사용하지 않았다.',
        '전체 값과 nS/RQ180자리는 [case metadata](evidence/cases/) 및 raw full_result에 있다.',
        '', '| case | raw L2 | raw Linf | abs(nS-1) | RQ-E | rho | root/eigenpair consistency |',
        '|---|---:|---:|---:|---:|---:|---|']
    for lab,r in zip(labels,rows):
        m=r['residual'];co=r['eigenpair_consistency'];text.append(f"| {lab} | {small(m['residual_L2'])} | {small(m['residual_Linf'])} | {small(m['normalization_error'])} | {small(m['RQ_minus_E'])} | {small(m['transformed_residual'])} | {co} |")
    text+=['','S=C C^T, T=C^-1HC^-T, y=C^Tv로 두면 (T-EI)y=C^-1r다.',
        '실수 대칭 T의 스펙트럼 정리로 dist(E,spectrum)<=||C^-1r||/||y||=sqrt(r^TS^-1r/nS)=rho.',
        '|RQ-E|<=rho는 Cauchy–Schwarz. [LAPACK SPD reduction](https://www.netlib.org/lapack/lug/node54.html)에 맞춘 직접 유도다.',
        'root 성공에서 RQ의 bracket 포함, Cauchy 관계, [E-rho,E+rho]의 bracket 교차·포함을 측정 확인했다.',
        '**MEASURED_ONLY_NO_ACCEPTANCE_THRESHOLD**: 임의 잔차 tolerance 없음. rho 계산은 interval bound가 아니므로',
        'eigenvector backward-error formal certificate로 승격하지 않는다. 작은 raw residual은 non-lowest root도 만족할 수 있다.','',
        '## CHECKER FAULT INJECTION / fresh tests','',
        '실제5개 S의 시험 사본에서 S00=-abs(S00)-1로 변경하고 모두 첫 negative pivot/정확 negative direction을 탐지했다.',
        'authoritative H/S는 불변. Native solver의 예제 물리 입력을 변경한 실험은 아니다.',
        '사전 synthetic33시험PASS: exact congruent roots, near-root 양쪽 count, exact root ambiguity,',
        'SPD2^-600 ladder, max-rung uncertainty, indefinite, nonsingular zero pivot, parser/layout/false count corruption.',
        'zero-containing pivot의 중심을 보고 부호를 선택한 사례0. 실패 native process/추가 재시도0.',
        '첫 관련시험은 이전 단계와 같은 시험 모듈명으로 collection error1에 멈췄다.',
        '첫 log/xml을 attempt1로 보존하고 새 시험 directory에 __init__.py를 추가해 namespace를 격리했다.',
        'sealed numerical checker/합성33시험/PLAN은 변경하지 않았다. 결과 취득 후 시험 수집에만 적용됐다.',
        '첫 로그를 출력하던 Python 부모의 cp949 encoding error도 있었다. 원래 capture bytes를 보존했고',
        '최종 launcher 출력만 UTF8로 지정했다. 과거 FULL 컴파일러 진단 encoding 경고 해결 주장은 하지 않는다.',
        '실제 음의 방향 proof는 결과 획득 후 새 시험의 별도 Fraction matrix-action 경로로도 재확인했다.',
        '이 후속 proof replay는 사후 검증이며 새 blind external audit로 부르지 않는다.',
        f"관련 시험 fresh **{v['tests']} passed / failure{v['failures']} / error{v['errors']} / skip{v['skipped']}**; 134개37.38초와35개0.49초의 두 실행을 합산했다(37.87초).",
        '[검증](evidence/verification.json)·[시험 로그](evidence/related_tests.log)·[junit](evidence/related_tests.xml).',
        'LOCAL FULL 생략 / 관련 시험으로 대체 / 새 isolated analysis/checker/test/report만 추가, 기존 A/common/frozen source/fixture 변경 없음.',
        '공식 기준선3289+1strict xfail 갱신 없음.','',
        '## WHAT IS PROVED / WHAT IS NOT PROVED','',
        '확정: 개별 저장 S의 interval SPD 또는 exact negative direction, SPD case의 독립 shifted inertia,',
        '성공 case의 λ1 구간과 E 포함, 실패1→2 case의 non-lowest 반례. 코드의 전체 formal proof/외부기관 감사는 아니다.',
        '측정:240자리 residual·metric normalization·RQ·transformed residual와 일관성.',
        '미확인: source recurrence 물리 정확성, NMAX 충분성, basis convergence, reference 정확성,',
        '저장 전 오차 원인, H2SOLV 전체 correctness, R=.4 B1, B2 독립 JC.',
        '이전 output reproduction/noninterference/실제 수렴 분기/MAXIT detector 증거는 보존한다.',
        '이번 반례는 그 증거를 삭제하지 않고 더 강한 lowest 주장만 막는다.','',
        '## FINAL CLASSIFICATION / NEXT DESIGNER DECISION','',
        '**'+t['classification']+' / STOP / NOT_CERTIFIED / NOT_PRODUCTION_APPROVED.**',
        'VENDOR/AUDIT scientific code·output·예제 precision/NMAX/OMEGA는 그대로다. R=.4/B2/sweep/optimization/push0.',
        '다음은 SPD 위반 저장 S의 생성 원인과 SPD이지만 non-lowest로 수렴한 예제의 root-selection 원인을',
        '분리해서 진단할 범위를 설계자가 결정하는 단계다. NMAX sweep/EN 변경이나 수정은 이번에 승인·실행하지 않았다.',
        'General의 interval wrapping을 줄이는 다른 verified factorization 또는 더 높은 checker precision 역시 새 승인 범위 대상이다.',
        'AGENTS/RULES를 읽었고 CURRENT_STATE 상단 현재 Gate/H2와 REPO_MAP의 전자구조 범위를 확인했다.',
        '최신 첨부 지시 전체 및 source shift/scaling/WA1 집계 줄을 직접 확인했다.',
        '과거 V0 PLAN/REPORT/format/protocol을 확인했지만 H2SOLV 전체 recurrence나 전체 repository를 재독·재증명한 것은 아니다.',
        'scientific-critical-thinking의 관찰/해석 분리를 적용했다. Software reference:',
        'Kassis, Agarwal, He, Patel & Brueckner (2026), [Scientific Agent Skills](https://arxiv.org/abs/2609.00065),',
        '현재 v2 metadata 확인. H2 물리 정확성 근거가 아니다.']
    (DOC/'REPORT.md').write_text('\n'.join(text)+'\n',encoding='utf8')
    print('Report generated from actual evidence; no numerical classifier changes.')

if __name__=='__main__':
    import sys
    {'package':package,'report':report}[sys.argv[1]]()
