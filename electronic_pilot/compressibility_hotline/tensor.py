"""Number-sector Schmidt diagnostic, without a Tensor Network executor."""
import itertools
import time
import numpy as np
from scipy.linalg import eigh


def unpack(v, m=28):
    i, j = np.triu_indices(m)
    w = np.zeros((m, m), complex)
    w[i, j] = v / np.where(i == j, 1, np.sqrt(2))
    w[j, i] = w[i, j]
    return w


def pack(w):
    i, j = np.triu_indices(len(w))
    return w[i, j] * np.where(i == j, 1, np.sqrt(2))


def gauges(a, b):
    c = b['c']
    energies = np.diag(c.T @ a['h'] @ c)
    order = np.argsort(energies, kind='stable')
    positions, r = eigh(-c.T @ a['dipoles'][2] @ c)
    for j in range(28):
        if r[np.argmax(abs(r[:, j])), j] < 0:
            r[:, j] *= -1
    return {'original_MO':np.eye(28), 'energy_MO':np.eye(28)[:, order],
            'position_z_eigenbasis':r}, dict(energy_order=order.tolist(),
            energy_duplicates_original=bool(np.array_equal(order, np.arange(28))),
            positions_z=positions.tolist(),
            MO_S_orthogonality_max=float(np.max(abs(c.T @ a['s'] @ c-np.eye(28)))))


def coordinates(v, data, c, r):
    if data['electrons'] == 1:
        return r.T @ c.T @ data['s'] @ v
    return r.T @ unpack(v) @ r


def original(x, data, c, r):
    return c @ r @ x if data['electrons'] == 1 else pack(r @ x @ r.T)


def decompose(x, cut):
    if x.ndim == 1:
        weights = np.array([np.linalg.norm(x[:cut]), np.linalg.norm(x[cut:])])
        return dict(one=True, x=x, cut=cut, singular=np.sort(weights)[::-1], weights=weights)
    u, s, vh = np.linalg.svd(x[:cut, cut:], full_matrices=False)
    ll, rr = x[:cut,:cut], x[cut:,cut:]
    weights = np.array([np.linalg.norm(ll), np.linalg.norm(rr)])
    singular = np.sort(np.r_[weights, s, s])[::-1]
    # Cross-sector matrix is [[0,X],[-X.T,0]], so each s occurs twice.
    return dict(one=False, x=x, cut=cut, u=u, s=s, vh=vh, weights=weights,
                singular=singular)


