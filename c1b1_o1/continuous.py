"""Continuous Hamiltonian radial quadrature, distinct from discrete KDK.

Only planar inbound scattering with one accessible simple turning point.
No interval-certified error claims. Doubles are never used in primary integrals.
"""
import mpmath as mm

class Unresolved(ValueError):
    pass

def principal(x):
    return mm.atan2(mm.sin(x), mm.cos(x))

def turning_point(g, r0, dps):
    # Descend from actual start, never choose an inaccessible inner root.
    previous=r0
    for i in range(1,4097):
        r=r0-(r0-mm.mpf('2.4'))*i/4096
        if g(r)<=0:
            lo,hi=r,previous
            break
        previous=r
    else:
        raise Unresolved('no turning bracket above public r_min')
    for _ in range(int(dps*3.5)+32):
        middle=(lo+hi)/2
        if g(middle)>0: hi=middle
        else: lo=middle
    rm=(lo+hi)/2
    if mm.diff(g,rm)<=0:
        raise Unresolved('non-simple/inaccessible turning point')
    return rm

def scatter(V,mu,q,p,r_exit,dps):
    with mm.workdps(dps):
        q,p=[mm.mpf(x) for x in q],[mm.mpf(x) for x in p]
        r0=mm.sqrt(sum(x*x for x in q))
        if q[0]*p[0]+q[1]*p[1]>=0 or r_exit<r0:
            raise Unresolved('requires inbound start and matched outbound radius')
        H=sum(x*x for x in p)/(2*mu)+V(r0)
        L=q[0]*p[1]-q[1]*p[0]
        if L<0: raise Unresolved('negative L not supported in V1')
        g=lambda r: 2*mu*(H-V(r))-L*L/(r*r)
        rm=turning_point(g,r0,dps)
        derivatives=[mm.diff(g,rm,n)/mm.factorial(n) for n in range(1,7)]
        def normalized(u):
            dr=u*u
            # Analytic endpoint; Taylor region shrinks with precision. Six terms
            # give O(dr^6) normalized error, well below each quadrature target.
            if abs(dr)<mm.power(10,-dps/3):
                z=sum(a*dr**i for i,a in enumerate(derivatives))
            else:
                z=g(rm+dr)/dr
            if z<=0: raise Unresolved('radial integrand nonpositive')
            return 2/mm.sqrt(z)
        def leg(r,kind):
            umax=mm.sqrt(r-rm)
            fun=lambda u: normalized(u)*(L/(rm+u*u)**2 if kind=='angle' else mu)
            # Geometric subdivisions also resolve the near-barrier bottleneck.
            points=[0]+[umax*i/16 for i in range(1,17)]
            value,error=mm.quad(fun,points,error=True,maxdegree=10)
            if not mm.isfinite(value) or error>mm.power(10,-dps/2):
                raise Unresolved('quadrature error estimate exceeds sealed target')
            return value,error
        a0,e0=leg(r0,'angle'); a1,e1=leg(r_exit,'angle')
        t0,et0=leg(r0,'time'); t1,et1=leg(r_exit,'time')
        theta=a0+a1
        initial_direction=mm.atan2(p[1],p[0])
        radial=mm.sqrt(g(r_exit)); tangential=L/r_exit
        direction=principal(theta+mm.atan2(tangential,radial)+mm.atan2(q[1],q[0]))
        po=[radial*mm.cos(theta)-tangential*mm.sin(theta),radial*mm.sin(theta)+tangential*mm.cos(theta)]
        reconstructed_H=sum(x*x for x in po)/(2*mu)+V(r_exit)
        reconstructed_L=r_exit*(mm.cos(theta)*po[1]-mm.sin(theta)*po[0])
        result=dict(r_min=rm,chi=principal(direction-initial_direction),sweep=theta,
                    direction=direction,time=t0+t1,H=H,L=L,p_out_x=po[0],p_out_y=po[1],
                    energy_reconstruction_error=abs(reconstructed_H-H),
                    angular_reconstruction_error=abs(reconstructed_L-L),
                    quadrature_error=max(e0,e1,et0,et1),root_residual=abs(g(rm)))
        return {k:mm.nstr(v,dps) for k,v in result.items()}
