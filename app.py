import sys
if sys.version_info < (3, 9):
    import hashlib
    _original_md5 = hashlib.md5
    def _patched_md5(*args, **kwargs):
        kwargs.pop('usedforsecurity', None)
        return _original_md5(*args, **kwargs)
    hashlib.md5 = _patched_md5

import streamlit as st
from groq import Groq
import httpx
import base64
import io
import os
import json
import re
import time
from datetime import date
from pathlib import Path
from dotenv import load_dotenv
import fitz
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import streamlit_analytics2 as streamlit_analytics

# --- CONFIG ---
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)
API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=API_KEY, http_client=httpx.Client(verify=False))

# --- FONT SETUP ---
font_path = os.path.join(os.path.dirname(__file__), "Noto_Sans_Tamil", "static", "NotoSansTamil-Regular.ttf")
if os.path.exists(font_path):
    pdfmetrics.registerFont(TTFont('NotoSansTamil', font_path))
    FONT = 'NotoSansTamil'
else:
    FONT = 'Helvetica'

# --- HELPERS ---
def extract_pdf_text(file_bytes, max_pages=10):
    pdf = fitz.open(stream=file_bytes, filetype="pdf")
    total_pages = len(pdf)
    text = ""
    start_page = min(3, total_pages - 1)
    for i in range(start_page, min(start_page + max_pages, total_pages)):
        page_text = pdf[i].get_text()
        if page_text.strip():
            text += f"\n--- Page {i+1} ---\n{page_text}"
    return text[:5000]

def extract_pdf_as_image(file_bytes):
    pdf = fitz.open(stream=file_bytes, filetype="pdf")
    total_pages = len(pdf)
    start_page = min(8, total_pages - 1)
    page = pdf[start_page]
    mat = fitz.Matrix(2.0, 2.0)
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("jpeg")
    return base64.b64encode(img_bytes).decode('utf-8')

def image_to_base64(file_bytes):
    return base64.b64encode(file_bytes).decode('utf-8')

def process_uploaded_file(uploaded_file):
    file_bytes = uploaded_file.read()
    if uploaded_file.type == "application/pdf":
        text = extract_pdf_text(file_bytes)
        if len(text.strip()) > 100:
            st.sidebar.success(f"✅ Text PDF loaded: {len(text)} chars")
            return text, None, "pdf_text"
        else:
            st.sidebar.success("✅ Scanned PDF loaded as image")
            image_b64 = extract_pdf_as_image(file_bytes)
            return None, image_b64, "pdf_image"
    else:
        st.sidebar.success("✅ Image loaded")
        image_b64 = image_to_base64(file_bytes)
        return None, image_b64, "image"

def get_age_profile(age, grade):
    if grade in ["Class 1", "Class 2"]:
        return """
VERY YOUNG LEARNER (Age 5-7):
- Use VERY simple words only
- Activities max 10 minutes
- Only 1-2 sentence instructions
- Fun games and drawings only
- Quiz questions must be YES/NO or one word answers
- Vocabulary max 3 very simple words per day
- Example activity: "Point to the picture and say the word"
"""
    elif grade in ["Class 3", "Class 4"]:
        return """
YOUNG LEARNER (Age 8-10):
- Use simple sentences
- Activities 15 minutes
- Mix of reading and fun activities
- Quiz questions can be short answers
- Vocabulary 3 simple words with easy meanings
- Example activity: "Read the paragraph and answer"
"""
    elif grade in ["Class 5", "Class 6"]:
        return """
INTERMEDIATE LEARNER (Age 10-12):
- Can handle paragraphs
- Activities 15-20 minutes
- Include some critical thinking
- Quiz questions need 2-3 sentence answers
- Vocabulary 3-5 words with meanings
- Example activity: "Read and summarize in own words"
"""
    else:
        return """
ADVANCED LEARNER (Age 12-15):
- Can handle complex text
- Activities 20-25 minutes
- Include analysis and evaluation
- Quiz questions need detailed answers
- Vocabulary includes subject-specific terms
- Example activity: "Analyze and compare concepts"
"""

