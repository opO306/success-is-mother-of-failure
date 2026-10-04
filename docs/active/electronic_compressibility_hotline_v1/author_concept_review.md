# Author concept review — independent of pytest assertions

2026-10-04 / 작성자 검토 / 외부 independent audit 아님.

| 설계자 의도 | 구현 증거와 경계 |
|---|---|
| 두 축을 처음부터 합치지 않기 | tensor.py와 baseline.py 별도 실행, 통합 실행기 없음 |
| 기존 exact finite state 사용 | 기존 A/B corpus SHA 봉인·보존; 새 AO/물리 모델 없음 |
| 의미 있는 Schmidt factorization | 고정 orbital Fock number sectors, singlet spin 쌍 보존; occupation enumeration 별도 검사 |
| 여러 사전 partitions | original/energy/z-position, cuts7/14/21; post-result search 없음 |
| 작은 값의 미래 영향 숨기지 않기 | norm/fidelity/energy/density/dipole 및 actual future/bound 기록, renormalization으로 숨기지 않음 |
| coverage와 resolution 분리 | 모든 block pair 포함, coarse radius 유지, HOT는 precision만 승격 |
| COLD=0 금지 | nonzero center+enclosure, canonical 요청 때 원본 복원; 원본은 메모리 보존 |
| bounded starvation | K=1, 모든 실제 trace의 block update 확인 |
| hysteresis의 safety override | 경계6→2전환, unsafe0.009 override, entry0.02 branch probe |
| scheduler가 물리를 바꾸지 않기 | primary90case 및 live outputs/다음 step 동일, full dense law 유지 |
| 숨은 사건 놓치지 않기 | 봉인한 control radius 상승을 실제 HOT로 검출; 자연 발생 전자 사건 증거는 아님 |
| cheap 확장성 | 미달. 모든 원본 읽기+Fraction bounds가 REF보다 비싸며 dense authority 메모리 유지 |

누락/미구현: tensor-native dynamics, 모든 MPS bonds, truly cheap monitor, sparse verified
coupling certificate, cold paging/I/O, physical spatial hierarchy, 장기/큰 전자 corpus,
formal numerical certificate, independent external audit, production A integration.

저랭크와 bytes 이득, bytes provenance와 물리 정확성, numeric test와 formal certification을
구분했다. 결론은 A CONDITIONAL/B POOR, Hotline accounting/control PASS but cost benefit FAIL.
따라서 두 축의 통합 production으로 확대하지 않았다.
