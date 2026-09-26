"""Symbolic shell composition; no trajectory measurement or D_valid access."""
from fractions import Fraction as Q

from a_reference import c1b1_outer_bootstrap as O
from a_reference import c1b1_outer_bound as B
from a_reference import c1b1_two_atom as C
from a_reference import ar2_lang2024 as L


def _tail_packet(radius,entry_upper,p_lower,w_lower,p_cap):
    env = O.ForceEnvelope()
    force,integral = env.value(radius),env.integral(radius)
    g = 2*O.ALPHA*w_lower-2*entry_upper*O.D
    v0 = w_lower/(B.MU*entry_upper)
    margin = Q(3,4)*v0*v0-2*integral/B.MU
    if g<=0 or v0<=0 or margin<=0 or radius-O.ALPHA*p_cap<L.R_MIN_BOHR:
        raise O.NotCertified('composed discrete/continuous tail escape did not close')
    impulse = integral/(v0/2)
    if B.H*force>=B.UP or impulse>=p_lower:
        raise O.NotCertified('composed zero-impulse/direction margin did not close')
    return {**O.EXECUTION_SCOPE,'scope':'tail_from_each_actual_handoff_state',
            'R_J':radius,'entry_radius_upper':entry_upper,'g_min':g,
            'force_cap':force,'force_envelope_terms':env.terms,
            'executor_remaining_impulse':Q(0),
            'executor_energy_tail_hartree':integral,
            'executor_modified_energy_tail_hartree':integral+B.H**2*force**2/(8*B.MU),
            'continuous_energy_change':Q(0),
            'continuous_tail_impulse':impulse,'continuous_radial_speed_floor':v0/2,
            'continuous_escape_margin':margin,
            'direction_error_radians':impulse/(p_lower-impulse),
            'angular_scope':'infinite_uniform_bound_not_claimed',
            'asymptote_scope':'mathematical_continuation_not_infinite_FX_execution',
            'comparison_scope':'continuous_flow_restarted_at_handoff_not_global_shadowing'}


