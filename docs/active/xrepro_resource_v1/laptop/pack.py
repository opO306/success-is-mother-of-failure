"""Pack one XREPRO output directory into DEST: records.json.gz ({relative path: text} of every file, work/ included),
plus campaign.log, execution_seal.json, the comparator output and a SHA256 list of every packed file."""
import gzip, hashlib, json, shutil, sys
from pathlib import Path

src, dest, cmp_file, stdout_file = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
dest.mkdir(parents=True, exist_ok=True)
files, sums = {}, {}
for f in sorted(p for p in src.rglob("*") if p.is_file()):
    rel = f.relative_to(src).as_posix()
    b = f.read_bytes()
    files[rel] = b.decode("utf-8")
    sums[rel] = hashlib.sha256(b).hexdigest()
with gzip.GzipFile(dest / "records.json.gz", "wb", mtime=0) as g:
    g.write(json.dumps({"files": files}, sort_keys=True).encode("utf-8"))
shutil.copy(src / "campaign.log", dest / "campaign.log")
shutil.copy(src / "execution_seal.json", dest / "execution_seal.json")
shutil.copy(cmp_file, dest / "compare_vs_run2.json")
shutil.copy(stdout_file, dest / "stdout.txt")
(dest / "SHA256SUMS.json").write_text(json.dumps(sums, indent=1, sort_keys=True), encoding="utf-8")
print(len(files), "files packed")
