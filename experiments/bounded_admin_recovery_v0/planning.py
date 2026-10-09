"""REVIEW_ONLY contract checks. No authority creation, repair, retry or network.

authority is an external trust boundary: an already independently verified
initial ledger and receipt pins. This module does not authenticate that boundary
or verify signatures. Untrusted package data cannot be used as authority.
All outputs, including success, set execution_authorized=False.
"""
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from .package_gate import digest, sha, strict_json

ROLES = ('provenance', 'preservation', 'classification', 'budget', 'control', 'package', 'approval', 'ledger')
BOUND = ('allocation_id', 'allocation_start_utc', 'original_zip_sha256', 'failed_evidence_zip_sha256',
         'instance_id', 'machine_id', 'country', 'caps')


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def integer(obj, key, *, positive=False):
    value = obj[key]
    require(type(value) is int and value >= (1 if positive else 0), 'UNKNOWN_OR_INVALID_USAGE:' + key)
    return value


def money(value):
    require(isinstance(value, str), 'MONEY_STRING_REQUIRED')
    result = Decimal(value)
    require(result.is_finite() and result >= 0, 'INVALID_MONEY')
    return result


def utc(value):
    result = datetime.fromisoformat(value)
    require(result.tzinfo is not None and result.utcoffset().total_seconds() == 0, 'UTC_REQUIRED')
    return result


def exact(a, b):
    # JSON equality must preserve types: True must not satisfy the integer 1.
    import json
    return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False)


def review_recovery(request, *, authority):
    result = dict(status='REFUSED', execution_authorized=False, automatic_retry=False,
                  historical_status='REMOTE_TEST_GATE_FAILED / UNRESOLVED', reasons=[])
    try:
        initial = authority['initial']
        policy_bytes = Path(__file__).with_name('protocol.json').read_bytes()
        require(digest(authority['policy_sha256']) and sha(policy_bytes) == authority['policy_sha256'],
                'EXTERNALLY_PINNED_POLICY_REQUIRED')
        policy = strict_json(policy_bytes)
        require(exact(initial['caps'], policy['caps']), 'INITIAL_CAPS_MUST_MATCH_FROZEN_POLICY')
        require(set(request['receipts']) == set(ROLES) == set(authority['receipt_pins']), 'ALL_EXTERNAL_RECEIPTS_REQUIRED')
        receipts = {}
        for role in ROLES:
            body = request['receipts'][role]
            require(isinstance(body, bytes) and digest(authority['receipt_pins'][role])
                    and sha(body) == authority['receipt_pins'][role], 'EXTERNAL_RECEIPT_PIN:' + role)
            obj = strict_json(body)
            require(obj['role'] == role and obj['verdict'] == 'VERIFIED', 'VERIFIED_ROLE_REQUIRED:' + role)
            require(all(exact(obj[k], initial[k]) for k in BOUND), 'INITIAL_BINDING_RESET_OR_MISMATCH:' + role)
            receipts[role] = obj
        origin, preservation, error, budget, control, package, approval, ledger = (receipts[k] for k in ROLES)
        require(origin['existing_sealed_origin'] is True and origin['verifier_id']
                and origin['verifier_id'] != authority['package_author_id'], 'INDEPENDENT_EXISTING_ORIGIN_REQUIRED')
        require(preservation['originals_immutable'] is True, 'ORIGINALS_NOT_PRESERVED')
        require(error['error_kinds'] == ['MISSING_EXISTING_SEALED_DEPENDENCY']
                and integer(error, 'nonpasses', positive=True) == integer(error, 'attributed_nonpasses')
                and error['nonpasses'] <= 320
                and integer(error, 'unclassified') == 0, 'FORBIDDEN_MIXED_OR_UNKNOWN_ERROR')
        require(approval['explicit_human_approval'] is True and approval['approval_reference']
                and approval['policy_sha256'] == authority['policy_sha256']
                and utc(approval['approved_utc']) < utc(initial['first_attempt_utc']), 'PRIOR_EXPLICIT_SCOPE_APPROVAL_REQUIRED')
        require(type(approval['max_admin_recoveries']) is int and approval['max_admin_recoveries'] == 1
                and type(approval['max_full_reruns']) is int and approval['max_full_reruns'] == 1, 'MAX_COUNTS_MUST_BE_ONE')
        require(integer(ledger, 'admin_recoveries_started') == 0 and integer(ledger, 'full_reruns_started') == 0
                and integer(ledger, 'prior_failed_attempts') == initial['prior_failed_attempts'], 'COUNTS_EXHAUSTED_OR_RESET')
        require(package['status'] == 'COMPLETE_DECLARED_ONLY' and package['separately_sealed'] is True
                and package['computation_criteria_authority_unchanged'] is True, 'PACKAGE_SEAL_OR_SCOPE_INVALID')
        require(package['added_files'] == origin['files'] == approval['recovery_scope'] and bool(origin['files'])
                and all(digest(v) for v in origin['files'].values()), 'EXACT_EXISTING_ADDITIONS_REQUIRED')
        require(digest(package['zip_sha256']) and digest(package['inventory_sha256'])
                and package['zip_sha256'] == approval['candidate_zip_sha256']
                and package['inventory_sha256'] == approval['candidate_inventory_sha256'], 'CANDIDATE_APPROVAL_BINDING')
        require(type(package['expected_tests']) is int and package['expected_tests'] == 320
                and package['test_files'] == initial['test_files'], 'FULL_ORIGINAL_320_SCOPE_REQUIRED')
        require(control['actual'] == 'running' and control['guardian'] == 'ARMED'
                and control['supervisor'] == 'CONTROL_OK' and control['outside_guest'] is True
                and control['stop_control_verified'] is True and control['cumulative_caps_enforced'] is True,
                'CONTROL_OR_CUMULATIVE_ENFORCEMENT_NOT_VERIFIED')
        elapsed = integer(budget, 'elapsed_ms')
        for role in ('budget', 'control', 'ledger'):
            age_ms = (utc(authority['review_utc']) - utc(receipts[role]['observed_utc'])).total_seconds() * 1000
            require(0 <= age_ms <= 5000, 'CURRENT_EXTERNAL_OBSERVATION_REQUIRED:' + role)
        observed_age_ms = (utc(budget['observed_utc']) - utc(initial['allocation_start_utc'])).total_seconds() * 1000
        require(observed_age_ms == elapsed, 'ELAPSED_OR_INITIAL_CLOCK_RESET')
        # Include the time since the last externally verified budget observation.
        elapsed += int((utc(authority['review_utc']) - utc(budget['observed_utc'])).total_seconds() * 1000)
        used_wall = integer(budget, 'compute_wall_used_ms'); used_cpu = integer(budget, 'aggregate_cpu_used_ms')
        repair = integer(budget, 'reserve_repair_ms', positive=True)
        repair_cpu = integer(budget, 'reserve_repair_cpu_ms', positive=True)
        suite_wall = integer(budget, 'reserve_suite_wall_ms', positive=True)
        suite_cpu = integer(budget, 'reserve_suite_cpu_ms', positive=True)
        recovery = integer(budget, 'reserve_recovery_ms', positive=True)
        require(used_wall <= elapsed, 'COMPUTE_WALL_EXCEEDS_ALLOCATION_AGE')
        require(used_wall + repair + suite_wall <= 120000 and used_cpu + repair_cpu + suite_cpu <= 120000,
                'CUMULATIVE_COMPUTE_CAP')
        finish = elapsed + repair + suite_wall + recovery
        deadline = integer(control, 'handoff_deadline_ms', positive=True)
        require(deadline <= min(420000, integer(initial, 'handoff_deadline_ms', positive=True))
                and finish <= deadline and finish + 180000 <= 600000, 'RECOVERY_AND_STOP_HEADROOM')
        require(integer(budget, 'memory_peak_bytes') <= 536870912 and integer(budget, 'cpu_affinity_count') == 1,
                'MEMORY_OR_CPU_SCOPE')
        rate = money(budget['hourly_usd']); spent = money(budget['running_fee_used_usd'])
        require(rate <= Decimal('0.25') and spent >= rate * Decimal(elapsed) / Decimal(3600000), 'RATE_OR_UNDERCOUNTED_FEE')
        projected = spent + rate * Decimal(repair + suite_wall + recovery + 180000) / Decimal(3600000)
        require(projected <= Decimal('0.05'), 'ORIGINAL_RUNNING_FEE_CAP')
        result.update(status='STATIC_REVIEW_CANDIDATE', remaining_compute_wall_ms=120000-used_wall,
                      remaining_aggregate_cpu_ms=120000-used_cpu, projected_running_fee_usd=str(projected),
                      required_next='EXTERNAL_AUTHORITY_AUTHENTICATION_AND_APPEND_ONLY_COUNT_RESERVATION; NO_EXECUTION_BY_THIS_MODULE')
    except (KeyError, TypeError, ValueError, ArithmeticError, OSError) as error:
        result['reasons'].append(str(error))
    return result


