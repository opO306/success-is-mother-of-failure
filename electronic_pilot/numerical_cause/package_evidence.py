"""Preserve compact stage evidence and verify original/source/raw hashes."""
import hashlib
import json
import shutil
from pathlib import Path


def h(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reconstructed_initial_hp_source():
    """Recover the initial source from the recorded, limited repair diff.

    This reconstructed snapshot is accepted only if its bytes match the
    SHA-256 sealed BEFORE the failed initial HP run.
    """
    path=Path("electronic_pilot/numerical_cause/high_precision.py")
    source=path.read_text()
    start=source.index("        # The historical LAPACK Cholesky")
    end=source.index("        error=c.T*a*c",start)
    source=source[:start]+"        if a!=a.T:\n            raise ValueError(\"AO overlap is asymmetric; cannot use Hermitian factorization\")\n        c=mp.inverse(mp.cholesky(a).T)\n"+source[end:]
    source=source.replace("    i,j=map(int,pair_a)\n    k,l=map(int,pair_b)","    i,j=pair_a\n    k,l=pair_b")
    source=source.replace(',AO_s_asymmetry=float(abs(s-s.T).max())','')
    source=source.replace('    p.add_argument("--output",default="high_precision_v2")\n','')
    source=source.replace('    target=root/args.output','    target=root/"high_precision"')
    source=source.replace('              overlap_factorization="lower-triangle recurrence identical in meaning to historical LAPACK; raw nonsymmetric S used for the residual; no matrix averaging",\n','')
    return source.encode()


def main():
    raw=Path("runs/h2_numerical_cause_v1")
    target=Path("docs/active/h2_numerical_cause_v1")
    target.mkdir(exist_ok=True)
    protected=json.loads((raw/"controls/seal.json").read_text())["protected_sha256"]
    assert all(h(Path(p))==expected for p,expected in protected.items()),"old pilot/evidence changed"
    # Original failure JSONs and seals checked against the previous manifest.
    previous=json.loads(Path("docs/active/h2_static_pilot_v2/raw_manifest.json").read_text())
    old_json={p:v for p,v in previous.items() if p.endswith(".json")}
    assert all(h(Path(p))==v["sha256"] for p,v in old_json.items()),"old raw JSON changed"
    for stage in ("controls","reproduce","compare","qz_curve","high_precision_v2"):
        data=json.loads((raw/stage/"results.json").read_text())
        for row in data["rows"]:
            if "AO_artifact_sha256" in row:
                assert h(raw/stage/f"R_{row['R_bohr']:g}.npz")==row["AO_artifact_sha256"]
            for p in row.get("paths",[]):
                if "artifact_sha256" in p:
                    name=f"point_{data['rows'].index(row):03d}_{p['path']}_{p['backend']}.npz"
                    assert h(raw/stage/name)==p["artifact_sha256"],name
        for name in ("results.json","seal.json"):
            shutil.copyfile(raw/stage/name,target/f"{stage}_{name}")
    for name in ("summary.json","selection.json"):
        shutil.copyfile(raw/name,target/name)
    for name in ("seal.json","comparison.json","checker_records.json"):
        shutil.copyfile(raw/"physical_comparison_v2"/name,target/f"physical_{name}")
    shutil.copyfile(raw/"high_precision/seal.json",target/"initial_hp_failed_seal.json")
    shutil.copyfile(Path("runs/h2_numerical_cause_hp_initial.xml"),target/"initial_hp_failed_tests.xml")
    shutil.copyfile(Path("runs/h2_numerical_cause_hp_repaired.xml"),target/"initial_hp_repaired_tests.xml")
    initial=reconstructed_initial_hp_source()
    sealed=json.loads((raw/"high_precision/seal.json").read_text())["sources"]
    expected=next(v for k,v in sealed.items() if k.endswith("/high_precision.py"))
    assert hashlib.sha256(initial).hexdigest()==expected,"initial source reconstruction mismatch"
    (target/"initial_hp_executed.py.txt").write_bytes(initial)
    old_test=Path("electronic_pilot/numerical_cause/test_integration.py").read_text()
    start=old_test.index("def test_asymmetric_raw_overlap")
    end=old_test.index("def test_three_real_AO",start)
    old_test=(old_test[:start]+old_test[end:]).encode()
    expected_test=next(v for k,v in sealed.items() if k.endswith("/test_integration.py"))
    assert hashlib.sha256(old_test).hexdigest()==expected_test,"initial test source reconstruction mismatch"
    (target/"initial_hp_test_executed.py.txt").write_bytes(old_test)
    for p in Path("electronic_pilot/numerical_cause").glob("*.py"):
        shutil.copyfile(p,target/(p.name+".txt"))
    for stem in ("controls","reproduce","compare","curve","hp","hp_v2","physical_comparison","physical_comparison_v2"):
        shutil.copyfile(Path(f"runs/h2_numerical_cause_{stem}.log"),target/f"{stem}.log")
    for platform in ("windows","wsl"):
        for extension in ("log","xml"):
            shutil.copyfile(Path(f"runs/h2_numerical_cause_{platform}_final.{extension}"),target/f"{platform}_tests.{extension}")
    # Existing outcore calls regenerate integrals; only the common-AO incore
    # records use the exact ndarray whose digest is stored in each path row.
    note=dict(original_outcore_AO_digest_scope="snapshot for diagnostics; outcore recomputes integrals on the fly, not a byte-identity assertion for its internal packed buffers",
              common_ao_incore_scope="all three coordinates at a geometry use the identical full s1 ndarray",
              initial_hp_source="reconstructed from the limited repair diff; byte hash matches its pre-failure seal",
              physical_adapter_initial_failure="missing outer-process RSS field in checker view; original failed records retained; fixed adapter did not alter curve data",
              initial_hp_failures="NumPy integer type in a unit test; initial worker correctly refused raw asymmetric overlap; later lower-triangle diagnostic validates against full unmodified S",
              original_protected_files_checked=len(protected),original_raw_JSONs_checked=len(old_json),not_certified=True)
    (target/"provenance_note.json").write_text(json.dumps(note,indent=2)+"\n",encoding="utf-8")
    manifest={str(p):dict(sha256=h(p),bytes=p.stat().st_size) for p in sorted(raw.rglob("*")) if p.is_file()}
    (target/"raw_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print("old protected",len(protected),"old raw JSON",len(old_json),"new raw manifest",len(manifest),"verified")


if __name__=="__main__":
    main()
