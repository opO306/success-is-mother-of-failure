# Atomic / Electronic Matter Foundation — Electronic Sector Panel V1

2026-10-04. **Static finite-basis panel P1–P5 PASS / NOT CERTIFIED / production foundation 미승인.**
두 기기 재현은 **PARTIAL: 같은 저장 AO 입력부터 네 대표 sector 계산을 재현**했다.
노트북의 새 적분 생성까지 포함한 전체 backend 재현은 UNAVAILABLE / NOT RUN이다.
전자·핵 dynamics, excited-state/history, density/wavefunction 상태 선택은 이번 작업에서 구현하지 않았다.

기존 판정은 그대로다: **H₂ static feasibility PARTIAL / QZ short-R UNSUPPORTED·UNRESOLVED / QZ sampled minimum UNRESOLVED.**
이번 TZ 표본이 통과했다고 기존 QZ 결과나 A foundation 승인 상태를 승격하지 않는다.

## ELECTRON COUNT NECESSITY

봉인한 cc-pVTZ·고정 핵·비상대론 Coulomb 식의 같은 geometry에서 N_e=1/2를 비교했다.
각 R에서 S/h/ERI의 실제 binary64 bytes와 SHA-256이 세 sector 사이에 동일하다.
공간 orbital M=28을 전부 유지하며, 한 전자는 차원28, 두 전자 singlet은406이다.
다섯 점에서 total energy 차이가 최소0.470591855970 hartree여서 P1 PASS다.
핵 정보만으로 어느 전자 수의 문제인지 정해지지 않는다. 이 pilot은 N_e를 authoritative input으로 선택했다.

아래 값은 E_e+V_NN, hartree다. 이름은 보고 label이며 solver 입력으로 전달하지 않는다.

| R bohr | N_e=1 doublet (H₂⁺ label) | N_e=2 singlet | N_e=2 triplet |
|---|---:|---:|---:|
| 0.8 | -0.3028257153454701 | -1.0154003699251604 | -0.4435441100896407 |
| 1.4 | -0.5693764823721944 | -1.1723345935442993 | -0.7793552744692077 |
| 2.0 | -0.6022444255722408 | -1.1361716888638451 | -0.8955798661928118 |
| 4.0 | -0.5442580387692789 | -1.0148498947395685 | -0.9926873477199145 |
| 20.0 | -0.4998157048609442 | -0.9996196559748818 | -0.9996196559748818 |

고립 Z=1/N_e=1 control: M=14, 차원14, E_H=-0.4998098113018429 hartree.

## SPIN SECTOR NECESSITY

같은 핵과 N_e=2에서도 공간 대칭 singlet M(M+1)/2=406과 공간 반대칭 triplet M(M−1)/2=378은 서로 다른 허용 공간이다.
동일한 ordered-product Hamiltonian을 정규화된 대칭/반대칭 basis로 투영했다.
첫 네 거리의 singlet/triplet energy 차이는0.571856259836/0.392979319075/0.240591822671/0.022162547020 hartree다. P2 PASS.
R20에서는 표시된 binary64 에너지가 같다. 해리 방향의 degeneracy는 sector가 같다는 뜻이 아니다.

triplet378은 하나의 spin projection에 대응하는 전체 공간 반대칭 차원이다.
이 spin-free Hamiltonian의 세 triplet projection은 동등하므로 차원을1134로 곱해 보고하지 않는다.
doublet의 두 spin projection도 같은 이유로 공간 차원을 두 배로 세지 않는다.
어느 sector를 선택한 static 문제인지 지정하는 데 sector 구분이 필요하다.
모든 sector를 포함한 완전한 Hamiltonian 자체는 핵·N_e·법칙으로 정의할 수 있다.
세계에서 spin을 어떤 자료형으로 저장할지, 항상 global ground state를 고를지 결정한 것은 아니다.

## TOTAL CHARGE: AUTHORITATIVE OR DERIVED

