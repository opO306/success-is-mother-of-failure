"""Another machine's signed experience may only ORDER what is measured first on this machine.

Designer idea (2026-10-10): share the tablet across machines; on a first-seen machine try the recorded
faster method first, and only if it is not confirmed here fall back to searching every method.

Authority: none. Nothing here selects, approves or activates a method. v0 policy.safe_method keeps SERIAL
until the existing judge/manager admit a current-session profile measured on THIS machine. Methods must give
identical physics results; a check where they do not is refused (stop condition), never a fallback.
Conservative defaults (designer decisions, see docs/active/ADAPTIVE_EXPERIENCE_TABLET_V1_TRANSFER_HINT_PLAN.md):
  past hint   : candidate's worst recorded time < SERIAL's best recorded time (no overlap)
  machine fit : the existing validator offers that method here (distinct physical cores and cgroup quota)
  check here  : REPEATS paired runs each, no overlap, identical results on every pair
  goal        : WALL_MIN only (v0 always keeps SERIAL for CPU_MIN)
"""
from experiments.evidence_canonicalization_v0.fingerprints import parse_bytes
from experiments.adaptive_experience_tablet_v0 import policy, routes

REPEATS = 5
METRIC = {'WALL_MIN': 'wall_ns'}


def _separated(faster, slower):
    return faster['max'] < slower['min']


def propose(experience, request, host_info, session=None):
    """Return which methods to measure first here. Raises if the request/host is not executable at all."""
    plans = routes.candidates(request, host_info)
    if 'SERIAL' not in plans:
        raise ValueError('NO_SERIAL_BASELINE')
    order_all = ['SERIAL'] + sorted(m for m in plans if m != 'SERIAL')
    base = dict(authority='NONE', self_search_order=order_all, repeats_required=REPEATS)
    goal = request.get('goal')
    if goal not in METRIC:
        return dict(base, decision='NO_HINT_GOAL_NOT_ELIGIBLE', measure_first=order_all)
    kind = policy.classify(experience, request, host_info, session)
    if kind != 'TRANSFER_HINT_ONLY':
        return dict(base, decision='NO_HINT_' + kind, measure_first=order_all)
    meta = experience.metadata
    past_env = parse_bytes(experience.session_bytes)['env']
    if past_env.get('platform') != host_info['env'].get('platform'):
        return dict(base, decision='NO_HINT_PLATFORM_DIFFERS', measure_first=order_all)
    metric = METRIC[goal]
    stats = meta['stats']
    usable = [m for m in stats if m != 'SERIAL' and m in plans and _separated(stats[m][metric], stats['SERIAL'][metric])]
    if not usable:
        return dict(base, decision='NO_HINT_NOT_SEPARATED_OR_NOT_EXECUTABLE_HERE', measure_first=order_all)
    hint = min(usable, key=lambda m: (stats[m][metric]['max'], m))
    return dict(base, decision='TRY_HINT_FIRST', hint=hint, measure_first=['SERIAL', hint],
                fallback_order=[m for m in order_all if m not in ('SERIAL', hint)],
                source=dict(profile_id=meta['profile_id'], session_id=meta['session_id'], env_id=meta['env_id'],
                            cpu_model=meta['cpu_model'], recorded=dict(SERIAL=stats['SERIAL'][metric], hint=stats[hint][metric])),
                current_env_id=host_info['env']['env_id'],
                same_cpu_model=past_env.get('cpu_model') == host_info['env'].get('cpu_model'))


def _repeats(values):
    if (not isinstance(values, list) or len(values) != REPEATS
            or any(type(v) is not int or v <= 0 for v in values)):
        raise ValueError('EXACT_POSITIVE_INTEGER_REPEATS_REQUIRED')
    return dict(min=min(values), max=max(values))


def judge(proposal, serial_ns, hint_ns, results_identical):
    """Judge the paired check measured here. Confirmation is only a submission for the existing admission."""
    if (not isinstance(proposal, dict) or proposal.get('decision') != 'TRY_HINT_FIRST' or not isinstance(proposal.get('hint'), str)
            or proposal.get('measure_first') != ['SERIAL', proposal['hint']] or not isinstance(proposal.get('fallback_order'), list)):
        raise ValueError('NO_HINT_TO_CHECK')
    serial, hint = _repeats(serial_ns), _repeats(hint_ns)
    if (not isinstance(results_identical, list) or len(results_identical) != REPEATS
            or any(flag is not True for flag in results_identical)):
        return dict(authority='NONE', decision='REFUSED_RESULTS_NOT_IDENTICAL', next='STOP_AND_INVESTIGATE', method=None)
    observed = dict(SERIAL=serial, hint=hint)
    if hint['max'] < serial['min']:
        return dict(authority='NONE', decision='HINT_CONFIRMED_SUBMIT_FOR_EXISTING_ADMISSION', method=proposal['hint'],
                    next_measure=[], observed=observed)
    return dict(authority='NONE', decision='FALLBACK_SELF_SEARCH', method=None,
                next_measure=list(proposal['fallback_order']), observed=observed)