def call_ai(prompt, image_b64=None):
    """Primary: Gemma 4 via Google GenAI. Fallback: Groq Llama."""
    google_key = os.getenv("GOOGLE_API_KEY")
    if google_key:
        try:
            from google import genai
            from google.genai import types
            g_client = genai.Client(api_key=google_key)

            for model in ["gemma-4-31b-it", "gemma-4-26b-a4b-it"]:
                for attempt in range(3):
                    try:
                        if image_b64:
                            response = g_client.models.generate_content(
                                model=model,
                                contents=[
                                    types.Part.from_bytes(
                                        data=base64.b64decode(image_b64),
                                        mime_type="image/jpeg"
                                    ),
                                    types.Part.from_text(text=prompt)
                                ]
                            )
                        else:
                            response = g_client.models.generate_content(
                                model=model,
                                contents=prompt
                            )
                        st.sidebar.success(f"✅ Powered by {model}")
                        return response.text
                    except Exception:
                        if attempt < 2:
                            time.sleep(2 ** attempt)
                        continue
        except Exception:
            pass

    st.sidebar.info("ℹ️ Using backup AI model")

    if image_b64:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                    {"type": "text", "text": prompt}
                ]
            }]
        )
    else:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )
    return response.choices[0].message.content

def parse_mcq_json(text):
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()
    match = re.search(r'\[[\s\S]*\]', text)
    if match:
        text = match.group(0)
    return json.loads(text)

def generate_pdf_report(name, age, grade, language, plan_text, blooms_text=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                           rightMargin=inch, leftMargin=inch,
                           topMargin=inch, bottomMargin=inch)

    title_style = ParagraphStyle('Title', fontName=FONT, fontSize=20,
        textColor=colors.HexColor('#1a5276'), spaceAfter=12, alignment=1)
    h1_style = ParagraphStyle('H1', fontName=FONT, fontSize=15,
        textColor=colors.HexColor('#1a5276'), spaceAfter=10)
    h2_style = ParagraphStyle('H2', fontName=FONT, fontSize=12,
        textColor=colors.HexColor('#2e86c1'), spaceAfter=8, spaceBefore=12)
    h3_style = ParagraphStyle('H3', fontName=FONT, fontSize=11,
        textColor=colors.HexColor('#1a5276'), spaceAfter=6, spaceBefore=8)
    normal_style = ParagraphStyle('Normal', fontName=FONT, fontSize=10,
        spaceAfter=4, leading=14)

    story = []
    story.append(Paragraph("Family Library AI Companion", title_style))
    story.append(Paragraph("Parent Report Card", h1_style))
    story.append(Spacer(1, 0.2*inch))

    profile_data = [
        ['Child Name', name],
        ['Age', f'{age} years'],
        ['Class', grade],
        ['Language', language],
    ]
    profile_table = Table(profile_data, colWidths=[2*inch, 4*inch])
    profile_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#2e86c1')),
        ('TEXTCOLOR', (0,0), (0,-1), colors.white),
        ('FONTNAME', (0,0), (-1,-1), FONT),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (1,0), (1,-1), [colors.HexColor('#eaf4fb'), colors.white]),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(profile_table)
    story.append(Spacer(1, 0.3*inch))

    story.append(Paragraph("7-Day Personalized Reading Plan", h2_style))
    for line in plan_text.split('\n'):
        line = line.strip().replace('**', '')
        if not line:
            story.append(Spacer(1, 0.05*inch))
            continue
        try:
            if any(line.startswith(d) for d in ['Day ', 'நாள் ', 'DAY ']):
                story.append(Paragraph(line, h3_style))
            elif line.startswith(('*', '-', '•')):
                story.append(Paragraph('• ' + line.lstrip('*-• '), normal_style))
            else:
                story.append(Paragraph(line, normal_style))
        except Exception:
            pass

    if blooms_text:
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph("Bloom's Taxonomy Questions", h2_style))
        for line in blooms_text.split('\n'):
            line = line.strip().replace('**', '')
            if not line:
                story.append(Spacer(1, 0.05*inch))
                continue
            try:
                if any(level in line for level in ['Remembering','Understanding','Applying',
                                                    'Analyzing','Evaluating','Creating',
                                                    'நினைவு','புரிதல்','பயன்பாடு']):
                    story.append(Paragraph(line, h3_style))
                elif line.startswith(('*', '-', '•')):
                    story.append(Paragraph('• ' + line.lstrip('*-• '), normal_style))
                else:
                    story.append(Paragraph(line, normal_style))
            except Exception:
                pass

    doc.build(story)
    buffer.seek(0)
    return buffer

