import streamlit as st
import os
import tempfile
import fitz  # PyMuPDF
import docx2txt
import pdfminer.high_level
import language_tool_python
import pandas as pd
import re
from spellchecker import SpellChecker

# === Section Keywords ===
SECTION_KEYWORDS = {
    "experience": ["experience", "work history", "employment", "professional experience"],
    "education": ["education", "academic", "university", "college", "degree"],
    "skills": ["skills", "technical skills", "competencies", "proficiencies"],
    "contact": ["email", "phone", "contact", "linkedin"]
}

# === Expanded Buzzwords ===
BUZZWORDS = [
    "team player", "self-motivated", "leadership", "python", "communication",
    "project management", "problem solving", "machine learning", "data analysis",
    "cloud", "aws", "azure", "docker", "kubernetes", "tensorflow", "pytorch",
    "nlp", "deep learning", "sql", "mongodb", "html", "css", "javascript", "react",
    "git", "agile", "scrum", "devops", "rest api", "fastapi", "django", "flask",
    "debugging", "testing", "unit test", "version control", "ci/cd", "oop", "design patterns"
]

PRO_EMAIL_DOMAINS = ["gmail.com", "yahoo.com", "hotmail.com"]

# === File Parsing ===
def extract_text_from_file(uploaded_file):
    if uploaded_file.name.endswith(".txt"):
        return uploaded_file.read().decode("utf-8"), 1
    elif uploaded_file.name.endswith(".pdf"):
        text = ""
        with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
            for page in doc:
                text += page.get_text()
            return text, len(doc)
    elif uploaded_file.name.endswith((".doc", ".docx")):
        return docx2txt.process(uploaded_file), 1
    return "", 0

# === Section Detection ===
def find_sections(text):
    found = {}
    text = text.lower()
    for section, keywords in SECTION_KEYWORDS.items():
        found[section] = any(k in text for k in keywords)
    return found

# === Years of Experience Detection ===
def detect_experience_years(text):
    patterns = [
        r'(\d+)\s*years?\s*(of)?\s*experience',
        r'(\d+)\+\s*years?'
    ]
    max_years = 0
    for pattern in patterns:
        matches = re.findall(pattern, text.lower())
        for match in matches:
            if isinstance(match, tuple):
                match = match[0]
            try:
                max_years = max(max_years, int(match))
            except:
                pass
    return max_years

# === Email and Phone Detection ===
def extract_email_and_phone(text):
    email = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    phone = re.search(r"\+?\d[\d\s\-]{8,}\d", text)
    return email.group(0) if email else None, phone.group(0) if phone else None

# === Professional Email Check ===
def is_professional_email(email):
    if email:
        domain = email.split('@')[-1].lower()
        return domain not in PRO_EMAIL_DOMAINS
    return False

# === LinkedIn Detection ===
def has_linkedin(text):
    return bool(re.search(r"(https?:\/\/)?(www\.)?linkedin\.com\/in\/[a-zA-Z0-9\-_]+", text.lower()))

# === Spell Checker (no whitelist) ===
def count_spelling_errors(text):
    spell = SpellChecker()
    words = re.findall(r'\b\w+\b', text.lower())
    misspelled = spell.unknown(words)
    return len(misspelled), list(misspelled)

# === Resume Length ===
def check_resume_length(text):
    words = text.split()
    return len(words)

# === Buzzword Detection ===
def detect_buzzwords(text):
    found = [word for word in BUZZWORDS if word in text.lower()]
    return found

# === Score Calculation ===
def calculate_score(sections, email, phone, professional_email, linkedin, spelling_errors, pages):
    score = 0
    if all(sections.values()): score += 30
    if email and phone: score += 10
    if professional_email: score += 10
    if linkedin: score += 5
    if spelling_errors <= 5: score += 10
    if pages <= 2: score += 10
    return min(score, 100)

# === Streamlit UI ===
def main():
    st.set_page_config(page_title="Resume Quality Checker", layout="centered")
    st.title("💼 Advanced Resume Quality Checker")
    uploaded_file = st.file_uploader("Upload Resume", type=["txt", "pdf", "doc", "docx"])

    if uploaded_file:
        text, pages = extract_text_from_file(uploaded_file)

        sections = find_sections(text)
        email, phone = extract_email_and_phone(text)
        professional_email = is_professional_email(email)
        linkedin = has_linkedin(text)
        exp_years = detect_experience_years(text)
        spelling_errors, misspelled_words = count_spelling_errors(text)
        word_count = check_resume_length(text)
        buzzwords_found = detect_buzzwords(text)
        score = calculate_score(sections, email, phone, professional_email, linkedin, spelling_errors, pages)

        st.header("📊 Resume Analysis Report")
        st.markdown(f"**✅ Completeness Score:** {score}/100")

        with st.expander("📂 Section Presence"):
            for sec, found in sections.items():
                st.write(f"{'✓' if found else '✗'} {sec.title()}")

        with st.expander("📧 Contact Info"):
            st.write(f"**Email:** {email or 'Not found'}")
            st.write(f"**Phone:** {phone or 'Not found'}")
            st.write(f"**Professional Email:** {'Yes' if professional_email else 'No'}")
            st.write(f"**LinkedIn:** {'✓' if linkedin else '✗'}")

        with st.expander("📈 Experience"):
            st.write(f"**Years of Experience Detected:** {exp_years} years")

        with st.expander("🔍 Spell Check"):
            st.write(f"**Spelling Errors:** {spelling_errors}")
            if misspelled_words:
                st.write(f"**Misspelled Words:** {', '.join(misspelled_words[:10])}...")

        with st.expander("📏 Length & Keywords"):
            st.write(f"**Total Words:** {word_count}")
            st.write(f"**Total Pages:** {pages}")
            st.write(f"**Buzzwords Found:** {', '.join(buzzwords_found) if buzzwords_found else 'None'}")

if __name__ == '__main__':
    main()