def certify_outgoing_outer(run,p_cap):
    p_cap = B.exact(p_cap)
    q,p,snapshot = O._state(run)
    a,entry_upper = O._sqrt_down(O._norm2(q)),B.sqrt_up(O._norm2(q))
    if a<20 or p_cap<=0:
        raise O.NotCertified('outgoing outer entry must be at R >= 20')
    radius = O.zero_impulse_radius()
    if a>=radius:
        tail = O.certify_tail(run)
        shells,total,impulse_sum = [],0,Q(0)
    else:
        j = C.impulse(q,B.H/2,run.mom)
        if run.J_cache is not None and run.J_cache!=j:
            raise O.NotCertified('initial impulse cache mismatch')
        try:
            jump,_ = O._jump(run,C._kick(run.mom,run.atoms,j))
        except C.ExecutorLimitExceeded as error:
            raise O.NotCertified('initial arithmetic overflow') from error
        if O.radius_squared_increment(q,jump)<=0:
            raise O.NotCertified('initial stored drift does not increase R squared')
        p_upper,p_lower = B.sqrt_up(O._norm2(p)),O._sqrt_down(O._norm2(p))
        w_lower = O._dot(q,p)
        shells,total,impulse_sum = [],0,Q(0)
        while a<radius:
            b = min(radius,a*Q(5,4))
            c = b+O.ALPHA*p_cap+O.D
            domain = O._covered_shell(a,c)
            k = B.H*domain.force/2+O.U
            optimistic_g = 2*O.ALPHA*(w_lower-c*k)-2*c*O.D
            if optimistic_g<=0:
                raise O.NotCertified('shell search has no outward starting margin')
            n = max(1,O.residence_steps(b*b-a*a,optimistic_g))
            record = None
            # A failed search is not evidence against physics; never guess N.
            for _ in range(16):
                try:
                    record = O._shell_induction(a,b,p_upper,p_lower,w_lower,p_cap,n,b*b-a*a)
                    break
                except O.NotCertified as error:
                    if 'residence induction' not in str(error):
                        raise
                    n *= 2
            if record is None:
                raise O.NotCertified('finite shell proof-search budget exhausted')
            count = record['max_steps']
            record['entry_enclosure'] = {'radius':(a,entry_upper),'p_norm':(p_lower,p_upper),'q_dot_p_lower':w_lower}
            # Every actual first handoff has n_actual<=count. Those already at
            # the next boundary make a zero-step handoff, still in this enclosure.
            p_upper += 2*count*k
            p_lower = max(Q(0),p_lower-2*count*k)
            w_lower -= count*record['w_loss_per_step']
            entry_upper = c
            record['exit_enclosure'] = {'radius':(b,c),'p_norm':(p_lower,p_upper),'q_dot_p_lower':w_lower}
            record['zero_step_handoff_if_already_beyond_b'] = True
            shells.append(record)
            total += count
            impulse_sum += count*k
            a = b
        tail = _tail_packet(radius,entry_upper,p_lower,w_lower,p_cap)
    safe_tail_steps = O._check_overflow(run,total,impulse_sum)
    sources = ('position','momentum_update','impulse','discretization','other_arithmetic')
    finite = {}
    for key in ('energy_hartree','angular_bohr_momentum'):
        terms = {s:sum((r[key][s] for r in shells),Q(0)) for s in sources}
        finite[key] = {**terms,'total':sum(terms.values(),Q(0))}
    energy = {s:finite['energy_hartree'][s] for s in sources}
    energy['tail_potential'] = tail['executor_energy_tail_hartree']
    energy['tail_modified_correction'] = tail['executor_modified_energy_tail_hartree']-tail['executor_energy_tail_hartree']
    energy['total'] = sum(energy.values(),Q(0))
    return {**O.EXECUTION_SCOPE,'version':O.VERSION,'evidence':'analytic_outgoing_outer_shell_composition',
            'profile':dict(O.PROFILE),'model_fingerprint':B.FINGERPRINT,
            'energy_quantity':'H-h^2*|F|^2/(8*mu)',
            'initial_state':snapshot,'shells':shells,'tail':tail,
            'max_steps_to_R_J':total,'half_kick_sum_cap':impulse_sum,
            'finite_energy_hartree':finite['energy_hartree'],'energy_hartree':energy,
            'angular_bohr_momentum':finite['angular_bohr_momentum'],
            'angular_scope':'finite_entry_to_R_J_only',
            'safe_additional_FX_tail_steps_lower_bound':safe_tail_steps,
            'global_trajectory_shadowing':'not_claimed',
            'physical_energy_endpoint_correction':B.H**2*max(
                [s['force_cap'] for s in shells]+[tail['force_cap']])**2/(8*B.MU),
            'attainability':'not_proved'}


def example_report():
    """Exact analytic example and provenance, not a new measured fixture."""
    import hashlib
    from pathlib import Path
    from a_numeric import FixedPoint

    run=C.new_run(FixedPoint(96,48),B.H,(-10,0,0),(-1,0,0),(10,0,0),(1,0,0),
                  momentum_profile=FixedPoint(96,80))
    certificate=certify_outgoing_outer(run,Q(2))
    root=Path(__file__).resolve().parents[1]
    files=('a_reference/c1b1_outer_chain.py','a_reference/c1b1_outer_bootstrap.py',
           'a_reference/c1b1_outer_bound.py','a_reference/c1b1_two_atom.py',
           'a_reference/ar2_lang2024.py','a_numeric/profiles.py','a_numeric/exp.py')
    def serial(x):
        if isinstance(x,Q):
            return str(x)
        if isinstance(x,dict):
            return {k:serial(v) for k,v in x.items()}
        if isinstance(x,(tuple,list)):
            return [serial(v) for v in x]
        return x
    return serial({'version':O.VERSION,'kind':'analytic_certificate_example_not_measurement',
                   'certificate':certificate,
                   'source_sha256':{f:hashlib.sha256((root/f).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
                                    for f in files}})


if __name__=='__main__':
    import json
    import sys
    from pathlib import Path
    report=example_report()
    if len(sys.argv)==2:
        Path(sys.argv[1]).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    else:
        print(json.dumps(report,indent=2))
