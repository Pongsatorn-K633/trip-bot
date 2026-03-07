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
- `O` = Outside — means "not an entity", not a label type

Example:
```
Input : "จากฮาคุบะไปคามิโคจิ"
Tokens: ["จาก", "ฮาคุบะ", "ไป", "คามิโคจิ"]
Labels: [O,     B-LOC,    O,    B-LOC      ]
```

#### NER vs Text Classification — two different tasks, same base model

Both tasks use WangchanBERTa as the encoder, but attach different heads:

```
WangchanBERTa encoder
        │
        ├──► Token Classification Head  →  NER
        │     (one label per token)         AutoModelForTokenClassification
        │
        └──► Sequence Classification Head  →  Text Classification / Intent
              (one label per [CLS] token)      AutoModelForSequenceClassification
```

| | NER | Text Classification |
|---|---|---|
| Output | 1 label per token | 1 label per sentence |
| Labels | `B-LOC`, `I-DATE`, `O` … | `query_itinerary`, `greeting` … |
| Loss computed on | Every token | Only `[CLS]` token |
| Answers | *What* entities are in the text | *What* the user wants to do |

Fine-tuning for NER and fine-tuning for text classification are **separate training runs** with separate datasets, even though both start from the same checkpoint.

#### Do you need both for this bot?

NER extracts *what* is in the text (date, place). Intent classification determines *what action* to take (query, delete, add).

| Bot complexity | What you need |
|---|---|
| Single-purpose — show activities only (current bot) | NER only — everything is implicitly `query_itinerary` |
| Multi-action — query + add + delete | NER + Intent classification |
| Full assistant — arbitrary tasks | LLM handles both implicitly |

For the current itinerary bot, **NER alone is sufficient**. Intent classification becomes necessary only when the bot supports multiple actions on the same entity.

#### PyThaiNLP NER vs WangchanBERTa NER

PyThaiNLP ships a built-in NER tagger (CRF-based). It is simpler but weaker:

| | PyThaiNLP NER | WangchanBERTa NER |
|---|---|---|
| Model type | CRF — classical ML | RoBERTa + token classification head |
| Tokenizer | newmm (dictionary word-level) | SentencePiece subword |
| Context awareness | None — labels each token independently | Full bidirectional attention |
| Size | ~MB, instant | ~500 MB, needs decent CPU/GPU |
| Use case | Quick prototype | Production accuracy |

The critical difference is **context**. CRF labels tokens one by one using local features. A transformer attends to the entire sentence, so the same surface form (e.g. "มัตสึโมโต") can be correctly labeled LOC or PERSON depending on surrounding words.

**Recommended order:** get PyThaiNLP NER working first to understand BIO output format, then replicate with WangchanBERTa to feel the quality difference.

#### NER real-world applications

NER's real home is **document processing**, not chatbots (LLMs replaced NER in chatbots after 2022):

| Industry | NER use |
|---|---|
| Medical | Extract drug names, dosages, symptoms from clinical notes → structured database |
| Legal | Extract parties, dates, clauses from contracts automatically |
| Finance | Extract company names, amounts, dates from earnings reports |
| HR | Resume parsing — extract skills, companies, job titles |
| Compliance | Flag PII (names, phones, IDs) in documents for redaction before sending to external APIs |

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

## Phase 3 — LLM + Context Injection (Production)

### Application layer vs Deep understanding

| Goal | Approach |
|---|---|
| Build a working chatbot now | Use pre-trained LLM via Ollama API — done |
| Understand how LLM works internally | Study the full pipeline below |
| Build your own LLM from scratch | Follow the deep learning path at the end |

---

### Step 1 — Why LLMs Change Everything
**Goal:** Understand what GPT / Claude actually do differently from BERT.

Topics:
- Decoder-only architecture (GPT, Llama, Typhoon) vs encoder-only (BERT, WangchanBERTa)
- BERT reads whole sentence bidirectionally — LLM reads left to right, generates new tokens
- Pre-training on massive text → emergent instruction following
- Why you don't need labeled data or fine-tuning for most tasks
- Zero-shot vs few-shot prompting

