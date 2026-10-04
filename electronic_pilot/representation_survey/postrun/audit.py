"""Independent report collision check against saved full matrix evolution."""
import numpy as np
from scipy.linalg import eigh, expm
from ..verify import independent_density


def collision_record(record,payload_plus,payload_minus,data,times,tolerance=1e-9):
    s,h=data["s"],data["h"]
    w,q=eigh(s);root=(q*np.sqrt(w))@q.T;inverse=(q/np.sqrt(w))@q.T
    diffs=[];density_diffs=[]
    for t in times[1:]:
        U=expm(-1j*(inverse@h@inverse)*t)
        a,b=[inverse@U@root@data["states"][j] for j in [2,3]]
        density_diffs.append(float(np.max(abs(independent_density(a,data)-independent_density(b,data)))))
        diffs.append(float(max(abs(np.vdot(a,op@a).real-np.vdot(b,op@b).real) for op in data["dipoles"])))
    equal=payload_plus==payload_minus
    future=max(diffs+density_diffs)
    expected="REJECTED" if equal and future>1e-6 else "UNRESOLVED"
    return dict(PASS=(record["summary_payload_equal"]==equal and record["authoritative"]==expected and
                       abs(record["future_dipole_difference_max"]-max(diffs))<=tolerance and
                       abs(record["future_density_kernel_max"]-max(density_diffs))<=tolerance),
                independent_future_dipole_max=max(diffs),independent_future_density_max=max(density_diffs),
                authoritative=expected,summary_payload_equal=equal)
