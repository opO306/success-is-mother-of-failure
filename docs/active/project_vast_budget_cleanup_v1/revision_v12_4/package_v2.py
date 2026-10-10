"""V12.4: attach A package revision 2 (one test-order fix) to the unchanged V12 transport, campaign and recovery.

The original V12 files, tablet_814.zip, its inventory and the tablet seals stay byte-identical and are still checked.
Every point below is in-process; no V12 file is edited:
  controller.configure            -> kind A takes the revision-2 entry of package_bindings_v2.json (B: original)
  controller.verify_local_package -> kind A: the original checks applied to revision 2, plus the exact-diff gate
                                     (original package intact; only the test file and the code-seal hash line differ)
  controller Transport.py_once    -> kind A 'guest_source_verify.py' sends guest_source_verify_v2.py, same command shape
  campaign.source_preflight       -> original checks (original packages intact) + revision-2 file pins
  campaign.transport_binding      -> kind A binding carries the revision-2 code/zip/inventory hashes
  terminal_proof.require_terminal -> the original A spec is replaced by the revision-2 spec (parent and watchdog)
Nothing here accepts "anything": revision-2 hashes are pinned as constants and every pin fails closed.
"""
import hashlib,json,shlex,time,zipfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
V12_BINDINGS=HERE.parent/'revision_v12/transport/package_bindings.json'
V12_BINDINGS_SHA256='44cbc9288d50567ca65055c6a867a3d052530d2758a1a52a38ecf64d47c96be4'
V2_BINDINGS=HERE/'package_bindings_v2.json'
V2_BINDINGS_SHA256='84f461a04892bacd1c933173246bab70211c37e6a3166f67ef3edd2a65c18c2d'
GUEST_V2=HERE/'guest_source_verify_v2.py'
GUEST_V2_SHA256='d28b5a78303dc758f4e263fdd3ac1519bebee93da1609d9b710f0c24adb26c52'
TEST='tests/test_adaptive_experience_tablet_v0.py'
SEAL='experiments/adaptive_experience_tablet_v0/code_seal.json'
EXTRA='experiments/adaptive_execution_real_learning_pilot_a_resume_v1/code_seal.json'
EXTRA_SHA256='ec1b50b4f32dc8cd3334aab6c6d063f340328fc2d24e73b8b16814052e6b5d60'
ORIGINAL_CODE='18a76f0e2ea466b7a13e2066367cfc8d52ba6085be66045dacc062490ef08d09'
V2_CODE='10e8c73f6466746dc761efca7e8d0c0172ae4edfceed171d71efff08b3ea29ce'
ORIGINAL_TEST='41b7c97f031ad8f305b94463cf2a90f8feef3181c1127c4430a32acc328add67'
V2_TEST='7727af7d0742858a0660ba1ee01a9b8472e8bda9d5d17fb6f9aba4cf8e799238'
# The approved change, checked independently of the builder: original block -> revision-2 block, exactly once.
OLD_BLOCK=(b"    tablet,_,_,_=archive; original=Path.read_bytes; accessed=[]\n"
           b"    def capture(path): accessed.append(path); return original(path)\n"
           b"    monkeypatch.setattr(Path,'read_bytes',capture)\n"
           b"    hits=tablet.search(request())\n")
NEW_BLOCK=(b"    tablet,_,_,_=archive; query=request(); original=Path.read_bytes; accessed=[]\n"
           b"    def capture(path): accessed.append(path); return original(path)\n"
           b"    monkeypatch.setattr(Path,'read_bytes',capture)\n"
           b"    hits=tablet.search(query)\n")
BINDING_KEYS=('code_sha256','protocol_sha256','zip_sha256','inventory_sha256','expected_tests')


def sha(data):return hashlib.sha256(data).hexdigest()


def decode(raw):
    def pairs(items):
        out={}
        for k,v in items:
            if k in out:raise ValueError('DUPLICATE_JSON_KEY:'+k)
            out[k]=v
        return out
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda v:(_ for _ in ()).throw(ValueError('NONFINITE_JSON')))


def bindings():
    old=V12_BINDINGS.read_bytes();new=V2_BINDINGS.read_bytes()
    if sha(old)!=V12_BINDINGS_SHA256:raise ValueError('V12_ORIGINAL_BINDINGS_DRIFT')
    if sha(new)!=V2_BINDINGS_SHA256:raise ValueError('V12_4_REVISION_2_BINDINGS_DRIFT')
    old,new=decode(old),decode(new)
    if new['B']!=old['B'] or new['A']['code_sha256']!=V2_CODE or old['A']['code_sha256']!=ORIGINAL_CODE:
        raise ValueError('V12_4_BINDINGS_SCOPE')
    return old,new


