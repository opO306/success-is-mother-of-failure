"""Reference evaluators: slow, rigorous definitions of physical functions in A.

A reference evaluator DEFINES the A value of a physical function as the exact
mathematical value of the chosen model, rounded once by a number profile
(C0 numeric plan 11.6, designer verdict 8th ed.). Fast executors are judged
against it; they may use any algorithm but must return the same bits or refuse.
"""
