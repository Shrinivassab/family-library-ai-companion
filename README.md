# 📚 Family Library AI Companion
### Hackathon: Gemma 4 Good | Kaggle × Google DeepMind

AI-powered personalized reading plans for children — built for rural India, open to the world.

## 🎯 Problem
In rural Tamil Nadu, India, millions of children face a devastating learning gap during after-school hours, weekends, and holidays. Parents cannot guide their children's reading because they don't know what reading level each book is, and children have no personalized study plan.

But this challenge isn't unique to Tamil Nadu — **any child, anywhere in the world, faces the same problem.** Family Library AI Companion was built in India, but designed for the world.

## 💡 Solution
Family Library AI Companion uses AI to:
- Scan home books via photo or PDF upload
- Profile the child by name, age, class, and language preference
- Generate 7-day personalized reading plans with daily activities, quizzes, and vocabulary
- Generate Bloom's Taxonomy questions at all 6 thinking levels
- Produce a downloadable Parent Report Card PDF
- **Respond in any language the family is most comfortable in**
- Work for any child, any book, anywhere in the world

## 🏆 Real World Impact
Built with retired Principal S. Sivakumar who runs a real Family Library program in Tiruchirappalli, Tamil Nadu. Training conducted May 9, 2026 at Subramaniyapuram Reading Centre with real children and parents from Sundararaj Nagar and Highways Colony. WhatsApp groups already created to continue engagement beyond the session.

## 🚀 Features
- 📸 **Book Upload** — photo or PDF of any book
- 📅 **7-Day Reading Plan** — daily activities, quizzes, vocabulary words
- 🧠 **Bloom's Taxonomy** — all 6 cognitive levels (Remember → Create)
- 🌐 **Any Language** — Tamil, English, or any language the family prefers
- 📄 **Parent Report Card** — downloadable PDF with Tamil font support
- 👨‍👩‍👧 **Parent Tips** — age-appropriate home learning guidance
- 🎓 **4 Age Profiles** — Class 1-2, 3-4, 5-6, 7-8 with different difficulty levels
- 🔁 **AI Fallback** — Gemma 4 primary, Groq as automatic backup

## 🛠️ Tech Stack
- **Frontend:** Streamlit
- **Primary AI:** Gemma 4 (gemma-4-31b-it) via Google GenAI
- **Fallback AI:** Groq (llama-3.3-70b-versatile + llama-4-scout vision)
- **PDF Processing:** PyMuPDF + ReportLab
- **Tamil Font:** NotoSansTamil
- **Language:** Python 3.11+

## 📦 Installation
```bash
git clone https://github.com/Shrinivassab/family-library-ai-companion.git
cd family-library-ai-companion
pip install -r requirements.txt
```

Create `.env` file:

GROQ_API_KEY=your-groq-api-key-here
GOOGLE_API_KEY=your-google-api-key-here

Run:
```bash
streamlit run app.py
```

## 🌍 Who Can Use This?
Originally built for rural Tamil Nadu, this app works for **any child, any book, in any language.**

The AI backbone supports 100+ languages natively — any regional language can be unlocked based on community need. A parent in Brazil, a teacher in Kenya, a family in rural India, a student in rural Mexico — if you have a book and a child who needs guidance, this app is for you.

> **Built in Tamil Nadu. Designed for the world.**

## 🗺️ Roadmap — What's Coming Next

- 🌏 **Any Language, Anywhere** — The AI supports 100+ languages. Any regional language can be added based on community need — Swahili in Kenya, Arabic in Egypt, Spanish in Mexico, Telugu in Andhra Pradesh, or any other. The architecture is language-agnostic by design.
- 📊 **Progress Tracker** — parents can log daily reading and track improvement over weeks
- 🏫 **Classroom Mode** — teacher uploads one book, generates plans for entire class at once
- 📱 **WhatsApp Bot** — send a book photo via WhatsApp, receive a reading plan instantly (ideal for low-data rural areas)
- 🔊 **Audio Reading Plans** — text-to-speech for parents who struggle to read
- 🧩 **Gamification** — streaks, badges, and rewards to keep children motivated
- 📈 **Learning Analytics** — visualize which Bloom's levels a child is strong or weak at
- 🤝 **Volunteer Network** — connect reading centres across Tamil Nadu and beyond on one platform
- 🌐 **Offline Mode** — downloadable app for areas with no consistent internet
- 🏷️ **Book Scanner** — scan barcode or spine to auto-identify book without uploading full PDF

## 👥 Credits
- **S. Sivakumar** — Retired Principal, DIET Kancheepuram, founder of Family Library Program
- **Family Library Program** — Tiruchirappalli District, Tamil Nadu, India
- Built for the **Gemma 4 Good Hackathon** — Kaggle × Google DeepMind