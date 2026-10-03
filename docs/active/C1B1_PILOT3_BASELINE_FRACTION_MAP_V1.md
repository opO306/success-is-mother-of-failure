# C1-B1 Pilot 3 measured baseline Fraction map

Six complete trajectories: 55,845 actual Combined steps. Source `ed37d651e10a995b19ece3a67fee92327fa2b921af86fb61d46633356749285a`.

Constructor routes: __new__ 4,867,919; _from_coprime_ints 6,102,424; total 10,970,343. gcd 12,615,567. All five operation counts exactly equal preserved production-only pstats. Final states match prior Combined results.

24 function/line addresses, 19 physical source lines. Four world-fixed addresses have 53 distinct exact values and 5,082,660 creations (46.330912%); one run-fixed half-dt address (including the world literal 2).

Timing is instrumented original-operation CPU attribution, excluding measured wrapper bookkeeping. Unwrapped accessor/dispatch cost remains in parent operations. Windows thread CPU clock is coarse. These percentages are not uninstrumented runtime speed and are not a prediction of attainable speedup.

| File : function : line | Lifetime | New | Coprime | Multiply | gcd | CPU % | N bits | D bits | Distinct values | Repetition % | Denominators |
|---|---|---:|---:|---:|---:|---:|---|---|---:|---:|---:|
| a_reference/c1b1_two_atom.py:step:498 | B_run_fixed_with_world_literal / dt_related | 55845 | 55845 | 0 | 111690 | 0.52706 | 2–5 | 1–1 | 2 | 99.99821 | 1 |
| a_numeric/profiles.py:to_exact:96 | C_step_variable_reused / position_power_of_two | 1005246 | 0 | 0 | 1005246 | 2.93394 | 0–52 | 1–49 | 209061 | 79.20300 | 17 |
| a_reference/c1b1_two_atom.py:<genexpr>:370 | C_step_relative_reused / position_power_of_two | 0 | 335088 | 0 | 544136 | 2.42446 | 0–52 | 1–48 | 104531 | 68.80491 | 17 |
| a_reference/c1b1_fast_impulse.py:impulse:75 | C_step_R2 / position_power_of_two | 55851 | 167553 | 0 | 216237 | 0.79058 | 0–103 | 1–95 | 104531 | 53.20988 | 24 |
| a_reference/c1b1_fast_impulse.py:<genexpr>:75 | D_axis_square / position_power_of_two | 0 | 167553 | 167553 | 335106 | 0.94870 | 0–103 | 1–95 | 104531 | 37.61317 | 17 |
| a_reference/c1b1_fast_impulse.py:impulse:87 | D_component_variable / dt_and_precision_power_of_two | 0 | 167553 | 167553 | 335106 | 1.19466 | 0–54 | 1–46 | 104531 | 37.61317 | 17 |
| a_reference/c1b1_fast_impulse.py:_impulse_model_R_fast:33 | A_world_fixed / fixed_parameter | 677688 | 677688 | 677688 | 1355376 | 6.76388 | 1–30 | 1–31 | 15 | 99.99889 | 9 |
| a_reference/c1b1_fast_impulse.py:_impulse_model_R_fast:53 | A_world_fixed / fixed_parameter | 282370 | 282370 | 282370 | 564740 | 2.72312 | 1–54 | 1–95 | 10 | 99.99823 | 6 |
| a_reference/c1b1_fast_impulse.py:_impulse_model_R_fast:56 | A_world_fixed / fixed_parameter | 338844 | 338844 | 338844 | 677688 | 3.21504 | 1–53 | 1–101 | 12 | 99.99823 | 7 |
| a_reference/c1b1_fast_impulse.py:_impulse_model_R_fast:67 | A_world_fixed / fixed_parameter | 1242428 | 1242428 | 1242428 | 2484856 | 11.36683 | 2–36 | 1–36 | 29 | 99.99883 | 12 |
| a_reference/c1b1_fast_impulse.py:at:94 | D_component_variable / dt_and_precision_power_of_two | 210322 | 210322 | 210322 | 630966 | 1.96767 | 88–296 | 114–302 | 323250 | 23.15355 | 65 |
| a_numeric/profiles.py:_as_exact:39 | D_component_variable / dt_and_precision_power_of_two | 273340 | 0 | 0 | 0 | 0.52706 | 0–296 | 1–302 | 210313 | 23.05810 | 38 |
| a_reference/c1b1_combined_arithmetic.py:<genexpr>:92 | C_step_exact_drift_endpoint / mass_and_dt_related | 335070 | 335070 | 0 | 879178 | 3.21504 | 0–137 | 1–134 | 418109 | 37.60871 | 107 |
| a_reference/c1b1_two_atom.py:<genexpr>:514 | C_step_exact_drift_endpoint / mass_and_dt_related | 0 | 335070 | 0 | 544118 | 2.17850 | 0–137 | 1–133 | 209055 | 37.60856 | 107 |
| a_reference/c1b1_two_atom.py:segment_min_R2:487 | E_general_exact_segment_guard / other_general | 55845 | 167535 | 0 | 216219 | 1.28250 | 0–254 | 1–265 | 104530 | 53.20530 | 112 |
| a_reference/c1b1_two_atom.py:<genexpr>:487 | E_general_exact_segment_guard / other_general | 0 | 167535 | 167535 | 335070 | 1.17709 | 0–254 | 1–265 | 104530 | 37.60707 | 107 |
| a_reference/c1b1_two_atom.py:segment_min_R2:488 | E_general_exact_segment_guard / other_general | 55845 | 167535 | 0 | 216215 | 0.87843 | 0–178 | 1–180 | 104526 | 53.20709 | 149 |
| a_reference/c1b1_two_atom.py:<genexpr>:488 | E_general_exact_segment_guard / other_general | 0 | 167535 | 167535 | 335070 | 1.26493 | 0–178 | 1–180 | 104526 | 37.60945 | 156 |
| a_reference/c1b1_two_atom.py:segment_min_R2:489 | E_general_exact_segment_guard / other_general | 55845 | 167535 | 0 | 216215 | 0.93113 | 0–103 | 1–95 | 104521 | 53.20933 | 24 |
| a_reference/c1b1_two_atom.py:<genexpr>:489 | E_general_exact_segment_guard / other_general | 0 | 167535 | 167535 | 335070 | 1.05411 | 0–103 | 1–95 | 104521 | 37.61244 | 17 |
| a_reference/c1b1_two_atom.py:segment_min_R2:492 | E_general_exact_segment_guard / other_general | 111690 | 111690 | 0 | 111690 | 0.72031 | 0–219 | 1–209 | 111692 | 49.99910 | 55949 |
| a_reference/c1b1_two_atom.py:segment_min_R2:493 | E_general_exact_segment_guard / other_general | 55845 | 335070 | 223380 | 614286 | 2.16093 | 0–407 | 1–409 | 139613 | 64.28559 | 145 |
| a_reference/c1b1_two_atom.py:step:518 | C_step_stored_R2 / position_power_of_two | 55845 | 167535 | 0 | 216219 | 1.03654 | 0–103 | 1–95 | 104530 | 53.20530 | 24 |
| a_reference/c1b1_two_atom.py:<genexpr>:518 | D_axis_stored_square / position_power_of_two | 0 | 167535 | 167535 | 335070 | 1.07168 | 0–103 | 1–95 | 104530 | 37.60707 | 17 |

Denominator shape counts and top repeated exact n/d values, plus gcd operand bit maxima, are in lifetime_map.json. Fixed parameter, mass/dt, position powers of two and genuine general guard rationals are separately labeled. Zero/unit literals coexist with variable output at several sites; repetition alone is not evidence that a variable state value may be cached.

The all-frame observer v1 was stopped for measurement overhead after a completed head_on and partial remaining data. It is INCOMPLETE, not counted as a successful complete census. Its source snapshots, SQLite data and completed state hash are preserved. Original arithmetic stayed unchanged.

The v2 observer restores the original Fraction descriptors and gcd function on every exit; independent cProfile on a real step and raw-state equality passed. No production optimization code preceded this map.
