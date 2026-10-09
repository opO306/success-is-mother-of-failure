"""Original consent/closure prerequisites plus the exact newly granted absolute end."""
from pathlib import Path
import importlib.util
from time_authority import require_extension
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('v12_original_preflight',HERE.parent/'revision_v12/preflight.py')
original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
require_tools=original.require_tools
require_time_extension=original.require_time_extension
def require_finite_policy(policy):
    if policy.get('v12_2_exact_extension') is not True:return original.require_finite_policy(policy)
    grant=require_extension()
    if policy.get('lease_seconds')!=grant['lease_seconds']:raise ValueError('SINGLE_GRANTED_ABSOLUTE_END')
    return original.require_finite_policy(dict(policy,lease_seconds=1800))
before_any_rental=original.before_any_rental
