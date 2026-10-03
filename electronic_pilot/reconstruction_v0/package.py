"""Preserve compact executed evidence, raw inventory, and failed versions."""
from pathlib import Path
import shutil
from electronic_pilot.frontend_reference_v0.audit import read,write,sha,verify


def main():
    root=Path.cwd();raw=root/'runs/h2_reconstruction_v0';dest=root/'docs/active/h2_reconstruction_v0/evidence';dest.mkdir(parents=True,exist_ok=False)
    phases={'run_v0':'failed_case_collision','run_io_v1':'failed_filename_replacement','run_io_v2':'','post_v0':'post','influence_v0':'influence','cause_spots_v0':'cause_spots'}
    inventory={};links={}
    for phase,alias in phases.items():
        for p in sorted((raw/phase).rglob('*')):
            if p.is_symlink():links[p.relative_to(root).as_posix()]=str(p.readlink());continue
            if not p.is_file():continue
            inventory[p.relative_to(root).as_posix()]=dict(sha256=sha(p),bytes=p.stat().st_size)
            if p.suffix not in ('.json','.log','.txt') or p.name=='vector.txt':continue
            relative=p.relative_to(raw/phase);q=dest/alias/relative;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
        if phase=='run_io_v2':
            for arm in ('L','I'):
                for name in ('s.npy','c.npy','S_spectrum.npy','ground_vector.npy'):
                    shutil.copyfile(raw/phase/arm/name,dest/arm/name)
    write(dest/'raw_inventory.json',dict(files=inventory,symlinks=links,raw_scope='only new named reconstruction phases, not whole runs directory'))
    count=verify(read(raw/'run_io_v2/execution_seal.json')['bound_sha256'],root,Path('C:/Users/zun24/성공은 실패의 어머니'))
    write(dest/'preservation_final.json',dict(original_and_initial_source_bindings_unchanged=True,bindings_checked=count,inherited_bindings=1178,
            existing_physics_frozen_sources_changed=False,source_versions_preserved=['numeric.cpp','numeric_io_v1.cpp','run.py','run_io_v1.py','run_io_v2.py']))
    write(dest/'failure_journal.json',dict(attempts=[
        dict(version='run_v0',reason='Windows case-insensitive h.bin/H.bin collision; one-body file overwritten, reshape fails before eigensolve',ground_energy_generated=False,tool_exit_code=1),
        dict(version='run_io_v1',reason='overbroad filename replacement produced singlet_matrix_higone_body.bin; high-precision refinement input unavailable',ground_energy_generated='preliminary L solve only, never overall accepted',tool_exit_code=1),
        dict(version='run_io_v2',reason='file-path-only correction, same numeric_io_v1.cpp and unchanged mathematical contract',tool_exit_code=0,completed_arms=2)],
        refused_precision_branches='Both 64-bit-significand H matrices failed pre-eigensolve guard; no energies filled',all_failures_preserved=True,automatic_fourth_attempt=False))
    print('PACKAGED',len(inventory),'raw files; preserved',count,flush=True)


if __name__=='__main__':main()
