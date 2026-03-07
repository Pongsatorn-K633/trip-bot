from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

# ── 1. Load model and tokenizer from the same fine-tuned checkpoint ──────────
MODEL_NAME = "Porameht/wangchanberta-thainer-corpus-v2-2"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForTokenClassification.from_pretrained(MODEL_NAME) # NER model fine-tuned on ThaiNER Corpus v2.2 (Thainer Wangchan)

# ── 2. Show available labels ─────────────────────────────────────────────────
print("Labels this model can detect:")
for id, label in model.config.id2label.items():
    print(f"  {id:2}: {label}")
print()

# ── 3. Build NER pipeline ────────────────────────────────────────────────────
# aggregation_strategy="simple" merges subword pieces into full entity spans
ner = pipeline("ner", model=model, tokenizer=tokenizer, aggregation_strategy="simple")

# ── 4. Test sentences ────────────────────────────────────────────────────────
test_sentences = [
    "ไปมัตสึโมโตวันที่ 29 พฤษภาคม",
    "ไปมัตสึโมตวันที่ 29 พฤษาคม",
    "วันที่ 30 พ.ค. ออกเดินทางจากฮาคุบะไปคามิโคจิ",
    "เช็คอินโรงแรมที่โตเกียวตอน 15:00 น.",
    "วันที่ 29 ทำอะไรบ้าง",
    "29"
]

USEFUL_LABELS = {"LOCATION", "DATE", "TIME", "FACILITY"}

for sentence in test_sentences:
    print(f"Input : {sentence}")
    results = ner(sentence)

    if not results:
        print("  (no entities found)")
    else:
        for ent in results:
            label = ent["entity_group"]
            word  = ent["word"]
            score = ent["score"]
            marker = " ✓" if label in USEFUL_LABELS else ""
            print(f"  [{label}] '{word}'  (score: {score:.3f}){marker}")
    print()


# {0: 'B-PERSON', 1: 'I-PERSON', 2: 'O', 3: 'B-ORGANIZATION', 4: 'B-LOCATION', 5: 'I-ORGANIZATION', 6: 'I-LOCATION', 7: 'B-DATE', 8: 'I-DATE', 9: 'B-TIME', 10: 'I-TIME', 11: 'B-MONEY', 12: 'I-MONEY', 13: 'B-FACILITY', 14: 'I-FACILITY', 15: 'B-URL', 16: 'I-URL', 17: 'B-PERCENT', 18: 'I-PERCENT', 19: 'B-LEN', 20: 'I-LEN', 21: 'B-AGO', 22: 'I-AGO', 23: 'B-LAW', 24: 'I-LAW', 25: 'B-PHONE', 26: 'I-PHONE', 27: 'B-EMAIL', 28: 'I-EMAIL', 29: 'B-ZIP', 30: 'B-TEMPERATURE', 31: 'I-TEMPERATURE'}