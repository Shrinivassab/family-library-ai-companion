# 📚 Family Library AI Companion
### Hackathon: Gemma 4 Good | Kaggle × Google DeepMind

AI-powered personalized reading plans for rural Indian children.

## 🎯 Problem
In rural Tamil Nadu, children have no personalized study plans and parents cannot guide them effectively after school and during holidays.

## 💡 Solution
Family Library AI Companion uses AI to:
- Scan home books via photo or PDF upload
- Generate 7-day personalized reading plans
- Generate Bloom's Taxonomy questions at all 6 thinking levels
- Produce downloadable Parent Report Card PDF
- Support Tamil and English languages

## 🏆 Real World Impact
Built with retired Principal S. Sivakumar who runs a real Family Library program in Tiruchirappalli, Tamil Nadu. Training conducted May 9, 2026 at Subramaniyapuram Reading Centre with real children and parents.

## 🚀 Features
- 📸 Book Upload — photo or PDF
- 📅 7-Day Reading Plan — activities, quizzes, vocabulary
- 🧠 Bloom's Taxonomy — all 6 thinking levels
- 🌐 Bilingual — Tamil and English
- 📄 Parent Report Card — downloadable PDF
- 👨‍👩‍👧 Parent Tips — home learning guidance

## 🛠️ Tech Stack
- Frontend: Streamlit
- AI: Groq (llama-3.3-70b + llama-4-scout vision)
- PDF: PyMuPDF + ReportLab
- Language: Python 3.11+

## 📦 Installation
```bash
git clone https://github.com/Shrinivassab/family-library-ai-companion.git
cd family-library-ai-companion
pip install -r requirements.txt
```

Create `.env` file:

GROQ_API_KEY=your-groq-api-key-here

Run:
```bash
streamlit run app.py
```

## 👥 Credits
- S. Sivakumar — Retired Principal, DIET Kancheepuram
- Family Library Program — Tiruchirappalli District, Tamil Nadu