"""Standalone exportable curves; unsupported points are gaps, never filled."""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--results",required=True)
    p.add_argument("--reference",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    data=json.loads(Path(args.results).read_text())
    with Path(args.reference).open() as f:
        ref=list(csv.DictReader(f))
    x=np.array([float(r["R_bohr"]) for r in ref])
    e=np.array([float(r["total_energy_hartree"]) for r in ref])
    plt.rcParams.update({"font.family":["Malgun Gothic","DejaVu Sans"],"axes.unicode_minus":False,"font.size":11})
    fig,axes=plt.subplots(1,2,figsize=(13,5.1),layout="constrained")
    colors=["#1976d2","#e69100","#239760"]
    for b,color in zip(("cc-pVDZ","cc-pVTZ","cc-pVQZ"),colors):
        rows={r["R_bohr"]:r for r in data["rows"] if r.get("kind")=="curve" and r["basis"]==b}
        y=np.array([rows[r]["total_energy_hartree"] if r in rows else np.nan for r in x])
        count=int(np.isfinite(y).sum())
        axes[0].plot(x,y,".-",color=color,label=f"{b} ({count}/44)",markersize=4)
        axes[1].plot(x,y-e,".-",color=color,label=b,markersize=4)
    axes[0].plot(x,e,color="#252b35",linewidth=1.6,label="Pachucki 독립 reference")
    axes[0].axhline(-1,color="#7b8694",ls="--",lw=1,label="정확한 고립 H 두 개")
    axes[0].set(xlim=(.4,6),ylim=(-1.19,-.95),xlabel="핵간 거리 R (bohr)",ylabel="전체 BO 에너지 (hartree)",title="에너지 우물 확대 — 전자 에너지 + 1/R")
    axes[0].legend(fontsize=9,loc="upper right")
    axes[1].axhline(.001,color="#c73545",ls="--",lw=1,label="사전 비교 기준 0.001 hartree")
    axes[1].set(xscale="log",yscale="log",xlabel="핵간 거리 R (bohr)",ylabel="계산 - reference (hartree)",title="basis 오차와 미계산 영역을 분리")
    axes[1].yaxis.set_major_formatter(FuncFormatter(lambda value, position: f"{value:g}"))
    axes[1].axvspan(.4,1.4,color="#239760",alpha=.09)
    axes[1].text(.45,.004,"QZ 0.4–1.4: 수치 검사 거부\n전체 곡선 비교 미완료",fontsize=9,color="#15663d")
    axes[1].legend(fontsize=9,loc="upper right")
    for ax in axes:
        ax.grid(alpha=.18)
    fig.suptitle("고정 핵 H₂ 정적 pilot | 결합 입력 없음 | NUMERICALLY COMPARED / NOT CERTIFIED",fontsize=13)
    target=Path(args.output)
    target.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(target.with_suffix(".png"),dpi=170)
    fig.savefig(target.with_suffix(".svg"))
    svg = target.with_suffix(".svg")
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text(encoding="utf-8").splitlines())+"\n", encoding="utf-8")


if __name__=="__main__":
    main()
