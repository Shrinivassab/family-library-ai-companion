import streamlit as st
from groq import Groq
from PIL import Image
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
API_KEY = os.getenv("GROQ_API_KEY", "your-actual-key-here")
client = Groq(api_key=API_KEY)

# --- FONT SETUP ---
font_path = os.path.join(os.path.dirname(__file__), "Noto_Sans_Tamil", "static", "NotoSansTamil-Regular.ttf")
if os.path.exists(font_path):
    pdfmetrics.registerFont(TTFont('NotoSansTamil', font_path))
    FONT = 'NotoSansTamil'
else:
    FONT = 'Helvetica'

# --- PAGE SETUP ---
st.set_page_config(page_title="Family Library AI Companion", page_icon="📚", layout="wide")
st.title("📚 Family Library AI Companion")
st.write("Personalized reading plans for every child — Powered by AI")

# --- SIDEBAR: CHILD PROFILE ---
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

# --- HELPERS ---
def extract_pdf_text(file_bytes, max_pages=5):
    pdf = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for i, page in enumerate(pdf):
        if i >= max_pages:
            break
        text += page.get_text()
    return text[:3000]

def image_to_base64(file_bytes):
    return base64.b64encode(file_bytes).decode('utf-8')

def get_book_content():
    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        if uploaded_file.type == "application/pdf":
            return extract_pdf_text(file_bytes), None, "pdf"
        else:
            return None, image_to_base64(file_bytes), "image"
    return None, None, None

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

    # Profile table
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

    # Reading Plan
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

    # Bloom's Section
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

# --- SESSION STATE ---
if 'plan_text' not in st.session_state:
    st.session_state.plan_text = None
if 'blooms_text' not in st.session_state:
    st.session_state.blooms_text = None

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📅 7-Day Reading Plan", "🧠 Bloom's Taxonomy Questions", "📄 Download Report"])

# ============================================================
# TAB 1: READING PLAN
# ============================================================
with tab1:
    st.header("Generate 7-Day Reading Plan")

    if st.button("🚀 Generate Reading Plan", key="gen_plan"):
        if not name:
            st.warning("Please enter the child's name in the sidebar!")
        else:
            with st.spinner("Creating personalized reading plan..."):
                if uploaded_file:
                    uploaded_file.seek(0)
                pdf_text, image_b64, file_type = get_book_content()

                base_prompt = f"""You are an educational AI for rural Indian students.
A child named {name}, age {age}, in {grade}, prefers {language}.
Generate a 7-day personalized reading plan with:
- Daily activities (15-20 minutes each)
- 3 quiz questions per day
- 3 vocabulary words per day
- Tips for parents
Format clearly for a parent to understand.
Respond in {language}."""

                if pdf_text:
                    prompt = f"Book content:\n{pdf_text}\n\nBased on this book, {base_prompt}"
                elif image_b64:
                    prompt = f"Look at this book image and {base_prompt}"
                else:
                    prompt = base_prompt

                st.session_state.plan_text = call_ai(prompt, image_b64)
                st.success("✅ Reading plan generated!")

    if st.session_state.plan_text:
        st.markdown(st.session_state.plan_text)

# ============================================================
# TAB 2: BLOOM'S TAXONOMY
# ============================================================
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
                if uploaded_file:
                    uploaded_file.seek(0)
                pdf_text, image_b64, file_type = get_book_content()

                blooms_prompt = f"""You are an expert educational psychologist using Bloom's Taxonomy.
A child named {name}, age {age}, in {grade}, prefers {language}.

IMPORTANT: Generate ALL questions STRICTLY based on the book content provided.
Do NOT use generic examples or unrelated topics like Harry Potter or The Jungle Book.
Every question must reference specific topics, chapters, or concepts from the book.

Generate questions covering ALL 6 levels of Bloom's Taxonomy:

1. REMEMBERING - 3 questions (recall specific facts FROM THE BOOK)
2. UNDERSTANDING - 3 questions (explain concepts FROM THE BOOK in own words)
3. APPLYING - 3 questions (apply knowledge FROM THE BOOK in new situations)
4. ANALYZING - 3 questions (analyze topics FROM THE BOOK, find patterns)
5. EVALUATING - 3 questions (judge and justify ideas FROM THE BOOK)
6. CREATING - 3 questions (create something new based on THE BOOK content)

For each level also provide:
- One parent activity related to THE BOOK topic
- Difficulty: Easy / Medium / Hard

Age-appropriate for {age} year old in {grade}.
Respond in {language}."""

                if pdf_text:
                    blooms_prompt = f"Book content:\n{pdf_text}\n\n{blooms_prompt}"
                elif image_b64:
                    blooms_prompt = f"Based on this book image, {blooms_prompt}"

                st.session_state.blooms_text = call_ai(blooms_prompt, image_b64)
                st.success("✅ Bloom's questions generated!")

    if st.session_state.blooms_text:
        st.markdown(st.session_state.blooms_text)

# ============================================================
# TAB 3: DOWNLOAD REPORT
# ============================================================
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
