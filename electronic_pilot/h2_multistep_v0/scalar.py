"""Decimal80 Velocity Verlet with unchanged dt/h/mass conventions."""
from decimal import Decimal as D,localcontext
from electronic_pilot.h2_nuclear_v0.scalar import finite,individual,force,energy,geometry,PRECISION,DT,H

def domain(r):
    r=finite(r)
    if not D('1.2')<=r<=D('1.6'):raise ValueError('R outside local Pilot domain')
    return r

def drift(previous,mass):
    with localcontext() as ctx:
        ctx.prec=PRECISION
        r=domain(previous['R']);p=finite(previous['P']);f=finite(previous['F']);mass=finite(mass)
        if mass<=0:raise ValueError('nonpositive mass')
        half=p+D(DT)*f/2;next_r=domain(r+D(DT)*half/(mass/2))
        return dict(P_half=str(half),R=str(next_r),requested_geometries={
            'left':str(next_r-D(H)),'right':str(next_r+D(H))})

def finish(previous,half,left,right,mass):
    for label,row in zip(('left','right'),(left,right)):
        if row['requested_R']!=half['requested_geometries'][label]:raise ValueError('stencil identity')
        energy(row)
    with localcontext() as ctx:
        ctx.prec=PRECISION
        f=force(left,right);p=finite(half['P_half'])+D(DT)*f/2;r=domain(half['R'])
        return dict(R=str(r),P=str(p),F=str(f),P_half=half['P_half'],dt=DT,h=H,
            mu=str(finite(mass)/2),nuclei=individual(r,p),points=[left,right],
            requested_geometries=half['requested_geometries'],state_status='SPECULATIVE',
            center_geometry=geometry(r),center_geometry_status='SERIALIZATION_ONLY_NOT_ELECTRONICALLY_EVALUATED',
            energy_conservation_tolerance=None)

def diagnostic(state,center,mass,c0_H):
    if center['requested_R']!=state['R']:raise ValueError('diagnostic center identity')
    with localcontext() as ctx:
        ctx.prec=PRECISION
        p=finite(state['P']);k=p*p/finite(mass);e=energy(center);total=e+k
        return dict(E_center=str(e),K=str(k),H_total=str(total),delta_H_from_C0=str(total-finite(c0_H)),
            status='MEASURED',energy_conservation_tolerance=None,
            actual_geometry=center['geometry'],mass_uncertainty_propagated=False)