def verify_revision_files():
    """Raw pins of every revision-2 input, plus the original A package still being exactly the sealed one."""
    old,new=bindings()
    for spec,label in ((old['A'],'ORIGINAL'),(new['A'],'REVISION_2')):
        if sha((ROOT/spec['archive']).read_bytes())!=spec['zip_sha256'] or sha((ROOT/spec['inventory']).read_bytes())!=spec['inventory_sha256']:
            raise ValueError(label+'_PACKAGE_A_RAW_PIN')
    if sha((ROOT/new['A']['comparison']).read_bytes())!=new['A']['comparison_sha256']:raise ValueError('REVISION_2_MANIFEST_PIN')
    if sha(GUEST_V2.read_bytes())!=GUEST_V2_SHA256:raise ValueError('V12_4_GUEST_VERIFIER_PIN')
    return dict(original_zip_sha256=old['A']['zip_sha256'],revision_2_zip_sha256=new['A']['zip_sha256'])


def make_configure(module,original):
    def configure(kind):
        original(kind)
        if kind=='A':
            _,new=bindings();spec=new['A']
            module.SPEC=spec
            module.CODE,module.PROTO,module.ZIP_HASH=spec['code_sha256'],spec['protocol_sha256'],spec['zip_sha256']
            module.SOURCE,module.INVENTORY=module.ROOT/spec['archive'],module.ROOT/spec['inventory']
            module.INVENTORY_HASH,module.EXPECTED=spec['inventory_sha256'],spec['expected_tests']
    configure.v12_4_wrapped=True
    return configure


def make_verify(module,original):
    def verify_local_package():
        if module.KIND!='A':return original()
        old,new=bindings();spec=module.SPEC
        if spec!=new['A'] or module.CODE!=V2_CODE or module.ROOT!=ROOT:raise ValueError('V12_4_REVISION_2_CONFIGURATION_REQUIRED')
        # 1. The original package is preserved exactly.
        prior=old['A'];prior_inventory_raw=(ROOT/prior['inventory']).read_bytes()
        if sha((ROOT/prior['archive']).read_bytes())!=prior['zip_sha256'] or sha(prior_inventory_raw)!=prior['inventory_sha256']:
            raise ValueError('ORIGINAL_PACKAGE_A_MUST_STAY_PRESERVED')
        # 2. Same checks as controller.verify_local_package, against revision 2 (code seal read from the pinned zip).
        if sha(module.INVENTORY.read_bytes())!=module.INVENTORY_HASH or sha(module.SOURCE.read_bytes())!=module.ZIP_HASH:
            raise ValueError('EXACT_NEW_PACKAGE_EXTERNAL_PINS')
        inventory=module.load(module.INVENTORY)
        if inventory['zip_sha256']!=module.ZIP_HASH or inventory['entries']!=spec['entries']:raise ValueError('INVENTORY_PACKAGE_SCOPE')
        if sha((ROOT/spec['case_inventory']).read_bytes())!=spec['case_inventory_sha256']:raise ValueError('ORIGINAL_320_CASE_INVENTORY_PIN')
        with zipfile.ZipFile(module.SOURCE) as z:
            seal_raw=z.read(SEAL);new_test=z.read(TEST)
            if sha(seal_raw)!=V2_CODE:raise ValueError('REVISION_2_CODE_SEAL_PIN')
            code=decode(seal_raw)
            required=dict(code['files'],**{SEAL:V2_CODE,EXTRA:EXTRA_SHA256})
            if len(code['files'])!=812 or inventory['files']!=required or len(required)!=814:
                raise ValueError('PRESERVE_813_PLUS_EXACT_EXISTING_SEAL')
            names=z.namelist()
            if (len(names)!=spec['entries'] or len(names)!=len(set(names)) or len(names)!=len({n.casefold() for n in names})
                    or set(names)!=set(required) or sum(i.file_size for i in z.infolist())!=inventory['uncompressed_bytes']):
                raise ValueError('EXACT_PACKAGE_MEMBERS_AND_SIZE')
            for info in z.infolist():
                module.safe_name(info.filename)
                if info.is_dir() or info.flag_bits&1 or (info.external_attr>>16)&0o170000 not in (0,0o100000):
                    raise ValueError('PACKAGE_REGULAR_UNENCRYPTED_ONLY')
            for name,wanted in required.items():
                if sha(z.read(name))!=wanted:raise ValueError('PACKAGE_CRC_OR_RAW_HASH:'+name)
        # 3. Exact difference to the original: only the approved test block and that one seal hash.
        prior_inventory=decode(prior_inventory_raw)
        with zipfile.ZipFile(ROOT/prior['archive']) as z:old_seal=z.read(SEAL);old_test=z.read(TEST)
        changed=sorted(n for n in set(prior_inventory['files'])|set(inventory['files']) if prior_inventory['files'].get(n)!=inventory['files'].get(n))
        if set(prior_inventory['files'])!=set(inventory['files']) or changed!=sorted((SEAL,TEST)):raise ValueError('REVISION_2_EXACT_TWO_MEMBER_DIFF')
        if sha(old_seal)!=ORIGINAL_CODE or sha(old_test)!=ORIGINAL_TEST or sha(new_test)!=V2_TEST:raise ValueError('REVISION_2_MEMBER_PINS')
        if old_test.count(OLD_BLOCK)!=1 or old_test.replace(OLD_BLOCK,NEW_BLOCK)!=new_test:raise ValueError('REVISION_2_APPROVED_TEST_BLOCK_ONLY')
        if old_seal.count(ORIGINAL_TEST.encode())!=1 or old_seal.replace(ORIGINAL_TEST.encode(),V2_TEST.encode())!=seal_raw:
            raise ValueError('REVISION_2_SEAL_ONE_HASH_ONLY')
        return dict(package_kind='A',entries=spec['entries'],inventory_sha256=module.INVENTORY_HASH,zip_sha256=module.ZIP_HASH,
                    package_revision=spec['package_revision'],revision_of_zip_sha256=prior['zip_sha256'],changed_members=changed)
    verify_local_package.v12_4_wrapped=True
    return verify_local_package