# ═══════════════════════════════════════════════
# PAGE SETUP — must be first Streamlit call
# ═══════════════════════════════════════════════
st.set_page_config(page_title="Family Library AI Companion", page_icon="📚", layout="wide")

with streamlit_analytics.track():

    # --- PWA SUPPORT ---
    st.markdown("""
<head>
<link rel="manifest" href="/app/static/manifest.json">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="Family Library">
<meta name="theme-color" content="#1f77b4">
</head>
""", unsafe_allow_html=True)

    # --- MOBILE FRIENDLY CSS ---
    st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
    [data-testid="stSidebar"] { padding-top: 1rem; min-width: 280px; }
    /* Camera input styling */
    .stCameraInput > div {
        border: 2px dashed #1f77b4;
        border-radius: 10px;
        padding: 10px;
    }
    .stCameraInput button {
        background-color: #1f77b4 !important;
        color: white !important;
        font-size: 16px !important;
        padding: 12px 24px !important;
        border-radius: 8px !important;
        width: 100% !important;
    }
    /* Mobile friendly buttons */
    .stButton > button {
        width: 100%;
        padding: 12px;
        font-size: 15px;
        border-radius: 8px;
    }
    /* Better tab styling */
    .stTabs [data-baseweb="tab"] {
        font-size: 14px;
        padding: 8px 12px;
    }
</style>
""", unsafe_allow_html=True)

    st.title("📚 Family Library AI Companion")
    st.write("Personalized learning for every child — Powered by AI")

    # --- SESSION STATE ---
    defaults = {
        'plan_text': None,
        'blooms_text': None,
        'pdf_text_cache': None,
        'image_b64_cache': None,
        'file_type_cache': None,
        'last_file_name': None,
        'last_camera_photo': None,
        'roadmap_text': None,
        'test_questions': None,
        'test_answers': {},
        'test_submitted': False,
        'test_start_time': None,
        'test_active': False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # ═══════════════════════════════════════════════
    # SIDEBAR
    # ═══════════════════════════════════════════════
    st.sidebar.header("👤 Child Profile")
    name = st.sidebar.text_input("Child's Name", placeholder="Enter child's name")
    age = st.sidebar.number_input("Age", min_value=4, max_value=18, value=8)
    grade = st.sidebar.selectbox("Class", ["Class 1","Class 2","Class 3","Class 4",
                                            "Class 5","Class 6","Class 7","Class 8"], index=2)
    language = st.sidebar.selectbox("Preferred Language", ["English", "Tamil"])

    # --- FILE UPLOAD ---
    st.sidebar.header("📖 Upload Book")
    uploaded_file = st.sidebar.file_uploader(
        "Photo or PDF of book",
        type=["jpg", "jpeg", "png", "pdf"]
    )

    if uploaded_file is not None:
        if uploaded_file.name != st.session_state.last_file_name:
            pdf_text, image_b64, file_type = process_uploaded_file(uploaded_file)
            st.session_state.pdf_text_cache = pdf_text
            st.session_state.image_b64_cache = image_b64
            st.session_state.file_type_cache = file_type
            st.session_state.last_file_name = uploaded_file.name
            st.session_state.last_camera_photo = None
            # Clear all generated content on new upload
            st.session_state.plan_text = None
            st.session_state.blooms_text = None
            st.session_state.roadmap_text = None
            st.session_state.test_questions = None
            st.session_state.test_answers = {}
            st.session_state.test_submitted = False
            st.session_state.test_start_time = None
            st.session_state.test_active = False
    else:
        if st.session_state.last_file_name and not st.session_state.last_camera_photo:
            st.sidebar.info("Using previously loaded book")

    if st.session_state.last_file_name:
        st.sidebar.info(f"📚 Book: {st.session_state.last_file_name}")

    # --- CAMERA CAPTURE ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("📷 Or Take a Photo")
    st.sidebar.caption("Point your camera at any book page")
    camera_photo = st.sidebar.camera_input(
        "Take a photo of the book",
        help="Point camera at book cover or any page"
    )

    if camera_photo is not None:
        if st.session_state.last_camera_photo != camera_photo:
            st.session_state.last_camera_photo = camera_photo
            camera_bytes = camera_photo.getvalue()
            image_b64 = base64.b64encode(camera_bytes).decode('utf-8')
            st.session_state.image_b64_cache = image_b64
            st.session_state.file_type_cache = "image"
            st.session_state.pdf_text_cache = None
            st.session_state.last_file_name = None
            # Clear all generated content on new capture
            st.session_state.plan_text = None
            st.session_state.blooms_text = None
            st.session_state.roadmap_text = None
            st.session_state.test_questions = None
            st.session_state.test_answers = {}
            st.session_state.test_submitted = False
            st.session_state.test_start_time = None
            st.session_state.test_active = False
            st.sidebar.success("📸 Book photo captured! Now click Generate Reading Plan.")
            st.sidebar.image(camera_bytes, caption="Your book photo", use_container_width=True)

    def get_book_content():
        return (
            st.session_state.pdf_text_cache,
            st.session_state.image_b64_cache,
            st.session_state.file_type_cache
        )

    def has_book():
        return st.session_state.last_file_name or st.session_state.last_camera_photo

    # --- WELCOME MESSAGE ---
    if not has_book():
        st.info("""
    👋 **Welcome! Here's how to use this app:**

    1. 👤 Enter child's name, age and class in the **left sidebar**
    2. 📖 Upload a **book photo or PDF** — or use 📷 **Take a Photo** in the sidebar
    3. 📅 **Reading Plan** tab — Get a 7-day personalized reading plan
    4. 🧠 **Bloom's Questions** tab — Deep learning questions at all 6 levels
    5. 🗺️ **Concept Roadmap** tab — Visual step-by-step learning pathway
    6. 📝 **Self Analysis Test** tab — 15 MCQ quiz with 15-minute timer & scoring
    7. 📄 **Download Report** tab — Parent Report Card PDF
    """)

    # --- TABS ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📅 Reading Plan",
        "🧠 Bloom's Questions",
        "🗺️ Concept Roadmap",
        "📝 Self Analysis Test",
        "📄 Download Report",
    ])

    # ═══════════════════════════════════════════════
    # TAB 1 — READING PLAN
    # ═══════════════════════════════════════════════
    with tab1:
        st.header("Generate 7-Day Reading Plan")

        if st.button("🚀 Generate Reading Plan", key="gen_plan"):
            if not name:
                st.warning("Please enter the child's name in the sidebar!")
            else:
                with st.spinner("Creating personalized reading plan..."):
                    pdf_text, image_b64, file_type = get_book_content()
                    age_profile = get_age_profile(age, grade)

                    base_prompt = f"""You are an educational AI for rural Indian students.
