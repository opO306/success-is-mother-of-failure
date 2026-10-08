"""Research-only signed profiles and signed separate controller witness. No production."""
from dataclasses import dataclass
from pathlib import Path
from .common import Ledger,canonical,digest,read,write_new,public,verify,HERE,raw_hash,code_manifest_path


@dataclass(frozen=True)
class Roots:
    inspector: str
    manager: str
    mode: str
    @classmethod
    def for_contract(cls,judge,ruler): return cls(public(judge),public(ruler),'OFFLINE_CONTRACT_ONLY')


@dataclass(frozen=True)
class Snapshot:
    goal: str
    session_sha256: str
    profile_bytes: bytes|None


class Manager:
    def __init__(self,directory,witness_directory,roots,witness_key):
        self.directory=Path(directory); self.directory.mkdir(parents=True,exist_ok=True)
        self.events=Ledger(self.directory/'events'); self.rejections=Ledger(self.directory/'refusals')
        self.witness=Path(witness_directory); self.witness.mkdir(parents=True,exist_ok=True)
        self.roots,self.key=roots,witness_key
        if roots.mode not in ('OFFLINE_CONTRACT_ONLY','RESEARCH_ONLY') or roots.inspector==roots.manager:
            raise ValueError('PRODUCTION_OR_IDENTICAL_ROOTS_REFUSED')
        if public(witness_key.public_key())!=roots.manager: raise ValueError('WITNESS_AUTHORITY_REFUSED')
        config=self.directory/'roots.json'
        existing=config.exists()
        if config.exists() and read(config)!=roots.__dict__: raise ValueError('ROOT_REPLACEMENT')
        if not config.exists(): write_new(config,roots.__dict__)
        self.head=self.witness/'signed_head.json'
        if not self.head.exists():
            if existing or self.events.history(): self._stop('MISSING_EXTERNAL_WITNESS'); raise ValueError('MISSING_EXTERNAL_WITNESS')
            self._publish_head()
        self._check()

    def _publish_head(self):
        history=self.events.history(); body={'count':len(history),'tip':history[-1]['sha256'] if history else 'GENESIS'}
        envelope={'body':body,'signature':self.key.sign(b'REAL_PILOT_WITNESS\0'+canonical(body)).hex()}
        # Controller-owned mutable head; signed historical activation records remain immutable.
        self.head.write_bytes(canonical(envelope))

    def _check(self):
        if (self.directory/'STOP.json').exists(): raise ValueError('STOP_NEW_REQUEST')
        if read(self.directory/'roots.json')!=self.roots.__dict__: self._stop('ROOT_INTEGRITY'); raise ValueError('ROOT_INTEGRITY')
        try:
            witness=read(self.head); verify(self.roots.manager,b'REAL_PILOT_WITNESS\0',witness)
            history=self.events.history()
        except Exception as error:
            self._stop('WITNESS_OR_LEDGER_INTEGRITY'); raise ValueError('WITNESS_OR_LEDGER_INTEGRITY') from error
        if witness['body']!={'count':len(history),'tip':history[-1]['sha256'] if history else 'GENESIS'}:
            self._stop('TAIL_OR_FORK_INTEGRITY'); raise ValueError('TAIL_OR_FORK_INTEGRITY')
        return history

    def _receipt(self,receipt):
        verify(self.roots.inspector,b'REAL_PILOT_RECEIPT\0',receipt); body=receipt['body']
        expected='CONTRACT_VALIDATED' if self.roots.mode=='OFFLINE_CONTRACT_ONLY' else 'REAL_SESSION_COST_CHECKED'
        if (body.get('verdict')!=expected or body.get('errors') or body.get('formula_independence')!='UNRESOLVED_SHARED_RWFORCE'
                or body.get('real_cost_evidence')!=(self.roots.mode=='RESEARCH_ONLY')
                or body.get('goal') not in ('CPU_MIN','WALL_MIN')
                or body.get('protocol_sha256')!=raw_hash(HERE/'protocol.json')):
            raise ValueError('INVALID_RECEIPT_SCOPE')
        if self.roots.mode=='RESEARCH_ONLY' and (body.get('scope')!='RESEARCH_ONLY'
                or body.get('code_manifest_sha256')!=raw_hash(code_manifest_path()) or not body.get('raw_files')):
            raise ValueError('REAL_RECEIPT_CODE_OR_RAW_BINDING')
        if self.roots.mode=='RESEARCH_ONLY':
            if body.get('stage') not in ('A','B'): raise ValueError('RECEIPT_STAGE_REFUSED')
            evidence=(self.directory.parent/body['stage']).resolve()
            for relative,expected_hash in body['raw_files'].items():
                path=(evidence/relative).resolve()
                if not path.is_relative_to(evidence) or raw_hash(path)!=expected_hash: raise ValueError('ADMITTED_RAW_EVIDENCE_INTEGRITY')
        return body

    def _stop(self,reason):
        if not (self.directory/'STOP.json').exists(): write_new(self.directory/'STOP.json',{'status':'STOP','reason':reason})

    def _reject(self,op,raw,error):
        self.rejections.append({'operation':op,'verdict':'REFUSED','evidence':raw,'error':str(error)})

    def admit(self,receipt):
        try:
            self._check(); body=self._receipt(receipt)
            profile={'state':'VERIFIED','mode':self.roots.mode,'session_sha256':body['session_sha256'],'goal':body['goal'],
                     'rows':body['rows'],'receipt':receipt}; profile['id']=digest(profile)
            path=self.directory/'profiles'/f"{profile['id']}.json"
            if not path.exists(): write_new(path,profile)
            return read(path)
        except Exception as error: self._reject('ADMIT',receipt,error); raise ValueError(str(error)) from error

    def approval_body(self,target,goal,decision,reason):
        history=self._check()
        return dict(mode=self.roots.mode,profile_id=target,goal=goal,decision_id=decision,reason=reason,
                    predecessor=history[-1]['sha256'] if history else 'GENESIS')

    def _profile(self,target):
        if len(target)!=64 or any(x not in '0123456789abcdef' for x in target): raise ValueError('PROFILE_NOT_ADMITTED')
        profile=read(self.directory/'profiles'/f'{target}.json')
        if profile['id']!=target or digest({k:v for k,v in profile.items() if k!='id'})!=target: raise ValueError('PROFILE_INTEGRITY')
        receipt=self._receipt(profile['receipt'])
        if (profile['rows']!=receipt['rows'] or profile['goal']!=receipt['goal']
                or profile['session_sha256']!=receipt['session_sha256'] or profile['mode']!=self.roots.mode):
            raise ValueError('PROFILE_INTEGRITY')
        return profile

    def activate(self,approval):
        try:
            history=self._check(); verify(self.roots.manager,b'REAL_PILOT_APPROVAL\0',approval); body=approval['body']
            if (body['mode']!=self.roots.mode or body['goal'] not in ('WALL_MIN','CPU_MIN') or not body['reason']
                    or body['predecessor']!=(history[-1]['sha256'] if history else 'GENESIS')
                    or any(event['payload']['body']['decision_id']==body['decision_id'] for event in history)):
                raise ValueError('APPROVAL_REFUSED')
            if body['profile_id']!='LEGACY' and self._profile(body['profile_id'])['goal']!=body['goal']:
                raise ValueError('GOAL_APPROVAL_MIX')
            self.events.append(approval); self._publish_head()
        except Exception as error: self._reject('ACTIVATE',approval,error); self._stop('INVALID_APPROVAL'); raise ValueError(str(error)) from error

    def rollback(self,approval):
        try:
            history=self._check(); target=approval['body']['profile_id']
            if target!='LEGACY' and target not in {event['payload']['body']['profile_id'] for event in history}:
                raise ValueError('ROLLBACK_TARGET_NOT_PREVIOUS')
            self.activate(approval)
        except Exception as error: self._reject('ROLLBACK',approval,error); self._stop('ROLLBACK_FAILED'); raise ValueError(str(error)) from error

    def review_correction(self,certificate):
        from experiments.evidence_canonicalization_v0 import correction
        try:
            self._check()
            if self.roots.mode!='RESEARCH_ONLY': raise ValueError('CORRECTION_REVIEW_SCOPE')
            return correction.validate(certificate,self.roots.inspector)
        except Exception as error:
            self._reject('CORRECTION_REVIEW',certificate,error)
            raise ValueError(str(error)) from error

    def approve_correction(self,certificate,approval):
        """Signed metadata review; no new performance profile or existing-profile change."""
        try:
            reviewed=self.review_correction(certificate)
            verify(self.roots.manager,b'REAL_PILOT_APPROVAL\0',approval); b=approval['body']
            if (b.get('profile_id')!='LEGACY' or b.get('correction_id')!=reviewed['certificate_sha256']
                    or b.get('goal')!=reviewed['goal'] or any(e['payload']['body']['profile_id']!='LEGACY' for e in self._check())):
                raise ValueError('CORRECTION_CANNOT_ACTIVATE_OR_CHANGE_PROFILE')
            self.activate(approval)
            write_new(self.directory/'correction_approvals'/f"{reviewed['certificate_sha256']}.json",
                  dict(certificate_sha256=reviewed['certificate_sha256'],approval=approval,
                       scope='APPROVED_HISTORICAL_REVIEW_ONLY',profile_activation='NONE',original_status='REAL_LEARNING_FAIL'))
        except Exception as error:
            self._reject('CORRECTION_APPROVE',approval,error); self._stop('INVALID_CORRECTION_APPROVAL')
            raise ValueError(str(error)) from error

    def begin(self,goal,session):
        if goal not in ('CPU_MIN','WALL_MIN'): raise ValueError('GOAL_REFUSED')
        history=self._check(); target='LEGACY'
        for event in history:
            verify(self.roots.manager,b'REAL_PILOT_APPROVAL\0',event['payload'])
            if event['payload']['body']['goal']==goal: target=event['payload']['body']['profile_id']
        return Snapshot(goal,digest(session),None if target=='LEGACY' else canonical(self._profile(target)))

    def choose(self,snapshot,session):
        self._check()
        if snapshot.profile_bytes is None or snapshot.session_sha256!=digest(session): return 'LEGACY'
        import json
        profile=json.loads(snapshot.profile_bytes)
        if canonical(self._profile(profile['id']))!=snapshot.profile_bytes: raise ValueError('SNAPSHOT_INTEGRITY')
        if profile['session_sha256']!=digest(session): return 'LEGACY'
        if profile['goal']!=snapshot.goal: raise ValueError('GOAL_MIX')
        rows=profile['rows']
        if snapshot.goal=='CPU_MIN': return min(rows,key=lambda x:(x['cpu_ns'],x['wall_ns'],x['method']))['method']
        best=min(row['wall_ns'] for row in rows)
        return min((row for row in rows if row['wall_ns']*100<=best*105),key=lambda x:(x['cpu_ns'],x['method']))['method']
