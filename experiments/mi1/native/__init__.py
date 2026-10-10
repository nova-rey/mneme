"""Small NumPy oracle for the Phase 4 MI1 attention-bank path.

This package is an engineering reference implementation. It does not mutate
MNEME state and is not wired into the production runtime.
"""

from .bank import BankAttachment, BankManifest, MemoryBank, augmented_attention, encode_slots

__all__ = ["BankAttachment", "BankManifest", "MemoryBank", "augmented_attention", "encode_slots"]