Q/e=ΣZ_i−N_e를 evaluator 호출 전에 검증한다. 고립 H0, 두 핵 N_e=1은+1, 두 핵 N_e=2는0이다.
ghost는 basis center이며 핵전하·핵반발에 기여하지 않는다. 모든 backend charge/multiplicity/좌표와 별도 장부가 대응한다.
canonical API는 독립 charge/Q를 받지 않는다. 진단용 전하 assertion에서도 Z=(1,1),N_e=2,Q=+1을 REFUSED로 거부하는 실제 시험이 통과했다. P3 PASS.
이 isolated pilot에서는 Q를 중복 authoritative state로 저장할 필요가 없다.
다른 계약에서 Q를 선택해 N_e를 유도할 수 있다는 대수적 가능성과 이번 N_e-authoritative 선택을 구분한다.

## NO-BOND-ID CHECK

물리 입력 key는 nuclei(Z,position_bohr),ghost_centers_bohr,electrons,sector,basis,law뿐이다.
Z=1만 지원하는 좁은 pilot이다. H 문자열은 Z=1의 원소/basis 식별이며 H₂/H₂⁺/bond ID는 없다.
report case_key는 계산이 끝난 뒤 추가한다. bond_id/molecule_id/reaction_id 및 독립 Q key 주입은 거부했다.
같은 kinetic+nuclear Coulomb+electron Coulomb 식에 Ne/공간 교환 대칭만 바뀐다. P4 AUTHOR SOURCE/CONCEPT REVIEW PASS.
이 판정은 외부 독립 physics audit 승인과 구별한다.

## ASYMPTOTIC CONTROLS

실행 전 R=[0.8,1.4,2,4,20] bohr와 H+ghost-H의 R4/20을 고정했다. 총18개 계산이며 추가 점·basis는 없다.
R20의 fragment 차이 절대값≤1e-4 hartree, R4보다 fragment에 가까움, R20 ghost 차이≤1e-7을 사전 봉인했다.

| 비교 | R4 차이 hartree | R20 차이 hartree |
|---|---:|---:|
| N_e=1 total−E_H | -0.0444482274674360 | -5.89355910136e-6 |
| singlet total−2E_H | -0.0152302721358828 | -3.33711960288e-8 |
| triplet total−2E_H | +0.0069322748837712 | -3.33711960288e-8 |

ghost fragment energy R4=-0.4998112994766909, R20=-0.4998098113018434.
R4 ghost−isolated H=-1.488174848e-6, R20=-4.996003611e-16 hartree다.
단순 basis sharing과 sector 변화는 다섯 geometry의 같은 AO 대응 및 ghost controls로 구분했다. P5 PASS.
R20은 유한 거리이고 continuum/basis exactness·무한 거리 극한·bound는 인증하지 않았다.

## DUAL-MACHINE REPRODUCIBILITY

본체 로컬 WSL Ubuntu24.04: Python3.12.3, Psi4 1.3.2/Libint1.2.1, NumPy1.26.4, SciPy1.11.4.
AO는 binary64, full-span generalized-h 좌표·모든 ERI 수축은 longdouble64 유효 비트(nmant63), eigensolve는 binary64다.
노트북 DESKTOP-0EASI0F: RAM7,968,595,968 bytes, Windows11 build22631, Python3.12.7, NumPy2.5.3, SciPy1.18.1, longdouble53 유효 비트(nmant52).
remote preflight에서 AO backend·NumPy/SciPy·실행 가능한 WSL 배포판이 없음을 확인했다.
별도 `C:\Users\zun24\ElectronicSectorPanelV1\venv`에 NumPy/SciPy만 설치했다.

