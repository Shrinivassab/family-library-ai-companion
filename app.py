import streamlit as st
from groq import Groq
import base64
import io
import os
from dotenv import load_dotenv
import fitz
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# --- CONFIG ---
load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=API_KEY)

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
    
    # Try to find a good content page (skip cover, copyright, index)
    # Usually content starts around page 8-12
    start_page = min(8, total_pages - 1)
    
    page = pdf[start_page]
    mat = fitz.Matrix(2.0, 2.0)  # higher zoom for better quality
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("jpeg")
    return base64.b64encode(img_bytes).decode('utf-8')

def image_to_base64(file_bytes):
    return base64.b64encode(file_bytes).decode('utf-8')

def process_uploaded_file(uploaded_file):
    """Process any uploaded file and return (pdf_text, image_b64, file_type)"""
    file_bytes = uploaded_file.read()
    
    if uploaded_file.type == "application/pdf":
        # Try text extraction first
        text = extract_pdf_text(file_bytes)
        if len(text.strip()) > 100:
            # Good text PDF
            st.sidebar.success(f"✅ Text PDF loaded: {len(text)} chars")
            return text, None, "pdf_text"
        else:
            # Scanned/image PDF — convert to image
            st.sidebar.success("✅ Scanned PDF loaded as image")
            image_b64 = extract_pdf_as_image(file_bytes)
            return None, image_b64, "pdf_image"
    else:
        # Regular image upload
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

# --- PAGE SETUP ---
st.set_page_config(page_title="Family Library AI Companion", page_icon="📚", layout="wide")
st.title("📚 Family Library AI Companion")
st.write("Personalized reading plans for every child — Powered by AI")

# --- SESSION STATE ---
if 'plan_text' not in st.session_state:
    st.session_state.plan_text = None
if 'blooms_text' not in st.session_state:
    st.session_state.blooms_text = None
if 'pdf_text_cache' not in st.session_state:
    st.session_state.pdf_text_cache = None
if 'image_b64_cache' not in st.session_state:
    st.session_state.image_b64_cache = None
if 'file_type_cache' not in st.session_state:
    st.session_state.file_type_cache = None
if 'last_file_name' not in st.session_state:
    st.session_state.last_file_name = None

# --- SIDEBAR ---
st.sidebar.header("👤 Child Profile")
name = st.sidebar.text_input("Child's Name", value="Priya")
age = st.sidebar.number_input("Age", min_value=4, max_value=18, value=8)
grade = st.sidebar.selectbox("Class", ["Class 1","Class 2","Class 3","Class 4",
                                        "Class 5","Class 6","Class 7","Class 8"], index=2)
language = st.sidebar.selectbox("Preferred Language", ["English", "Tamil"])

st.sidebar.header("📖 Upload Book")
uploaded_file = st.sidebar.file_uploader(
    "Photo or PDF of book",
    type=["jpg", "jpeg", "png", "pdf"]
)

# Process file only when new file uploaded
if uploaded_file is not None:
    if uploaded_file.name != st.session_state.last_file_name:
        pdf_text, image_b64, file_type = process_uploaded_file(uploaded_file)
        st.session_state.pdf_text_cache = pdf_text
        st.session_state.image_b64_cache = image_b64
        st.session_state.file_type_cache = file_type
        st.session_state.last_file_name = uploaded_file.name
        # Clear previous results when new file uploaded
        st.session_state.plan_text = None
        st.session_state.blooms_text = None
else:
    if st.session_state.last_file_name:
        st.sidebar.info("Using previously loaded book")

if st.session_state.last_file_name:
    st.sidebar.info(f"📚 Book: {st.session_state.last_file_name}")

def get_book_content():
    return (
        st.session_state.pdf_text_cache,
        st.session_state.image_b64_cache,
        st.session_state.file_type_cache
    )

# --- WELCOME MESSAGE ---
if not st.session_state.last_file_name:
    st.info("""
    👋 **Welcome! Here's how to use this app:**

    1. 👤 Enter child's name, age and class in the **left sidebar**
    2. 📖 Upload a **book photo or PDF** in the sidebar
    3. Click **Generate Reading Plan** for a 7-day plan
    4. Click **Bloom's Questions** for deeper learning questions
    5. Download the **Parent Report Card** PDF
    """)

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📅 7-Day Reading Plan", "🧠 Bloom's Taxonomy Questions", "📄 Download Report"])

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

with tab3:
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