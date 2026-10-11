"""Frozen native-memory ablation and database retrieval experiments.

Python is scoped to this experiment because the Infinity native Thrift SDK and
NumPy exact-neighbor reference run in the same benchmark process. The Docker
image owns dependencies; this package does not install host tools or change ELF.
"""