같은 source SHA와 저장 binary64 AO 입력을 봉인해 LAN192.168.0.2→192.168.0.4로 전송했다.
bundle SHA256 `b24a25314d7607c4cab9ed4603165b806f45248f6a95e35c178704dd6e1edab7` 일치 후 worker1로 H와 R1.4의 세 sector를 재계산했다.
임시 LAN 전송 server는 종료했다. 모든 representative의 차원·Ne·sector·AO hash·수치 검사 PASS, exit0이다.
에너지 차이 H1.11e-16 / N_e1 2.22e-16 / singlet1.33e-15 / triplet2.22e-15 hartree로 봉인된1e-9 이내다.
노트북 별도 product-action residual 최대1.33e-14 hartree, exchange parity error0.
**부분 saved-AO 환경 재현 PASS. Fresh AO 포함 전체 두 기기 재현 NOT RUN. 독립 physics checker·bitwise 결정론·A 실행기 승인 아님.**

## STATE MINIMALITY RESULT

선택한 고정 핵 static sector 문제의 최소 입력 후보는 **핵 Z/위치 + N_e + spin/electronic sector + Hamiltonian/basis 계약**이다.
Q는 derived이고 ground-state electronic solution은 그 문제를 푼 출력이다.
basis·좌표·solver는 이 finite pilot의 계산 명세이지 최종 세계 상태에 그대로 넣기로 승인한 것은 아니다.
한 sector의 lowest numerical root를 매번 다시 선택하는 가정을 최종 A law로 채택하지 않았다.

본체18/18 numerical accepted, 기존 TZ accepted control R1.4/2/20 차이 최대1.04805e-13 hartree.
같은 원래 TZ의 exponents/원래 contraction coefficient와 sphericalM28을 bytes가 아닌 값별 exact equality로 확인했다.
R0.8의 과거 libcint/binary64 변환 거부는 보존했고, 새 Libint/full-generalized-h/extended 수축에서만 새 결과를 얻었다.
matrix Hermiticity max2.78272e-11≤1e-10, eigen residual max1.67590e-13≤1e-9.
별도 full-product action18/18 PASS, residual max1.96637e-13, 실제 spin 교환 대칭 확인.
이 작용 검사는 같은 저장 적분을 공유하는 author checker다. AO 정확도·엄밀 최저근·외부 감사·continuum 인증은 아니다.
본체 전체 wall41.366초, point peak RSS 최대134.543MiB. Vast/GPU/성능 최적화 없음.

## UNRESOLVED

오차 장부: 비상대론·고정 핵·spin-free 모델의 생략; finite contracted TZ basis 오차;
binary64 AO/좌표/eigensolver 및 extended contraction의 반올림; 허용오차 안의 잔차는 모두 남아 있다.
공간 전체를 유지한 직접 eigensolve이므로 iteration_count=null이며 root hint·warm start·cutoff·행렬 평균화는 없다.
reference control 대응은 같은 finite 문제 수치 확인이다. continuum reference 오차를 닫지 않는다.
정확한 원자−0.5를 solver tuning에 넣지 않았다. E_H와−0.5의 차이0.000190188698 hartree는 finite basis 잔여의 설명에만 사용한다.

설계 구상 일치성은 자동 시험과 별도로 검토했다. 화학 이름이 법칙을 선택하지 않고 전자 수·교환 대칭이 상태 공간을 선택한다.
한계: nuclei+Ne+sector가 real electronic state/history를 충분히 정한다는 결론은 아직 없고,
wavefunction/density 저장, excited states, 전자 시간 이력, nonadiabatic dynamics는 미평가다.
물리 형성·포획·force trajectory·전자전달·반응·생명 증거는 이번 결과에 없다.

Windows 관련111 passed(1.55초), WSL 관련120 passed(9.82초), 신규39. 실패/error/실제skip0.
새 의미 결함 주입은 Ne/sector/charge/차원/좌표/잔차/핵반발/누락·중복·AO 대응을 검사한다.
첫 준비 실행의 runs parent 누락, Windows longdouble에 부적합한 unit algebra bound의2 failed/17 passed,
잘못된 시험 파일명으로 인한 collection error(no tests ran)를 지우지 않고 별도 증거로 보존했다.
unit algebra 비교만32×해당 dtype epsilon으로 수정했다. Panel의 모든 수치 허용오차와 source/input은 실행 전부터 그대로다.