A child named {name}, age {age}, in {grade}, prefers {language}.

{age_profile}

Generate a 7-day personalized reading plan following the above age profile strictly.
Include:
- Daily activities appropriate for this age
- 3 quiz questions at the right difficulty level
- 3 vocabulary words suitable for this age
- Tips for parents on how to help this age group
Format clearly for a parent to understand.
Respond in {language}."""

                    if pdf_text:
                        prompt = f"""The following is ACTUAL content from a real textbook.
Use ONLY this content to create the reading plan.
Do NOT invent stories or use other books.

===BOOK CONTENT===
{pdf_text}
===END===

{base_prompt}"""
                    elif image_b64:
                        prompt = f"""This is a page from a Tamil Nadu government school textbook.
Look carefully at ALL the text, topics, lessons, and content visible in this image.
Identify the specific subject, chapter names, and key concepts shown.
Use ONLY the actual content visible — specific lesson names, topics, exercises.
Do NOT talk about cover pages, index pages, or generic book structure.

{base_prompt}"""
                    else:
                        prompt = base_prompt

                    st.session_state.plan_text = call_ai(prompt, image_b64)
                    st.success("✅ Reading plan generated!")

        if st.session_state.plan_text:
            st.markdown(st.session_state.plan_text)

    # ═══════════════════════════════════════════════
    # TAB 2 — BLOOM'S QUESTIONS
    # ═══════════════════════════════════════════════
    with tab2:
        st.header("🧠 Bloom's Taxonomy Question Generator")
        st.write("Generates questions at all 6 thinking levels for deeper learning")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.info("🔵 **Level 1** Remembering\n\nRecall facts and basic concepts")
            st.info("🟢 **Level 2** Understanding\n\nExplain ideas in own words")
        with col2:
            st.info("🟡 **Level 3** Applying\n\nUse knowledge in new situations")
            st.info("🟠 **Level 4** Analyzing\n\nDraw connections and find patterns")
        with col3:
            st.info("🔴 **Level 5** Evaluating\n\nJustify decisions and opinions")
            st.info("🟣 **Level 6** Creating\n\nProduce new or original work")

        st.divider()

        if st.button("🧠 Generate Bloom's Questions", key="gen_blooms"):
            if not name:
                st.warning("Please enter the child's name in the sidebar!")
            else:
                with st.spinner("Generating Bloom's Taxonomy questions..."):
                    pdf_text, image_b64, file_type = get_book_content()
                    age_profile = get_age_profile(age, grade)

                    blooms_prompt = f"""You are an expert educational psychologist using Bloom's Taxonomy.
