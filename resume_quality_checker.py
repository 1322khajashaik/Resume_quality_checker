import streamlit as st
import os
import tempfile
import fitz  # PyMuPDF
import docx2txt
import pdfminer.high_level
import language_tool_python
import pandas as pd
import re

# ======= Improved Helper Functions ========

def extract_text_pdf(path):
    try:
        text = ''
        with fitz.open(path) as pdf:
            for page in pdf:
                text += page.get_text()
        return text
    except Exception:
        return pdfminer.high_level.extract_text(path)  # fallback

def extract_text_docx(path):
    return docx2txt.process(path)

def extract_text_txt(path):
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()

def extract_text(file):
    ext = os.path.splitext(file.name)[1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(file.read())
        tmp_path = tmp.name

    if ext == '.pdf':
        text = extract_text_pdf(tmp_path)
    elif ext in ['.doc', '.docx']:
        text = extract_text_docx(tmp_path)
    elif ext == '.txt':
        text = extract_text_txt(tmp_path)
    else:
        text = ""
    os.remove(tmp_path)
    return text

def check_sections(text):
    checks = {}
    # 1. Email detection
    emails = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text)
    checks['Email'] = bool(emails)
    # 2. Phone detection (common patterns)
    checks['Phone'] = bool(
        re.findall(r'(\+?\d{1,3}[^\S\r\n]*)?(\(?\d{3,4}\)?[^\S\r\n]*)?\d{3,4}[^\S\r\n]*\d{3,4}', text)
    )
    # 3. Professional Email
    corp_email = any([
        bool(re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.(com|org|net|co)\b", mail)) and
        not re.search(r"@(gmail|yahoo|hotmail|outlook)\.", mail)
        for mail in emails
    ])
    checks['Professional Email'] = corp_email
    # 4. LinkedIn
    linkedin_pattern = r"(https?://)?(www\.)?linkedin\.com/(in|pub)/[A-z0-9_\-\.]+"
    checks['LinkedIn'] = bool(re.search(linkedin_pattern, text))
    # 5. Education
    checks['Education'] = any(
        kw in text.lower()
        for kw in ['education', 'degree', 'bachelor', 'master', 'phd', 'b.sc', 'm.sc', 'mba', 'btech', 'b.e.', 'b.e', 'mtech']
    )
    # 6. Experience
    checks['Experience'] = any(
        kw in text.lower()
        for kw in ['experience', 'work history', 'employment', 'positions', 'career profile', 'professional experience']
    )
    # 7. Skills
    checks['Skills'] = 'skill' in text.lower()
    return checks

def count_years_experience(text):
    # Try to extract years from date patterns
    years = re.findall(r'((?:19|20)\d{2})', text)
    if years:
        years = [int(y) for y in years]
        if len(years) >= 2:
            return max(years) - min(years)
    # Fallback to "X years" pattern
    match = re.findall(r'(\d+)\s+years?', text)
    if match:
        return max([int(m) for m in match])
    return 0

def spell_check(text):
    tool = language_tool_python.LanguageTool('en-US')
    matches = tool.check(text)
    error_words = set([m.context[m.offset:m.offset + m.errorLength] for m in matches])
    return len(error_words), error_words

def word_page_count(text):
    word_count = len(text.split())
    page_count = max(1, int(word_count / 500) + (1 if word_count % 500 else 0))
    return word_count, page_count

def buzzword_check(text):
    # EXTENSIVE BUZZWORD LIST (can be dynamically extended)
    buzzwords = [
        # Soft skills & adjectives
        'team player','self-motivated','leadership','synergy','proactive','hardworking','dynamic','results-driven',
        'detail-oriented','innovative','strategic','goal oriented','motivated','passionate','responsible',
        'organized','adaptable','communication','problem solving','critical thinking','flexible','fast learner',
        # Common tech skills (add more as needed)
        'python','java','c++','c#','javascript','sql','excel','tableau','powerbi','aws','azure','docker','kubernetes',
        'react','node','git','jira','linux','agile','scrum','html','css','typescript',
        # Popular certifications/roles
        'pmp','six sigma','aws certified','data analyst','business analyst','product manager','devops','cloud',
        'machine learning','artificial intelligence','deep learning','nlp','data science','web development',
        # Misc
        'project management','client relations','stakeholder engagement','negotiation','training', 'mentoring'
    ]
    found = []
    text_lower = text.lower()
    for bw in buzzwords:
        # Use word boundaries for short buzzwords, substring for phrases.
        pattern = re.escape(bw)
        if len(bw.split()) == 1:
            if re.search(r'\b'+pattern+r'\b', text_lower): 
                found.append(bw)
        else:
            if bw in text_lower: 
                found.append(bw)
    return found

def calculate_score(sections, spell_errors, word_count, page_count, buzzwords):
    score = 0
    score += sum(list(sections.values())) * 10
    score -= min(spell_errors, 5) * 2
    if sections['Professional Email']:
        score += 5
    if 300 <= word_count <= 1000:
        score += 10
    if buzzwords:
        score += 3 + len(buzzwords)  # reward for more buzzwords
    if page_count > 2:
        score -= 5
    return max(0, min(100, score))

# ======= Streamlit App Layout =======

st.set_page_config('Resume Quality Checker', layout='wide')
st.title("📄 Resume Quality Checker")

uploaded_files = st.file_uploader("Upload one or more resumes (PDF, DOCX, TXT):", type=['pdf', 'docx', 'doc', 'txt'], accept_multiple_files=True)

if uploaded_files:
    results = []
    for file in uploaded_files:
        st.subheader(f"{file.name}")
        text = extract_text(file) or ""
        if not text or len(text) < 100:
            st.warning("❗ Failed to extract sufficient text. Please check the file.")
            continue
        sections = check_sections(text)
        years_exp = count_years_experience(text)
        spell_errors, error_words = spell_check(text)
        word_count, page_count = word_page_count(text)
        buzzwords_found = buzzword_check(text)
        score = calculate_score(sections, spell_errors, word_count, page_count, buzzwords_found)

        # Display Dashboard
        col1, col2, col3 = st.columns([2,1,1])
        with col1:
            st.markdown(f"**Resume Score:** <span style='font-size:2em;'>{score}/100</span>", unsafe_allow_html=True)
        with col2:
            st.metric("Words", word_count)
        with col3:
            st.metric("Estimated Pages", page_count)

        with st.expander('Section Checklist'):
            for k, v in sections.items():
                st.write(f'{"✅" if v else "❌"} {k}')
        st.write(f"**Years of Experience Detected:** {years_exp}")
        st.write(f"**Buzzwords Present:** {', '.join(buzzwords_found) if buzzwords_found else 'None'}")
        st.write(f"**Spelling Errors:** {spell_errors}")
        if spell_errors:
            st.write("Misspelled Words:", ", ".join(error_words))

        if page_count > 2 and word_count > 1000:
            st.warning("Resume is longer than recommended for entry or junior level (2 pages). Consider trimming.")

        # Store for batch result/export
        results.append({
            "File": file.name, "Score": score, "Pages": page_count,
            "Words": word_count, "YearsExp": years_exp,
            "SpellErrors": spell_errors, "Buzzwords": ', '.join(buzzwords_found)
        })

    # Batch Table & Export
    if len(results) > 1:
        df = pd.DataFrame(results)
        st.dataframe(df)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Results as CSV", csv, "resume_analysis.csv", "text/csv")
