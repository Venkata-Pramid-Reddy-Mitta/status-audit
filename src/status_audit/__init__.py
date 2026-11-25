"""status-audit: recompute program RAG from objective signals and reconcile it.

A RAG (Red/Amber/Green) status on a program report is a human summary. This package
exists because a summary cannot audit itself: reading the colour tells you nothing about
whether it is honest. The only way to know is to recompute the colour independently from
the objective signals and compare. Everything here serves that one comparison.
"""

__version__ = "0.1.0"
