"""Stable text identity for inventory counts, excluding spacing and punctuation."""
import unicodedata


def sentence_key(text):
    return ''.join(c for c in unicodedata.normalize('NFC', text) if c.isalnum())