def truncate(d, chi):
    x, k = d['x'], d['cut']
    z = np.zeros_like(x)
    if d['one']:
        indices = np.argsort(-d['weights'], kind='stable')[:min(chi,2)]
        for i in indices:
            if i == 0:z[:k] = x[:k]
            else:z[k:] = x[k:]
        payload = sum((k if i == 0 else len(x)-k)*16+8 for i in indices)
        used = int(sum(d['weights'][i] > 0 for i in indices))
        return z, payload, used
    best = (-1, None)
    # Complete spin pairs only: never discard one member of a degenerate pair.
    for left, right in itertools.product([0,1], repeat=2):
        if left+right > chi:continue
        rank = min(len(d['s']), (chi-left-right)//2)
        weight = left*d['weights'][0]**2+right*d['weights'][1]**2+2*sum(d['s'][:rank]**2)
        if weight > best[0]:best = (weight,(left,right,rank))
    left,right,rank = best[1]
    if left:z[:k,:k] = x[:k,:k]
    if right:z[k:,k:] = x[k:,k:]
    cross = (d['u'][:,:rank]*d['s'][:rank]) @ d['vh'][:rank]
    z[:k,k:] = cross
    z[k:,:k] = cross.T
    m = len(x)
    payload = left*(k*(k+1)//2*16+8)+right*((m-k)*(m-k+1)//2*16+8)
    payload += rank*(m*16+8)
    used = int(left+right+2*rank)
    return z, payload, used


def evolve(v, d, dt):
    return d['u'] @ (np.exp(-1j*d['e']*dt)*(d['u'].T @ d['s'] @ v))


def density(v, d):
    if d['electrons'] == 1:return np.outer(v,v.conj()).real
    w = unpack(v)
    return (d['c'] @ (2*w@w.conj().T) @ d['c'].T).real


def metrics(ref, test, d):
    nr = float(np.vdot(ref,d['s']@ref).real)
    nt = float(np.vdot(test,d['s']@test).real)
    delta = test-ref
    overlap = abs(np.vdot(ref,d['s']@test))**2
    fidelity = float(overlap/(nr*nt)) if nt > 0 else 0.
    return dict(state_error_S=float(np.sqrt(max(0,np.vdot(delta,d['s']@delta).real))),
                norm_error=abs(nt-nr), fidelity=fidelity,
                projector_distance=float(np.sqrt(max(0,2*(1-min(1,fidelity))))),
                energy_error=float(abs(np.vdot(test,d['h']@test)-np.vdot(ref,d['h']@ref))),
                density_error=float(np.max(abs(density(test,d)-density(ref,d)))),
                dipole_error=float(max(abs(np.vdot(test,op@test)-np.vdot(ref,op@ref)) for op in d['dipoles'])))


def diagnostic(data, gs, c, protocol):
    rows, reconstructions, costs = [], [], []
    sh,sv = eigh(data['s']); inv = (sv/np.sqrt(sh))@sv.T
    op_energy = float(max(abs(eigh(inv@data['h']@inv,eigvals_only=True))))
    op_dipole = float(max(max(abs(eigh(inv@op@inv,eigvals_only=True))) for op in data['dipoles']))
    for name, initial in zip(protocol['states'],data['states']):
        for t in protocol['times_atomic']:
            v = evolve(initial,data,t)
            future = evolve(v,data,protocol['future_delta_atomic'])
            for gauge,r in gs.items():
                x = coordinates(v,data,c,r)
                for cut in protocol['cuts_spatial_orbitals']:
                    wall,cpu = time.perf_counter(),time.process_time()
                    d = decompose(x,cut)
                    costs.append(dict(state=name,time=t,gauge=gauge,cut=cut,
                                      decompose_cpu=time.process_time()-cpu,
                                      decompose_wall=time.perf_counter()-wall))
                    s = d['singular']; q = s*s; q = q/q.sum()
                    entropy = float(-sum(q[q>0]*np.log2(q[q>0])))
                    rank = int(sum(s > protocol['rank_relative_threshold']*s[0]))
                    for chi in protocol['chi']:
                        cpu = time.process_time(); z,payload,used = truncate(d,chi)
                        test = original(z,data,c,r); encode_cpu = time.process_time()-cpu
                        cpu = time.process_time(); met = metrics(v,test,data)
                        observable_cpu = time.process_time()-cpu
                        cpu = time.process_time(); ft = evolve(test,data,protocol['future_delta_atomic'])
                        evolution_cpu = time.process_time()-cpu
                        fm = metrics(future,ft,data)
                        # Triangle/operator bound for unnormalized quadratic observables.
                        eps = met['state_error_S']; factor = eps*(2*np.sqrt(np.vdot(v,data['s']@v).real)+eps)
                        eb = float(op_energy*factor)
                        db = float(op_dipole*factor)
                        row = dict(state=name,time=t,gauge=gauge,cut=cut,chi=chi,chi_used=used,
                                   singular_values=s.tolist(),rank_at_1e_12=rank,entropy_bits=entropy,
                                   discarded_weight=float(np.linalg.norm(x-z)**2),
                                   discarded_norm=float(np.linalg.norm(x-z)),
                                   unconstrained_discarded_weight=float(sum(s[chi:]**2)),
                                   dense_payload_bytes=int(v.nbytes),factor_payload_bytes=payload,
                                   shared_gauge_bytes=int(r.nbytes+c.nbytes),
                                   factor_metadata_minimum_bytes=32,encode_cpu=encode_cpu,
                                   observable_cpu=observable_cpu,evolution_cpu=evolution_cpu,
                                   metrics=met,future_metrics=fm,
                                   energy_error_bound=eb,dipole_error_bound=db,
                                   future_state_error_bound=eps,
                                   bound_status='ANALYTIC_REAL_ARITHMETIC_BOUND / NUMERICAL_EVALUATION_NOT_INTERVAL_CERTIFIED')
                        row['meets_inherited_tolerances'] = bool(max(met['state_error_S'],fm['state_error_S'])<=protocol['state_tolerance'] and
                            max(met['energy_error'],met['density_error'],met['dipole_error'],fm['energy_error'],fm['density_error'],fm['dipole_error'])<=protocol['observable_tolerance'])
                        rows.append(row); reconstructions.append(test)
    return rows,np.array(reconstructions),costs