```
BERT (encoder):   reads [full sentence] → outputs labels for existing tokens
LLM  (decoder):   reads [prompt] → predicts next token → appends → repeats
```

---

### Step 2 — How LLM Generates Text (the behind-the-scenes pipeline)

This is what Ollama does invisibly when you call `requests.post(...)`:

```
Your plain text (system prompt + user message)
    │
    ▼  1. Tokenize  (SentencePiece / BPE — same concept as WangchanBERTa)
["▁วัน", "ที่", "▁29", "▁ทำ", "อะไร", "บ้าง"]
    │
    ▼  2. Token IDs  (vocabulary lookup)
[2341, 891, 445, 1203, 567, 892]
    │
    ▼  3. Embedding lookup  (each ID → 768/4096-dim vector)
    │
    ▼  4. Decoder transformer layers  (left-to-right attention, ~32 layers)
    │      each token attends to ALL previous tokens
    │
    ▼  5. Predict next token  (softmax over full vocabulary)
    │      "กิจกรรม" → 42%
    │      "กำหนดการ" → 31%
    │      ... pick highest (or sample)
    │
    ▼  6. Append predicted token → repeat from step 4
    │      until <end> token is predicted
    │
    ▼  7. Detokenize → plain Thai text reply
```

You only see step 1 input and step 7 output. Everything in between is inside Ollama.

**Why the itinerary JSON is text, not vectors:**
- RAG converts documents to vectors for *searching large corpora*
- Your itinerary (~2,000 tokens) fits entirely in the context window
- No search needed — paste everything, LLM reads it all as tokens
- Every user message re-sends the full itinerary (stateless — no memory between calls)

---

### Step 3 — Prompt Engineering
**Goal:** Learn to control LLM behavior through prompts.

Topics:
- System prompt vs user prompt
- Role prompting ("You are a Thai travel assistant...")
- Context injection — paste your JSON into the prompt
- Output formatting (ask for bullets, specific structure)
- Temperature / top-p — controls randomness of next-token sampling

```python
# trip-bot system prompt structure
system = f"""
คุณเป็นผู้ช่วยท่องเที่ยวภาษาไทย
ทริปนี้อยู่ในช่วง 29 พ.ค. – 8 มิ.ย. 2569
ตอบตามข้อมูลนี้เท่านั้น: {itinerary_json}
"""
```

**How LLM handles what Phase 1 needed code for:**

| Phase 1 needed | LLM does automatically |
|---|---|
| Regex for date extraction | Reads "29 พ.ค." in context → understands it |
| Gazetteer for place names | Reads JSON → matches places in context |
| Intent classification | Infers what user wants from phrasing |
| Typo handling | Predicts most likely meaning from context |

---

### Ollama Model Selection

Ollama hosts and runs inference locally — no API key, no cost, no data leaving your machine.

**Install:** download from ollama.com then pull a model:

```bash
ollama pull qwen2.5:3b    # recommended starting point
ollama serve              # starts local server on localhost:11434
```

**Model comparison for this bot (Thai group chat, CPU only):**

| Model | Size | Speed (CPU) | Thai quality | Recommended for |
|---|---|---|---|---|
| `qwen2.5:3b` | 1.9 GB | ~10-15s | Good | **Starting point - best balance** |
| `qwen2.5` | 4.7 GB | ~30-60s | Very good | Better quality, slower |
| `supachai/llama-3-typhoon-v1.5:8b-instruct` | 4.9 GB | ~30-60s | Best (Thai-specific) | Best Thai, needs patience |
| `llama3.2:1b` | 1.3 GB | ~5s | Decent | Fastest, weakest Thai |

**Upgrade path:**
- Start with `qwen2.5:3b` -> test response quality
- If Thai quality not good enough -> upgrade to `qwen2.5` or `typhoon`
- If too slow for group chat -> downgrade to `llama3.2:1b`

**How Ollama works:**
- Downloads model in GGUF format (quantized - 4-bit instead of 16-bit = smaller, faster)
- Runs as background server on `localhost:11434`
- Your Python code sends HTTP requests - Ollama runs the full inference pipeline internally
- You only see plain text in -> plain text out

