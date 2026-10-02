"""Copy compact evidence to Git; retain large matrix witnesses under runs/."""
import hashlib
import json
import shutil
from pathlib import Path


def main():
    root=Path("docs/active/h2_static_pilot_v2")
    root.mkdir(parents=True,exist_ok=True)
    files={"results.json":"runs/h2_static_pilot_v2/full/results.json",
           "comparison.json":"runs/h2_static_pilot_v2/comparison.json",
           "seal.json":"runs/h2_static_pilot_v2/full/seal.json",
           "sanity_results.json":"runs/h2_static_pilot_v1/sanity/results.json",
           "sanity_seal.json":"runs/h2_static_pilot_v1/sanity/seal.json",
           "solver_executed.py.txt":"runs/h2_static_pilot_v2/solver_executed.py",
           "orthogonality_message_diagnostic.json":"runs/h2_static_pilot_v2/orthogonality_message_diagnostic.json",
           "reference_transcription.json":"runs/h2_reference_sources/transcription_check_v2.json",
           "windows_tests.log":"runs/h2_static_pilot_focused_windows_final.log",
           "windows_tests.xml":"runs/h2_static_pilot_focused_windows_final.xml",
           "wsl_tests.log":"runs/h2_static_pilot_focused_wsl_final.log",
           "wsl_tests.xml":"runs/h2_static_pilot_focused_wsl_final.xml",
           "campaign.log":"runs/h2_static_pilot_v2_campaign.log"}
    for name,source in files.items():
        shutil.copyfile(source,root/name)
    raw_root=Path("runs/h2_static_pilot_v2/full")
    raw={str(x):dict(sha256=hashlib.sha256(x.read_bytes()).hexdigest(),bytes=x.stat().st_size)
         for x in sorted(raw_root.iterdir()) if x.is_file()}
    (root/"raw_manifest.json").write_text(json.dumps(raw,indent=2)+"\n",encoding="utf-8")
    old=Path("runs/h2_static_pilot_v2/solver_executed.py").read_text()
    new=Path("electronic_pilot/solver.py").read_text()
    assert old.replace("error={orth:.17g}","error={orth_error:.17g}")==new
    (root/"postrun_source_note.json").write_text(json.dumps(dict(
        executed_solver_sha256=hashlib.sha256(old.encode()).hexdigest(),
        final_solver_sha256=hashlib.sha256(new.encode()).hexdigest(),
        changed="one f-string variable in the orthonormalization refusal message; no accepted-value calculation changes",
        original_failures="13 numerical refusals; 3 NameError in refusal message; all preserved",
        curve_rerun_after_fix=False),indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