A child named {name}, age {age}, in {grade}, prefers {language}.

{age_profile}

CRITICAL: Generate ALL questions STRICTLY based on the book content provided.
Do NOT use generic examples or placeholder text like [specific story name].
Every single question must reference actual topics from the book.
Follow the age profile above strictly when setting question difficulty and format.

Generate questions for ALL 6 levels:
1. REMEMBERING - 3 questions (recall facts FROM THE BOOK)
2. UNDERSTANDING - 3 questions (explain FROM THE BOOK in own words)
3. APPLYING - 3 questions (apply FROM THE BOOK knowledge)
4. ANALYZING - 3 questions (analyze FROM THE BOOK topics)
5. EVALUATING - 3 questions (judge FROM THE BOOK ideas)
6. CREATING - 3 questions (create based on THE BOOK)

Each level: include parent activity + difficulty (Easy/Medium/Hard)
Respond in {language}."""

                    if pdf_text:
                        blooms_prompt = f"""ACTUAL textbook content below. Use ONLY this.
Do NOT use placeholder text like [specific story name from the book].

===BOOK CONTENT===
{pdf_text}
===END===

{blooms_prompt}"""
                    elif image_b64:
                        blooms_prompt = f"""Look at this book image carefully.
Use ONLY what you see in this book. No placeholders.

{blooms_prompt}"""

                    st.session_state.blooms_text = call_ai(blooms_prompt, image_b64)
                    st.success("✅ Bloom's questions generated!")

        if st.session_state.blooms_text:
            st.markdown(st.session_state.blooms_text)

    # ═══════════════════════════════════════════════
    # TAB 3 — CONCEPT ROADMAP
    # ═══════════════════════════════════════════════
    with tab3:
        st.header("🗺️ AI Concept Roadmap")
        st.write("A structured learning pathway from basic to advanced concepts")
        st.caption("Designed by S. Sivakumar, Former Principal, DIET Kancheepuram")

        st.info("""
**What is a Concept Roadmap?**
A step-by-step sequence that guides students from the most basic idea to advanced understanding.
Each step builds logically on the previous one.

*Example — Human Heart:*
Introduction → Location → External Structure → Internal Structure → Chambers → Valves → Blood Vessels → Blood Circulation → Functions → Application to Health
    """)

        if st.button("🗺️ Generate Concept Roadmap", key="gen_roadmap"):
            if not name:
                st.warning("Please enter the child's name in the sidebar!")
            elif not has_book():
                st.warning("Please upload a book or take a photo first!")
            else:
                with st.spinner("Analyzing content and building learning roadmap..."):
                    pdf_text, image_b64, file_type = get_book_content()

                    roadmap_prompt = f"""You are an expert educational designer. Analyze this book content and create a structured learning roadmap. Start from the most basic foundational concept and sequence all concepts logically so each step builds on the previous one. This is for a child named {name}, age {age}, grade {grade}. Respond in {language}.

Format EACH step EXACTLY like this (do not deviate):

**Step [N]: [Concept Name]**
📖 [One sentence explaining this concept clearly]
➡️ [One sentence on why this step comes before the next]

Generate between 8 and 12 steps, moving from foundational to advanced. Do not add any text before Step 1 or after the final step."""

                    if pdf_text:
                        roadmap_prompt = f"""===BOOK CONTENT===
{pdf_text}
===END===

{roadmap_prompt}"""
                    elif image_b64:
                        roadmap_prompt = f"""Look at this book image carefully and identify all the concepts present.

