# Learning Roadmap — NLP to LLM

---

## Phase 2 — ML-Based NLP & Transformers

### Step 1 — Text Preprocessing
**Goal:** Understand how raw text becomes model input.

Topics:
- Tokenization at character / subword level (SentencePiece, BPE)
- What is a vocabulary? What is an `<UNK>` token?
- Padding and truncation (`max_length`)
- Attention mask — why it exists
- The difference between word tokenization (Phase 1 / PyThaiNLP) vs subword tokenization (transformers)

Practice:
```python
from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained("airesearch/wangchanberta-base-att-spm-uncased")
print(tokenizer("วันนี้ทำอะไรบ้าง"))
# See: input_ids, attention_mask
```

---

### Step 2 — What is a Transformer?
**Goal:** Understand the architecture behind BERT / WangchanBERTa.

Topics:
- Encoder vs Decoder (BERT = encoder only)
- Self-attention — how tokens look at each other
- What is a `[CLS]` token? What is `[SEP]`?
- Pre-training vs fine-tuning — why we don't train from scratch
- Why WangchanBERTa for Thai? (pre-trained on Thai corpus)

Resource: "The Illustrated BERT" by Jay Alammar (Google it — best visual explanation)

---

### Step 3 — Named Entity Recognition (NER)
**Goal:** Understand the task your bot needs.

Topics:
- What is NER? (extract "ฮาคุบะ" → LOCATION, "29 พ.ค." → DATE)
- BIO tagging scheme: `B-LOC`, `I-LOC`, `O`
- Token classification head on top of BERT
- How the model outputs one label per token

Example:
```
Input : "จากฮาคุบะไปคามิโคจิ"
Tokens: ["จาก", "ฮาคุบะ", "ไป", "คามิโคจิ"]
Labels: [O,     B-LOC,    O,    B-LOC      ]
```

---

### Step 4 — Fine-Tuning WangchanBERTa for NER
**Goal:** Train the model on your task.

Topics:
- What is LST20? (Thai NER dataset — your training data)
- How to load and format a dataset with HuggingFace `datasets`
- `Trainer` API — the standard fine-tuning loop
- Evaluation metrics: precision, recall, F1 (seqeval library)
- Saving and loading a checkpoint

Practice: Follow the HuggingFace NER fine-tuning tutorial, swap the dataset for LST20.

---

### Step 5 — Plug into the Bot
**Goal:** Replace `intent_engine.py` with the trained model.

- Load model with `pipeline("ner", model="your-checkpoint")`
- Extract `origin` and `destination` entities
- Uncomment the Phase 2 block in `webhook.py`

---

## Phase 3 — LLM + Context Injection

### Step 1 — Why LLMs Change Everything
**Goal:** Understand what GPT / Claude actually do differently.

Topics:
- Decoder-only architecture (GPT, Claude) vs encoder-only (BERT)
- Pre-training on massive text → emergent instruction following
- Why you don't need labeled data or fine-tuning for most tasks
- Zero-shot vs few-shot prompting

---

### Step 2 — Prompt Engineering
**Goal:** Learn to control LLM behavior through prompts.

Topics:
- System prompt vs user prompt
- Role prompting ("You are a Thai travel assistant...")
- Context injection — paste your JSON into the prompt
- Chain-of-thought prompting
- Output formatting (ask for JSON, bullet points, etc.)

Practice:
```
System: You are a Thai travel assistant.
        Here is the itinerary: {itinerary_json}
        Answer in Thai. Be concise.

User:   วันที่ 29 พ.ค. ทำอะไรบ้าง?
```

---

### Step 3 — RAG (Retrieval-Augmented Generation)
**Goal:** Understand how to scale beyond what fits in a prompt.

Topics:
- Why you can't always paste everything into a prompt (token limits)
- Embeddings — turning text into vectors
- Vector similarity search (find relevant chunks)
- Retrieve → inject → generate pipeline
- Tools: `chromadb`, `faiss`, OpenAI/Claude embeddings

This is the production pattern for document Q&A chatbots.

---

### Step 4 — Replace the Bot Engine
**Goal:** Apply everything to this project.

- Call Claude or OpenAI API from `webhook.py`
- Inject `tokyo-matsumoto.json` as context
- Remove `intent_engine.py` and `response_builder.py`
- Handle token cost and rate limits

---

## Summary

| Phase | Key Skill | What You Build |
|---|---|---|
| 1 (done) | Rule-based NLP, keyword matching | Working trip chatbot |
| 2 | Transformers, NER, fine-tuning | Smarter entity extractor |
| 3 | Prompt engineering, RAG, LLM APIs | Production-grade chatbot |
