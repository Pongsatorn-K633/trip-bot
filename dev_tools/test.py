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


print("Transformers tokenizer test:")
from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained("airesearch/wangchanberta-base-att-spm-uncased")
print(tokenizer("วันนี้ทำอะไรบ้าง"))