def make_transport(module):
    class PackageRevision2Transport(module.Transport):
        v12_4_package=True
        def py_once(self,script_name,args,name,timeout=30,phase_deadline=None,required_seconds=None):
            if script_name!='guest_source_verify.py' or module.KIND!='A':
                return super().py_once(script_name,args,name,timeout,phase_deadline,required_seconds)
            script=GUEST_V2.read_bytes()
            if sha(script)!=GUEST_V2_SHA256:raise ValueError('V12_4_GUEST_VERIFIER_PIN')
            # Same as revision_v12/transport/controller.py py_once for a stdin script (control, deadline, command shape).
            self.control(timeout if required_seconds is None else required_seconds,phase_deadline=phase_deadline)
            if phase_deadline is not None:
                timeout=min(timeout,phase_deadline-time.monotonic())
                if timeout<=0:raise TimeoutError('UNCHANGED_RPC_PHASE_DEADLINE')
            command=shlex.join([module.VENV,'-B','-',*map(str,args)])
            return self.run([*self.ssh_argv,command],name,timeout,input=script)
    return PackageRevision2Transport


def patch_controller(module):
    """Apply to every freshly executed controller.py module (campaign loads it by file path each time)."""
    if getattr(module,'v12_4_package_installed',False):return module
    module.configure=make_configure(module,module.configure)
    module.verify_local_package=make_verify(module,module.verify_local_package)
    module.Transport=make_transport(module)
    module.v12_4_package_installed=True
    return module


def install_campaign(campaign):
    if getattr(campaign.source_preflight,'v12_4_wrapped',False):return campaign
    original_preflight=campaign.source_preflight
    original_binding=campaign.transport_binding
    def source_preflight(policy):
        result=original_preflight(policy)
        verify_revision_files()
        return result
    def transport_binding(policy,kind,owner,out,B_close):
        binding=original_binding(policy,kind,owner,out,B_close)
        if kind=='A':
            old,new=bindings()
            if any(binding[k]!=old['A'][k] for k in BINDING_KEYS):raise ValueError('V12_ORIGINAL_BINDING_SHAPE')
            binding.update({k:new['A'][k] for k in BINDING_KEYS},package_revision=new['A']['package_revision'])
        return binding
    source_preflight.v12_4_wrapped=True;transport_binding.v12_4_wrapped=True
    campaign.source_preflight=source_preflight;campaign.transport_binding=transport_binding
    return campaign


def install_recovery():
    """lifecycle.verified_recovery does `from terminal_proof import require_terminal` at call time."""
    import terminal_proof
    if getattr(terminal_proof.require_terminal,'v12_4_wrapped',False):return terminal_proof
    original=terminal_proof.require_terminal
    old,new=bindings()
    def require_terminal(files,*,writer_completion_verified,spec,original_case_ids=None):
        if spec==old['A']:spec=new['A']
        elif spec!=old['B']:raise ValueError('V12_4_UNKNOWN_PACKAGE_SPEC')
        return original(files,writer_completion_verified=writer_completion_verified,spec=spec,original_case_ids=original_case_ids)
    require_terminal.v12_4_wrapped=True
    terminal_proof.require_terminal=require_terminal
    return terminal_proof


def preflight(campaign,controller):
    """Before any approval use or Provider call: load controller.py exactly as the stage does and run the package gate."""
    files=verify_revision_files()
    spec=campaign.importlib.util.spec_from_file_location('v12_4_package_preflight',controller)
    module=campaign.importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.configure('A')
    if (not getattr(module,'v12_4_package_installed',False) or module.CODE!=V2_CODE
            or not any(getattr(c,'v12_4_package',False) for c in module.Transport.__mro__)):
        raise ValueError('V12_4_CONTROLLER_ATTACHMENT_MISSING')
    import terminal_proof
    if not getattr(terminal_proof.require_terminal,'v12_4_wrapped',False) or not getattr(campaign.transport_binding,'v12_4_wrapped',False):
        raise ValueError('V12_4_RECOVERY_OR_BINDING_ATTACHMENT_MISSING')
    return dict(files,package=module.verify_local_package())
