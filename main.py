import streamlit as st
import base64
from groq import Groq

# ==========================
# Streamlit Page Config
# ==========================
st.set_page_config(page_title="KYC Vision Verification", layout="centered")

# ==========================
# Load API Key from Secrets
# ==========================
api_key = st.secrets.get("GROQ_API_KEY")

if not api_key:
    st.error("GROQ_API_KEY not found in Streamlit secrets.")
    st.stop()

client = Groq(api_key=api_key)


# ==========================
# Helper: Normalize Booleans
# ==========================
def normalize_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        stripped = value.strip().lower()
        if stripped == "true":
            return True
        if stripped == "false":
            return False
    return None


# ==========================
# Streamlit UI
# ==========================
st.set_page_config(page_title="KYC Vision Verification", layout="centered")
st.title("🛂 KYC Vision Verification System")

user_prompt = st.text_input(
    "Enter verification statement",
    "Analyze this ID document for authenticity and manipulation."
)

col_front, col_back = st.columns(2)
with col_front:
    front_image = st.file_uploader("Upload Front Side", type=["jpg", "jpeg", "png"], key="front")
with col_back:
    back_image = st.file_uploader("Upload Back Side (optional)", type=["jpg", "jpeg", "png"], key="back")

uploaded_files = [f for f in [front_image, back_image] if f is not None]

if uploaded_files:
    st.markdown(
        f"📎 **{len(uploaded_files)} image(s) uploaded** — "
        f"{'both sides detected' if len(uploaded_files) == 2 else 'single side uploaded'}"
    )

# ==========================
# System Prompt
# ==========================


system_prompt = """

You are not a generic LLM.
You are a deterministic ICAO rule-based validator.
You must apply mathematical validation before giving conclusions.
If checksum fails, you must flag it.
Do not assume document authenticity.

 

You are an ICAO 9303 compliant document forensic analysis model.

Your task is to perform a structured forensic analysis of government ID documents, specifically those containing a Machine Readable Zone (MRZ).

You must follow ICAO 9303 standards strictly.

If you are not aware of ICAO 9303, read and apply the following rules:

==============================
SECTION 1 — ICAO 9303 BASICS
==============================

ICAO 9303 defines the format and validation rules for Machine Readable Travel Documents (MRTDs).

For ID-1 size cards (credit-card sized IDs), the MRZ format is:

TD1 FORMAT:
- 3 lines
- Each line is exactly 30 characters
- Total characters per MRZ = 90

If any line is not exactly 30 characters, flag structural inconsistency.

==============================
SECTION 2 — TD1 MRZ STRUCTURE
==============================

Line 1:
Positions:
1-2   Document Code
3-5   Issuing Country (ISO 3166 alpha-3)
6-14  Document Number
15    Document Number Check Digit
16-30 Optional Data

Line 2:
1-6   Date of Birth (YYMMDD)
7     Birth Date Check Digit
8     Sex (M/F/<)
9-14  Expiry Date (YYMMDD)
15    Expiry Date Check Digit
16-18 Nationality (ISO alpha-3)
19-29 Optional Data
30    Final Composite Check Digit

Line 3:
Surname<<GivenNames<<

Names are separated by double <<.
Remaining spaces are filled with <

==============================
SECTION 3 — CHECK DIGIT RULE
==============================

ICAO check digit algorithm:

1. Replace letters with numeric values:
   A=10, B=11 ... Z=35
   < = 0

2. Use repeating weight pattern:
   7, 3, 1, 7, 3, 1, ...

3. Multiply each character value with its weight.
4. Sum all products.
5. Modulo 10 of total = check digit.

If calculated digit ≠ MRZ digit → flag as CHECKSUM FAILURE.

==============================
SECTION 4 — VALIDATION STEPS
==============================

You must perform these steps in order:

STEP 1:
Extract MRZ EXACTLY as visible.
Do not correct, normalize, or fix anything.

STEP 2:
Verify each line has exactly 30 characters.

STEP 3:
Parse fields according to TD1 positions.

STEP 4:
Validate:
- Document number check digit
- Date of birth check digit
- Expiry date check digit
- Final composite check digit

STEP 5:
Compare MRZ data with human-readable visible data:
- Name
- Date of Birth
- Expiry Date
- Document Number
- Nationality
- Sex

If any mismatch → flag DATA INCONSISTENCY.

STEP 6:
Evaluate structural integrity:
- Font alignment
- MRZ spacing consistency
- Unusual character usage
- Invalid country codes

==============================
SECTION 5 — FRAUD RISK LOGIC
==============================

Assign fraud risk based on evidence:

LOW RISK:
- All checksums valid
- All fields consistent
- Proper structure

MODERATE RISK:
- Minor formatting issues
- Slight visual vs MRZ mismatch

HIGH RISK:
- Any checksum failure
- Composite check digit failure
- Document number mismatch
- Structural format violation

You must justify fraud level strictly using technical evidence.

==============================
SECTION 6 — OUTPUT FORMAT
==============================

Your output must include:

1. Exact MRZ extraction (3 lines)
2. Field breakdown
3. Check digit calculations
4. Visual vs MRZ comparison table
5. Structural validation
6. Fraud risk conclusion with reasoning

If image quality is low, state reduced confidence.

Do NOT speculate.
Do NOT hallucinate missing values.
Only report what is visible.

---
based on these if any even one inconsistency found. Mark it as FAIL. 
Status: Fail/Pass
Reason: (Summarize into 3 to 5 senctence Why You marked it as Fail/True)

---
---
 Just give me answer in table form. just status and Reson can be out of table. I don't need paragraph text
---

"""

# ==========================
# Verification Button
# ==========================
if st.button("Verify"):

    if not uploaded_files:
        st.warning("Please upload at least the front side of the ID.")
        st.stop()

    side_labels = ["Front side", "Back side"]
    content = [{"type": "text", "text": f"{user_prompt} ({len(uploaded_files)} side(s) provided.)"}]

    for i, file in enumerate(uploaded_files):
        image_bytes = file.read()
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:image/jpeg;base64,{base64_image}"
        content.append({"type": "text", "text": f"Image {i + 1} ({side_labels[i]}):"})
        content.append({
            "type": "image_url",
            "image_url": {"url": data_url}
        })

    with st.spinner("Analyzing document..."):
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ],
            temperature=0,
            max_completion_tokens=1024
            # response_format={"type": "json_object"}
        )

    result = response.choices[0].message.content

    st.write(result)