{roadmap_prompt}"""

                    st.session_state.roadmap_text = call_ai(roadmap_prompt, image_b64)
                    st.success("✅ Concept roadmap generated!")

        if st.session_state.roadmap_text:
            st.divider()
            st.subheader("📍 Your Learning Pathway")

            lines = st.session_state.roadmap_text.strip().split('\n')
            step_blocks = []
            current_block = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if re.match(r'\*{0,2}(Step|படி)\s*\d+', line, re.IGNORECASE):
                    if current_block:
                        step_blocks.append(current_block)
                    current_block = [line]
                else:
                    current_block.append(line)
            if current_block:
                step_blocks.append(current_block)

            bg_colors = [
                '#e8f4fd', '#e8f7e8', '#fff3e0', '#fce4ec', '#f3e5f5',
                '#e0f2f1', '#fff8e1', '#e8eaf6', '#f1f8e9', '#fbe9e7', '#e3f2fd', '#f9fbe7',
            ]
            border_colors = [
                '#2e86c1', '#27ae60', '#f39c12', '#c0392b', '#8e44ad',
                '#16a085', '#f57f17', '#3949ab', '#558b2f', '#bf360c', '#1565c0', '#827717',
            ]

            if len(step_blocks) >= 2:
                for i, block in enumerate(step_blocks):
                    bg = bg_colors[i % len(bg_colors)]
                    border = border_colors[i % len(border_colors)]

                    html_lines = []
                    for raw_line in block:
                        raw_line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', raw_line)
                        html_lines.append(raw_line)
                    block_html = '<br>'.join(html_lines)

                    st.markdown(f"""
<div style="
    background: {bg};
    border-left: 5px solid {border};
    border-radius: 10px;
    padding: 16px 20px;
    margin: 6px 0;
    font-size: 15px;
    line-height: 1.7;
">
{block_html}
</div>
""", unsafe_allow_html=True)

                    if i < len(step_blocks) - 1:
                        st.markdown("""
<div style="text-align:center; font-size:28px; color:#888; margin:2px 0;">↓</div>
""", unsafe_allow_html=True)
            else:
                st.markdown(st.session_state.roadmap_text)

    # ═══════════════════════════════════════════════
    # TAB 4 — SELF ANALYSIS TEST
    # ═══════════════════════════════════════════════
    BLOOMS_DISTRIBUTION = {
        "Remembering": 4,
        "Understanding": 3,
        "Applying": 3,
        "Analyzing": 2,
        "Evaluating": 2,
        "Creating": 1,
    }
    BLOOMS_EMOJI = {
        "Remembering": "🔵", "Understanding": "🟢", "Applying": "🟡",
        "Analyzing": "🟠", "Evaluating": "🔴", "Creating": "🟣",
    }
    BLOOMS_TIPS = {
        "Remembering": "Re-read the chapter and make flashcards for key facts.",
        "Understanding": "Explain the topic in your own words to a parent.",
        "Applying": "Practice similar problems from the textbook exercises.",
        "Analyzing": "Draw diagrams and compare concepts to find connections.",
        "Evaluating": "Discuss: 'What do you think about...?' with a parent.",
        "Creating": "Write a short story or make a project using what you learned.",
    }
    TEST_DURATION = 900  # 15 minutes in seconds

    with tab4:
        st.header("📝 Self Analysis Test")
        st.write("15 MCQ questions from your book content — 15 minute timed test")
        st.caption("Designed by S. Sivakumar, Former Principal, DIET Kancheepuram")

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("🔵 Remembering", "4 Qs")
            st.metric("🟢 Understanding", "3 Qs")
        with col_b:
            st.metric("🟡 Applying", "3 Qs")
            st.metric("🟠 Analyzing", "2 Qs")
        with col_c:
            st.metric("🔴 Evaluating", "2 Qs")
            st.metric("🟣 Creating", "1 Q")

        st.divider()

        # ── GENERATE & START ──
        if not st.session_state.test_active:
            if st.button("🎯 Generate & Start Test", key="gen_test", type="primary"):
                if not name:
                    st.warning("Please enter the child's name in the sidebar!")
                elif not has_book():
                    st.warning("Please upload a book or take a photo first!")
                else:
                    with st.spinner("Generating 15 MCQ questions..."):
                        pdf_text, image_b64, file_type = get_book_content()

                        content_for_prompt = pdf_text if pdf_text else (
                            "Use the book content visible in this image" if image_b64 else
                            "General grade-appropriate content"
                        )

                        today = date.today().isoformat()

                        test_prompt = f"""You are an expert educational psychologist. Generate exactly 15 MCQ questions from this content using Bloom's Taxonomy distribution: Remembering(4), Understanding(3), Applying(3), Analyzing(2), Evaluating(2), Creating(1). Each question must have 4 options A/B/C/D. Return as JSON array with fields: question, options(array of 4 strings), correct_answer(one of "A","B","C","D"), blooms_level, difficulty(Easy/Medium/Hard). Make questions randomized and different each time. Today's date is {today} — use this to ensure variety across days. Content: {content_for_prompt}. Child: {name}, age {age}, {grade}. Language: {language}. Return JSON only, no other text.