**LOCAL FULL 생략 / 관련 시험으로 대체 / 새 독립 survey·시험·문서만 변경, 기존 실행 코드·공용 로직·동결 계약/fixture 불변.**
공식 baseline을 갱신하지 않는다. protected tracked187파일 및 이전 QZ raw87파일 전후 SHA 유지.
AGENTS/RULES는 전체 읽었고 CURRENT_STATE/REPO_MAP는 활성 Gate·전자 연구 범위만 부분 읽었다.
기존 H₂ 두 보고서와 QZ Gate 관련 절·evaluator/campaign/action checker를 직접 읽었다.

## NEXT GATE

**Electronic State / History Gate로 넘어갈 근거가 생겼다.** 같은 핵·Ne·sector라도 서로 다른 실제 electronic state/history가 가능한지 별도 조사한다.
이번 작업에서 그 Gate를 실행하거나 ground-state BO를 최종 A foundation으로 확정하지 않는다.

## Git·회복·증거

실제 ancestry: Generation1 `24ee72e336b2c8faef6b4dadbd155a98ba68b3b4`는
QZ `5095b085502c2de4f2f34a48ab4a35d4d6aa75ca`의 직접 parent다.
이번 branch `codex/electronic-sector-panel-v1`는 QZ에서 시작했다.
worktree `C:\Users\zun24\.codex\worktrees\electronic-sector-panel-v1\성공은 실패의 어머니`.
마지막 직접 지시 “마지막에 푸시도 좀 해줘 직접”를 적용해 검토·회복 package 확인 후 이번 branch를 push한다.
첨부 본문의 이전 push 금지를 덮는 최신 지시다. master merge는 요청되지 않았다.
Push SHA/원격 확인 영수증은 push 이전 sealed recovery ZIP에 넣지 않고 별도 보존한다.

compact evidence: [electronic_sector_panel_v1/](electronic_sector_panel_v1/desktop_results.json),
[사전 봉인](electronic_sector_panel_v1/desktop_seal.json),
[author 구상 검토](electronic_sector_panel_v1/author_review_v1.json),
[노트북 부분 재현](electronic_sector_panel_v1/laptop_replay_v1.json),
[raw manifest](electronic_sector_panel_v1/raw_manifest_v1.json).
대형 AO/변환/전체 eigenvector·별도 recovery는 Git 밖 `runs/electronic_sector_panel_v1_20261004/`에 보존한다.
프로젝트 동결 코드·historical H₂ evidence는 수정하지 않았다.

방법 검토에는 scientific-critical-thinking skill을 적용했다.
Kassis,T.; Agarwal,V.; He,Y.; Patel,D.; Brueckner,A.M.(2026),
[Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065),
최신 arXiv record(2026-09-02 개정)을 확인했다. 이 방법 참고문헌은 물리 결과의 독립 reference가 아니다.

## 쉽게 답하면

1. **핵만으로 충분한가?** 아니다. 같은 핵이라도 전자 수가 달라질 수 있다.
2. **N_e가 필요한가?** 이 계약에서는 authoritative 정보다.
3. **Q는 별도 상태인가?** isolated 계에서는 ΣZ−N_e로 계산하는 중복 장부다.
4. **같은 N_e에서 spin도 필요한가?** 어느 singlet/triplet 문제를 선택했는지 구분해야 한다. 저장 형식은 미결정이다.
5. **화학 ID 없이 계산했는가?** 그렇다.18개 모두 같은 법칙·전체 TZ 공간으로 계산했다.
6. **두 기기에서 재현됐는가?** 저장 AO에서 시작한 대표4개는 재현됐다. 새 AO 생성 포함 전체 재현은 아직 아니다.
7. **최소 static 입력 후보는?** 핵 Z/위치·N_e·선택 sector·Hamiltonian/basis 명세다.
8. **어떤 정보가 빠졌는가?** 실제 전자 상태와 시간 이력, excited/nonadiabatic 상태의 필요성 판단이 빠졌다.
9. **다음 Gate로 넘어가야 하는가?** 그렇다. State/History를 별도 검토할 차례이며 자동 착수하지 않았다.