**Group chat trigger word:**
In group chats, bot responds only when message starts with the trigger word:
```
fujisan วันที่ 29 ทำอะไรบ้าง   <- bot responds
วันที่ 29 ทำอะไรบ้าง           <- bot ignores
```

---

### Ollama Model Selection

Ollama hosts and runs inference locally — no API key, no cost, no data leaving your machine.

**Install:** download from ollama.com → then pull a model:

**Model comparison for this bot (Thai group chat, CPU only):**

| Model | Size | Speed (CPU) | Thai quality | Recommended for |
|---|---|---|---|---|
| \ | 1.9 GB | ~10–15s | Good | **Starting point — best balance** |
| \ | 4.7 GB | ~30–60s | Very good | Better quality, slower |
| \ | 4.9 GB | ~30–60s | Best (Thai-specific) | Best Thai, needs patience |
| \ | 1.3 GB | ~5s | Decent | Fastest, weakest Thai |

**Upgrade path:**
- Start with \ → test response quality
- If Thai quality not good enough → upgrade to \ or - If too slow for group chat → downgrade to 
**How Ollama works:**
- Downloads model in GGUF format (quantized — 4-bit instead of 16-bit = smaller, faster)
- Runs as background server on - Your Python code sends HTTP requests — Ollama runs the full inference pipeline internally
- You only see plain text in → plain text out

**Group chat trigger word:**
In group chats, bot responds only when message starts with the trigger word:
---

### Step 4 — RAG (Retrieval-Augmented Generation)
**Goal:** Understand when and why context injection is not enough.

Topics:
- Token limit problem: when data > context window, you can't paste everything
- Embeddings — convert text chunks to vectors that capture semantic meaning
- Vector similarity search — find chunks most relevant to the query
- Retrieve relevant chunks → inject only those → LLM generates answer
- Tools: `chromadb`, `faiss`, OpenAI/Claude embeddings

**When RAG is needed vs not:**

| Data size | Approach |
|---|---|
| Small JSON / single document (trip-bot now) | Full context injection — no RAG |
| 10+ trips | Still probably fine with full injection |
| 100+ trips + reviews + guides | RAG — mandatory |

---

### Step 5 — If You Want to Build Your Own LLM

The full learning path from understanding to building from scratch:

```
Level 1 — Tokenization              ✓ done (SentencePiece, BPE, input_ids)
Level 2 — Embeddings                ✓ done (token IDs → vectors, WangchanBERTa)
Level 3 — Encoder transformer       ✓ done (BERT, attention, NER, BIO)
Level 4 — Decoder / Generation      → next (next-token prediction, autoregressive)
Level 5 — Pre-training              → how model learns from raw text (loss, backprop)
Level 6 — Build your own small LLM  → implement transformer in PyTorch from scratch
```

**Recommended resources in order:**

| Resource | What you learn |
|---|---|
| 3Blue1Brown — Neural Networks series | Backpropagation visually |
| Andrej Karpathy — makemore (YouTube) | Build bigram → MLP → transformer from scratch |
| Andrej Karpathy — nanoGPT (GitHub) | Minimal GPT in ~300 lines of PyTorch |
| HuggingFace course chapters 1–4 | Pre-training and fine-tuning at scale |
| Paper: "Attention Is All You Need" (2017) | Original transformer architecture |

nanoGPT is the single best resource — it implements exactly the pipeline above
(`tokenize → IDs → transformer layers → predict next token → repeat`) from zero.

---

## Summary

| Phase | Status | Key skill | What you built |
|---|---|---|---|
| 1 | Done | Rule-based NLP, keyword matching | Working trip chatbot |
| 2 | Done (learning) | Transformers, NER, BIO tagging, subword tokenization | Understood ML-based NLP |
| 3 | Done (production) | Prompt engineering, context injection, Typhoon API | Production LLM chatbot via `openai` SDK + `typhoon-v2.5-30b-a3b-instruct` |
| 4 (optional) | Future | Decoder architecture, pre-training, PyTorch | Build your own LLM |
