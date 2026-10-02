"""Standalone scientific plot of the scoped error decomposition and fresh QZ."""
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np


def main():
    root=Path("runs/h2_numerical_cause_v1")
    summary=json.loads((root/"summary.json").read_text())
    curve=json.loads((root/"qz_curve/results.json").read_text())
    with Path("electronic_pilot/reference_pachucki_v2.csv").open() as f:
        reference=list(csv.DictReader(f))
    plt.rcParams.update({"font.family":["Malgun Gothic","DejaVu Sans"],"axes.unicode_minus":False,"font.size":10})
    fig,axes=plt.subplots(1,2,figsize=(12.4,4.8),layout="constrained")
    hp=summary["high_precision_decomposition"]
    fields=["binary64_measured_signed_asymmetry","AO_input_propagated_with_fixed_binary64_C","remaining_binary64_transform_and_assembly_component"]
    colors=["#334155","#2563eb","#d97706"]
    labels=["측정된 비대칭","AO 입력에서 전파된 성분","변환·행렬 구성 연산 성분"]
    x=np.arange(3)
    for k,(field,color,label) in enumerate(zip(fields,colors,labels)):
        axes[0].bar(x+(k-1)*.23,[abs(float(r[field])) for r in hp],width=.22,label=label,color=color)
    axes[0].axhline(1e-10,color="#be123c",ls="--",label="기존 행렬 guard 1e-10")
    axes[0].set(yscale="log",xticks=x,xticklabels=["R=0.7","R=1.0","R=1.4"],ylabel="대표 singlet coupling의 |비대칭|",title="같은 AO 값의 오차 전파 진단")
    axes[0].yaxis.set_major_formatter(FuncFormatter(lambda v,p:f"{v:.0e}"))
    axes[0].legend(fontsize=8)
    xx=np.array([float(r["R_bohr"]) for r in reference])
    yy=np.array([float(r["total_energy_hartree"]) for r in reference])
    actual={r["R_bohr"]:r["paths"][0]["total_energy_hartree"] for r in curve["rows"] if r["paths"][0]["accepted"]}
    z=np.array([actual.get(r,np.nan) for r in xx])
    axes[1].plot(xx,yy,color="#64748b",label="Pachucki reference")
    axes[1].plot(xx,z,".-",color="#2563eb",label="새 QZ 34/44",markersize=4)
    axes[1].axvspan(.4,1.3,color="#be123c",alpha=.08)
    axes[1].set(xlim=(.4,4),ylim=(-1.19,-.99),xlabel="R (bohr)",ylabel="전체 BO energy (hartree)",title="새 전체 실행: 최소점·전체 비교 미해결")
    axes[1].text(.47,-1.155,"0.4–1.3\nREFUSED",color="#9f1239",fontsize=9)
    axes[1].legend(fontsize=9)
    for ax in axes:
        ax.grid(alpha=.18)
    fig.suptitle("H₂ numerical cause isolation | 같은 finite basis | NOT CERTIFIED",fontsize=13)
    target=Path("docs/active/h2_numerical_cause_v1/diagnostic_curve.png")
    target.parent.mkdir(exist_ok=True)
    fig.savefig(target,dpi=170)


if __name__=="__main__":
    main()
