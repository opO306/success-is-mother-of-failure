"""Research data store: every research run kept as tiered, provenance-stamped,
immutable data -- for later analysis and, eventually, as training data for a
learned B.

Deliberately imports nothing. Importing this package must not pull in the
evaluator tier: `research_store.b_visible` is the only module B-side or
learned-B code may ever import, and a package `__init__` that re-exported
`research_store.evaluator` would put the evaluator tier one attribute away
from any code that imports the package at all.

    research_store/
      _core.py        tier-agnostic mechanics (objects, index chain, verify)
      provenance.py   who/what/which-version produced a record
      b_visible.py    the b_visible tier ONLY -- alias data B could have seen
      evaluator.py    evaluator + ground_truth tiers (real names, answers)
      ingest_blind.py evaluator-side: store one G7.3c blind research run
      verify.py       whole-store integrity + cross-tier reference check

See `docs/current/RESEARCH_STORE_V1.md` for the contract.
"""