def review_completion(receipt, expected_sha256, expected_case_ids):
    """Checks a pre-verified raw/JUnit receipt, never asserts independent verification."""
    result = dict(status='REFUSED', execution_authorized=False, reasons=[])
    try:
        require(isinstance(receipt, bytes) and digest(expected_sha256) and sha(receipt) == expected_sha256,
                'EXTERNAL_RESULT_PIN')
        obj = strict_json(receipt)
        require(obj['role'] == 'full_rerun' and obj['verdict'] == 'VERIFIED', 'RESULT_ROLE')
        expected = set(expected_case_ids)
        require(len(expected_case_ids) == len(expected) == 320, 'EXPECTED_EXACT_320_IDS')
        cases = obj['cases']; ids = [c['id'] for c in cases]
        require(len(cases) == len(set(ids)) == 320 and set(ids) == expected
                and all(c['outcome'] == 'passed' for c in cases), 'FULL_SUITE_FAIL_ERROR_SKIP_ZERO_REQUIRED')
        require(obj['benchmark_complete'] is True and type(obj['new_physics_calls']) is int
                and obj['new_physics_calls'] == 0 and type(obj['gpu_calls']) is int and obj['gpu_calls'] == 0,
                'BENCHMARK_AND_NO_COMPUTE_SCOPE')
        result['status'] = 'STATIC_RESULT_CONTRACT_MATCH'
    except (KeyError, TypeError, ValueError) as error:
        result['reasons'].append(str(error))
    return result
