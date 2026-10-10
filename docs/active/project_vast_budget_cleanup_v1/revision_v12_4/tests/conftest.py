"""Mock-only tests for V12.3: no network, no Vast CLI, no SSH, no physics. Paths match fresh_owned's order."""
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parents[1]
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
import process_bridge
process_bridge.paths()
