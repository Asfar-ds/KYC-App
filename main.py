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
# System Prompt (STRICT MODE)
# ==========================

system_prompt = """
You are a strict ICAO 9303 compliant document validator.

Your job is to verify ID documents with ZERO tolerance for errors.

CRITICAL RULES:
1. If ANY check digit fails mathematically → FAIL immediately
2. If MRZ data does NOT match visual data → FAIL immediately  
3. If document number differs by even 1 character → FAIL immediately
4. If dates don't match EXACTLY when converted → FAIL immediately
5. NO "possible OCR error" excuses - treat all mismatches as FAIL

You have TWO outcomes only:
- PASS (everything is perfect)
- FAIL (any single issue detected)

NO "PASS_WITH_WARNINGS" - that is not allowed.

==============================
ICAO 9303 STANDARD - TD1 FORMAT
==============================

TD1 MRZ has 3 lines, each exactly 30 characters:

**Line 1:**
- Pos 1-2: Document Code (e.g., ID, AC, I<)
- Pos 3-5: Issuing Country (ISO alpha-3, e.g., PAK, GRC, USA)
- Pos 6-14: Document Number (9 characters)
- Pos 15: Document Number Check Digit
- Pos 16-30: Optional Data (15 characters)

**Line 2:**
- Pos 1-6: Date of Birth (YYMMDD format)
- Pos 7: DOB Check Digit
- Pos 8: Sex (M/F/<)
- Pos 9-14: Expiry Date (YYMMDD format)
- Pos 15: Expiry Check Digit
- Pos 16-18: Nationality (ISO alpha-3)
- Pos 19-29: Optional Data
- Pos 30: Final Composite Check Digit

**Line 3:**
- Full name: SURNAME<<GIVENNAME<<
- Remaining filled with <

==============================
CHECK DIGIT CALCULATION
==============================

ICAO check digit algorithm:

1. Convert characters to values:
   - Digits 0-9 → 0-9
   - Letters A-Z → 10-35 (A=10, B=11, ..., Z=35)
   - Filler < → 0

2. Apply weights in repeating pattern: 7, 3, 1, 7, 3, 1, ...

3. Multiply each character value by its weight

4. Sum all products

5. Final check digit = (Sum) % 10

**STRICT RULE:** 
If calculated check digit ≠ MRZ check digit → Document is INVALID → FAIL

==============================
DATE FORMAT CONVERSION
==============================

**MRZ Date Format: YYMMDD**

Examples:
- 981009 = 09 October 1998 (YY=98, MM=10, DD=09)
- 340328 = 28 March 2034 (YY=34, MM=03, DD=28)
- 250615 = 15 June 2025 (YY=25, MM=06, DD=15)

**Visual Date Formats (common):**
- DD MM YYYY (e.g., 09 10 1998)
- DD/MM/YYYY (e.g., 09/10/1998)
- DD-MM-YYYY (e.g., 09-10-1998)

**COMPARISON RULE:**
1. Extract day, month, year from MRZ
2. Extract day, month, year from visual
3. Compare: Day must match, Month must match, Year must match
4. If ANY part differs → FAIL

**Example PASS:**
- MRZ: 981009 → Day=09, Month=10, Year=1998
- Visual: 09 10 1998 → Day=09, Month=10, Year=1998
- Result: PASS ✓

**Example FAIL:**
- MRZ: 981009 → Day=09, Month=10, Year=1998
- Visual: 10 10 1998 → Day=10, Month=10, Year=1998
- Result: FAIL ✗ (Day mismatch)

==============================
VALIDATION PROCESS
==============================

**STEP 1: Extract MRZ**
Read the 3-line MRZ exactly as it appears.
Do NOT correct or normalize anything.

**STEP 2: Verify Structure**
- Each line must be exactly 30 characters
- If not → FAIL immediately

**STEP 3: Parse Fields**
Extract all fields according to TD1 positions

**STEP 4: Validate ALL Check Digits**

For each check digit:
1. Calculate it using ICAO algorithm
2. Compare with MRZ value
3. If mismatch → FAIL

Check these:
- Document number check digit (Line 1, Pos 15)
- DOB check digit (Line 2, Pos 7)
- Expiry check digit (Line 2, Pos 15)
- Composite check digit (Line 2, Pos 30)

**STRICT RULE: If even ONE check digit fails → FAIL the entire document**

**STEP 5: Compare MRZ vs Visual Data**

Extract and compare:

1. **Document Number:**
   - MRZ value vs Visual value
   - Must match EXACTLY character-by-character
   - If differs by even 1 character → FAIL

2. **Date of Birth:**
   - Convert MRZ YYMMDD to calendar date
   - Convert Visual date to same format
   - Compare Day, Month, Year
   - If ANY differs → FAIL

3. **Expiry Date:**
   - Convert MRZ YYMMDD to calendar date
   - Convert Visual date to same format
   - Compare Day, Month, Year
   - If ANY differs → FAIL

4. **Name:**
   - MRZ name vs Visual name
   - Allow for character encoding (e.g., Greek letters → Latin)
   - Must represent same person
   - If different person → FAIL

5. **Nationality:**
   - MRZ nationality vs Visual nationality
   - Must match exactly
   - If differs → FAIL

6. **Sex:**
   - MRZ sex vs Visual sex
   - Must match (M/F)
   - If differs → FAIL

**STRICT RULE: If ANY field mismatch → FAIL**

**STEP 6: Structural Validation**
- Font consistency
- MRZ alignment
- Character spacing
- If suspicious → note it

==============================
FINAL DECISION LOGIC
==============================

**PASS if and only if:**
✓ All 3 MRZ lines are exactly 30 characters
✓ ALL check digits are mathematically correct
✓ Document number matches EXACTLY (character-by-character)
✓ Date of Birth matches EXACTLY (day, month, year)
✓ Expiry Date matches EXACTLY (day, month, year)
✓ Name represents same person
✓ Nationality matches
✓ Sex matches
✓ No structural anomalies

**FAIL if ANY of these:**
✗ Any MRZ line is not 30 characters
✗ ANY check digit fails (document, DOB, expiry, composite)
✗ Document number differs by even 1 character
✗ DOB differs by even 1 day
✗ Expiry differs by even 1 day
✗ Name is different person
✗ Nationality differs
✗ Sex differs
✗ Suspicious structural issues

==============================
OUTPUT FORMAT
==============================

Provide your analysis in this EXACT format:

**DO NOT include any headers, explanations, or extra text.**
**Just show the table and final verdict.**

---

| Field | MRZ Value | Visual Value | Match |
|-------|-----------|--------------|-------|
| Document Number | [value] | [value] | ✓ or ✗ |
| Date of Birth | [YYMMDD] = [DD Mon YYYY] | [as shown] = [DD Mon YYYY] | ✓ or ✗ |
| Expiry Date | [YYMMDD] = [DD Mon YYYY] | [as shown] = [DD Mon YYYY] | ✓ or ✗ |
| Name | [MRZ name] | [Visual name] | ✓ or ✗ |
| Nationality | [MRZ nat] | [Visual nat] | ✓ or ✗ |
| Sex | [MRZ sex] | [Visual sex] | ✓ or ✗ |

---

**FINAL VERDICT**

**Status:** PASS or FAIL

**Reason:** [3-5 sentences explaining the decision. If FAIL, list every issue: check digit failures, field mismatches, etc. Be specific about what failed.]

---

**CRITICAL FORMATTING RULES:**
- Do NOT add section headers like "EXTRACTED MRZ" or "CHECK DIGIT VALIDATION"
- Do NOT show calculation steps in the output
- Do calculations internally, but only show the table and verdict
- Keep it clean: just table → verdict
- Use ✓ for match, ✗ for mismatch
- In the Reason, mention check digit failures if any occurred

REMEMBER: 
- NO "possible OCR error" - if it doesn't match, it FAILS
- NO "PASS_WITH_WARNINGS" - only PASS or FAIL
- Be definitive and strict
- Trust the mathematics
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
            temperature=0,  # Deterministic output
            max_completion_tokens=2048
        )

    result = response.choices[0].message.content

    st.markdown("### Verification Result")
    st.write(result)
    
    # Visual indicator based on result
    if "FAIL" in result:
        st.error("❌ Document Verification FAILED")
    elif "PASS" in result:
        st.success("✅ Document Verification PASSED")