Example format:
[
  {{
    "question": "What is...?",
    "options": ["Option A text", "Option B text", "Option C text", "Option D text"],
    "correct_answer": "A",
    "blooms_level": "Remembering",
    "difficulty": "Easy"
  }}
]"""

                        raw = call_ai(test_prompt, image_b64)

                        try:
                            questions = parse_mcq_json(raw)
                            if not isinstance(questions, list) or len(questions) < 5:
                                st.error("AI returned too few questions. Please try again.")
                                st.stop()
                            st.session_state.test_questions = questions[:15]
                            st.session_state.test_answers = {}
                            st.session_state.test_submitted = False
                            st.session_state.test_start_time = time.time()
                            st.session_state.test_active = True
                            st.rerun()
                        except (json.JSONDecodeError, ValueError):
                            st.error("Could not parse questions from AI. Please try again.")
                            with st.expander("Raw AI response"):
                                st.text(raw)

        # ── ACTIVE TEST ──
        if st.session_state.test_active and st.session_state.test_questions:
            questions = st.session_state.test_questions

            if not st.session_state.test_submitted:
                # Timer display
                elapsed = time.time() - st.session_state.test_start_time
                remaining = max(0, TEST_DURATION - int(elapsed))
                mins, secs = divmod(remaining, 60)
                timer_color = "#c0392b" if remaining < 120 else "#27ae60"

                st.markdown(f"""
<div style="
    background:{timer_color};
    color:white;
    text-align:center;
    padding:12px;
    border-radius:10px;
    font-size:26px;
    font-weight:bold;
    margin-bottom:20px;
">
⏱️ Time Remaining: {mins:02d}:{secs:02d}
</div>
""", unsafe_allow_html=True)

                if remaining == 0:
                    for i in range(len(questions)):
                        val = st.session_state.get(f"q_{i}")
                        if val:
                            st.session_state.test_answers[i] = val[0]
                    st.session_state.test_submitted = True
                    st.rerun()

                st.subheader(f"Answer all {len(questions)} questions:")

                for i, q in enumerate(questions):
                    blooms = q.get("blooms_level", "")
                    diff = q.get("difficulty", "")
                    emoji = BLOOMS_EMOJI.get(blooms, "⚪")

                    st.markdown(
                        f"**Q{i+1}. {q['question']}** &nbsp;&nbsp; {emoji} _{blooms}_ &nbsp;|&nbsp; _{diff}_"
                    )

                    opts = q.get("options", [])
                    labels = [f"{chr(65+j)}) {opt}" for j, opt in enumerate(opts)]

                    selected = st.radio(
                        f"q{i+1}",
                        options=labels,
                        key=f"q_{i}",
                        label_visibility="collapsed",
                    )

                    if selected:
                        st.session_state.test_answers[i] = selected[0]

                    st.divider()

                if st.button("✅ Submit Test", key="submit_test", type="primary"):
                    for i in range(len(questions)):
                        val = st.session_state.get(f"q_{i}")
                        if val:
                            st.session_state.test_answers[i] = val[0]
                    st.session_state.test_submitted = True
                    st.rerun()

            # ── RESULTS ──
            if st.session_state.test_submitted:
                questions = st.session_state.test_questions
                answers = st.session_state.test_answers

                score = 0
                weak = {}
                strong = {}

                for i, q in enumerate(questions):
                    correct = q.get("correct_answer", "")
                    given = answers.get(i, "")
                    lvl = q.get("blooms_level", "Unknown")
                    if given == correct:
                        score += 1
                        strong[lvl] = strong.get(lvl, 0) + 1
                    else:
                        weak[lvl] = weak.get(lvl, 0) + 1

                total = len(questions)
                pct = int((score / total) * 100) if total > 0 else 0

                if pct >= 80:
                    score_color, grade_label = "#27ae60", "Excellent! 🌟"
                elif pct >= 60:
                    score_color, grade_label = "#f39c12", "Good Job! 👍"
                else:
                    score_color, grade_label = "#c0392b", "Keep Practising! 💪"

                st.markdown(f"""
