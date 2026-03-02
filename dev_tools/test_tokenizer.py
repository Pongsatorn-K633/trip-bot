print("PythaiNLP (Dictionary-based) word-tokenizer test:")
from pythainlp.tokenize import word_tokenize

test_cases = [
    "วันนี้ทำอะไรบ้าง",
    "กำหนดการวันนี้",
    "ตื่นกี่โมง",
    "ไปที่ไหนต่อ",
    "เดินทางยังไง",
    "ออกเดินทางกี่โมง",
    "กำหนดการวันที่ 29 พ.ค.",
    "วันที่29พ.ค.ทำอะไรบ้าง",
]

for text in test_cases:
    tokens = word_tokenize(text, engine="newmm", keep_whitespace=False)
    print(f"Input : {text}")
    print(f"Tokens: {tokens}")
    print()


print("Transformers wangchanberta (SentencePiece Model) tokenizer test:")
from transformers import AutoTokenizer

# 1. Load the tokenizer for WangchanBERTa
tokenizer = AutoTokenizer.from_pretrained("airesearch/wangchanberta-base-att-spm-uncased")

# 2. Your raw text (no special tokens added by you!)
raw_text = "ผมกำลังเตรียมตัวแข่งแฮกกาธอน"
# raw_text = "วันนี้ทำอะไรบ้าง"

# 3. Pass the text through the tokenizer
# We'll ask it to return the actual string tokens so we can read them
tokens = tokenizer.tokenize(raw_text)

# tokenizer() adds special tokens automatically, then convert IDs back to readable strings
encoding = tokenizer(raw_text, add_special_tokens=True)
tokens_with_special = tokenizer.convert_ids_to_tokens(encoding["input_ids"])

print("Original Text  :", raw_text)
print("Subword tokens :", tokens)
print("With <s>/</s>  :", tokens_with_special)
print("input_ids      :", encoding["input_ids"])
print("attention_mask :", encoding["attention_mask"])