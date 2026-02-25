"""
Phase 2 Placeholder — WangchanBERTa NER Model
==============================================

This module will host the Named Entity Recognition (NER) pipeline
fine-tuned on the LST20 dataset using the WangchanBERTa base model.

Target entities:
  - ORIGIN      : departure location  (e.g., "มัตสึโมโตะ")
  - DESTINATION : arrival location    (e.g., "ฮาคุบะ")

Planned implementation steps:
  1. Fine-tune  airesearch/wangchanberta-base-att-spm-uncased  on LST20
     with a token-classification head (BIO tagging scheme).
  2. Save checkpoint to  app/models/checkpoints/wangchanberta-ner/
  3. Load via  transformers.pipeline("ner", model=..., aggregation_strategy="simple")
  4. Post-process entity spans → {"origin": str | None, "destination": str | None}
  5. Pass entities to a Map API (e.g., Google Maps Directions) for custom routing.

Dependencies to add to requirements.txt when ready:
  transformers>=4.40.0
  torch>=2.2.0
  sentencepiece>=0.1.99
  accelerate>=0.27.0

Usage (once implemented):
  from app.models.ner_placeholder import extract_entities
  entities = extract_entities("จากมัตสึโมโตะไปฮาคุบะยังไง")
  # → {"origin": "มัตสึโมโตะ", "destination": "ฮาคุบะ"}
"""

from typing import TypedDict


class Entities(TypedDict):
    origin: str | None
    destination: str | None


def extract_entities(text: str) -> Entities:
    """
    STUB — raises NotImplementedError until Phase 2 model is implemented.
    Replace this body with the actual Hugging Face NER inference pipeline.
    """
    raise NotImplementedError(
        "Phase 2 NER model is not yet implemented. "
        "See app/models/ner_placeholder.py for the implementation plan."
    )