<div style="
    background:{score_color};
    color:white;
    text-align:center;
    padding:28px;
    border-radius:15px;
    font-size:30px;
    font-weight:bold;
    margin:16px 0;
">
{grade_label}<br>
Score: {score} / {total} &nbsp;({pct}%)
</div>
""", unsafe_allow_html=True)

                st.subheader("📊 Performance by Bloom's Level")
                for lvl in BLOOMS_DISTRIBUTION:
                    right = strong.get(lvl, 0)
                    wrong = weak.get(lvl, 0)
                    lvl_total = right + wrong
                    if lvl_total > 0:
                        lvl_pct = int((right / lvl_total) * 100)
                        status = "✅" if lvl_pct >= 60 else "⚠️ Needs work"
                        emoji = BLOOMS_EMOJI.get(lvl, "")
                        st.write(f"{emoji} **{lvl}**: {right}/{lvl_total} correct ({lvl_pct}%) {status}")

                if weak:
                    st.subheader("📚 Revision Suggestions")
                    for lvl, count in weak.items():
                        tip = BLOOMS_TIPS.get(lvl, "Review this topic again.")
                        emoji = BLOOMS_EMOJI.get(lvl, "")
                        st.info(f"{emoji} **{lvl}** ({count} wrong): {tip}")

                st.subheader("📋 Answer Review")
                for i, q in enumerate(questions):
                    correct = q.get("correct_answer", "")
                    given = answers.get(i, "")
                    opts = q.get("options", [])
                    letter_to_idx = {"A": 0, "B": 1, "C": 2, "D": 3}

                    correct_idx = letter_to_idx.get(correct, 0)
                    correct_text = opts[correct_idx] if correct_idx < len(opts) else correct

                    if given == correct:
                        st.success(f"Q{i+1}: ✅ Correct — {correct}) {correct_text}")
                    else:
                        given_idx = letter_to_idx.get(given, -1)
                        given_text = opts[given_idx] if 0 <= given_idx < len(opts) else "Not answered"
                        st.error(
                            f"Q{i+1}: ❌ You chose {given}) {given_text} | Correct: {correct}) {correct_text}"
                        )

                st.divider()
                if st.button("🔄 Take New Test", key="new_test"):
                    st.session_state.test_questions = None
                    st.session_state.test_answers = {}
                    st.session_state.test_submitted = False
                    st.session_state.test_start_time = None
                    st.session_state.test_active = False
                    st.rerun()

    # ═══════════════════════════════════════════════
    # TAB 5 — DOWNLOAD REPORT
    # ═══════════════════════════════════════════════
    with tab5:
        st.header("📄 Download Parent Report Card")

        if not st.session_state.plan_text and not st.session_state.blooms_text:
            st.warning("Please generate a Reading Plan and/or Bloom's Questions first!")
        else:
            st.success("Your report is ready to download!")
            if st.session_state.plan_text:
                st.write("✅ Reading Plan included")
            if st.session_state.blooms_text:
                st.write("✅ Bloom's Taxonomy Questions included")

            if st.button("📄 Generate PDF Report"):
                with st.spinner("Creating PDF..."):
                    pdf_buffer = generate_pdf_report(
                        name, age, grade, language,
                        st.session_state.plan_text or "",
                        st.session_state.blooms_text
                    )
                    st.download_button(
                        label="⬇️ Download Report Card PDF",
                        data=pdf_buffer,
                        file_name=f"{name}_Family_Library_Report.pdf",
                        mime="application/pdf"
                    )

    # ═══════════════════════════════════════════════
    # GLOBAL TIMER TICK — auto-refresh while test runs
    # ═══════════════════════════════════════════════
    if st.session_state.test_active and not st.session_state.test_submitted:
        time.sleep(1)
        st.rerun()
