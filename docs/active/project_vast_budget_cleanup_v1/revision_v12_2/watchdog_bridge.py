"""Run the unchanged V12 watchdog with the exact extended preflight imported first."""
from pathlib import Path
import sys,runpy
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import preflight  # Exact granted target/time; retained in sys.modules for cleanup.
sys.path.insert(1,str(HERE.parent/'revision_v12'))
sys.path.insert(2,str(HERE.parent/'revision_v12/transport'))
from closure_bridge import install
from time_authority import install as install_time_authority
install_time_authority()
install()
runpy.run_path(str(HERE.parent/'revision_v12/watchdog.py'),run_name='__main__')
