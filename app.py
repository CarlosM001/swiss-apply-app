import streamlit as st
import os
import sys
import re
import requests
from io import BytesIO 
from docx import Document 
from dotenv import load_dotenv
from supabase import create_client
from pypdf import PdfReader

# Pfad-Setup für Backend
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.shared.utils.docx_builder import build_cover_letter_docx, SwissLetterHeader
from backend.api.llm.prompt_builder import build_single_call_prompt
from backend.api.llm.llm_client import generate_cover_letter_body_only

# ==========================================
# 1. INITIALISIERUNG & SETUP
# ==========================================
load_dotenv()
st.set_page_config(page_title="Swiss-Apply KI", page_icon="🇨🇭", layout="wide")

# STARTUP-DESIGN (CSS)
st.markdown("""
<style>
[data-testid="stToolbar"] {visibility: hidden !important;}
footer {visibility: hidden !important;}
.block-container {padding-top: 2rem;}
[data-testid="stExpander"] {border: 1px solid #D52B1E; border-radius: 10px;}
.stButton>button {border-radius: 8px;}
</style>
""", unsafe_allow_html=True)

# Supabase Verbindung
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase = create_client(supabase_url, supabase_key)

# ==========================================
# 2. SESSION STATE (GEDÄCHTNIS)
# ==========================================
if 'selected_company' not in st.session_state: st.session_state.selected_company = ""
if 'selected_job' not in st.session_state: st.session_state.selected_job = ""
if 'selected_desc' not in st.session_state: st.session_state.selected_desc = ""
if 'user' not in st.session_state: st.session_state.user = None

# Token Handling für Persistenz
if 'access_token' in st.session_state and 'refresh_token' in st.session_state:
    try:
        supabase.auth.set_session(st.session_state.access_token, st.session_state.refresh_token)
    except: pass

# Passwort-Reset Abfang-Logik (Aus der E-Mail)
if "code" in st.query_params:
    try:
        res = supabase.auth.exchange_code_for_session({"auth_code": st.query_params["code"]})
        st.session_state.user = res.user
        st.session_state.access_token = res.session.access_token
        st.session_state.refresh_token = res.session.refresh_token
        st.query_params.clear()
        st.success("✅ Verifizierung erfolgreich! Bitte setze im Profil dein neues Passwort.")
    except: st.error("Der Link ist ungültig oder abgelaufen.")

# ==========================================
# 3. HILFSFUNKTIONEN
# ==========================================
def create_rav_docx(data):
    doc = Document()
    doc.add_heading('RAV Nachweis Arbeitsbemühungen', 0)
    table = doc.add_table(rows=1, cols=5)
    table.style = 'Table Grid'
    hdr = table.rows[0].cells
    hdr[0].text, hdr[1].text, hdr[2].text, hdr[3].text, hdr[4].text = 'Datum', 'Firma', 'Stelle', 'Form', 'Status'
    for item in data:
        row = table.add_row().cells
        row[0].text = str(item.get('applied_at', ''))[:10]
        row[1].text = item.get('company_name', '')
        row[2].text = item.get('job_title', '')
        row[3].text = 'Online'
        row[4].text = 'Offen'
    stream = BytesIO()
    doc.save(stream)
    return stream.getvalue()

# ==========================================
# 4. LOGIN / REGISTRIERUNG
# ==========================================
if st.session_state.user is None:
    st.title("🇨🇭 Swiss-Apply KI")
    t1, t2, t3 = st.tabs(["🔐 Anmelden", "📝 Registrieren", "🔑 Passwort vergessen"])
    
    with t1:
        with st.form("l_form"):
            e_in = st.text_input("E-Mail")
            p_in = st.text_input("Passwort", type="password")
            if st.form_submit_button("Anmelden", use_container_width=True):
                try:
                    res = supabase.auth.sign_in_with_password({"email": e_in, "password": p_in})
                    st.session_state.user = res.user
                    st.session_state.access_token = res.session.access_token
                    st.session_state.refresh_token = res.session.refresh_token
                    st.rerun()
                except Exception as e: st.error(f"Login Fehler: {e}")
    
    with t2:
        with st.form("r_form"):
            ne = st.text_input("E-Mail")
            np = st.text_input("Passwort", type="password")
            ic = st.text_input("Einladungscode", type="password")
            if st.form_submit_button("Konto erstellen", use_container_width=True):
                if ic == "SWISS2026":
                    try:
                        supabase.auth.sign_up({"email": ne, "password": np})
                        st.success("Erfolg! Bitte prüfe dein E-Mail-Postfach.")
                    except Exception as e: st.error(str(e))
                else: st.error("Einladungscode falsch.")
                
    with t3:
        st.write("Gib hier deine E-Mail ein, um einen Link zum Zurücksetzen zu erhalten.")
        with st.form("pw_reset_mail_form"):
            reset_email = st.text_input("Deine E-Mail-Adresse")
            if st.form_submit_button("Reset-Link senden", use_container_width=True):
                try:
                    supabase.auth.reset_password_for_email(reset_email)
                    st.info("Falls die E-Mail bei uns registriert ist, wurde ein Link gesendet.")
                except Exception as e: st.error(str(e))

# ==========================================
# 5. HAUPTPROGRAMM (EINGELOGGT)
# ==========================================
else:
    st.sidebar.title("🇨🇭 Swiss-Apply")
    st.sidebar.write(f"Eingeloggt: **{st.session_state.user.email}**")
    if st.sidebar.button("Logout"):
        supabase.auth.sign_out()
        st.session_state.clear()
        st.rerun()

    # Profil laden
    try:
        p_res = supabase.table("profiles").select("*").eq("id", st.session_state.user.id).single().execute()
        p_data = p_res.data if p_res.data else {}
    except: p_data = {}

    cur_name = p_data.get("full_name", "")
    cur_city = p_data.get("city", "")
    cur_resume = p_data.get("resume_text", "")

    # SEKTION 1: PROFIL & LEBENSLAUF
    with st.expander("👤 Mein Profil & Lebenslauf"):
        with st.form("prof_form"):
            st.subheader("1. Kontaktdaten")
            c1, c2 = st.columns(2)
            fn = c1.text_input("Name", value=cur_name)
            st_n = c1.text_input("Strasse", value=p_data.get("street", ""))
            ct = c2.text_input("PLZ/Ort", value=cur_city)
            ph = c2.text_input("Telefon", value=p_data.get("phone", ""))
            
            st.subheader("2. Lebenslauf (Für die KI)")
            if cur_resume:
                st.success("✅ Ein Lebenslauf ist bereits gespeichert! (Überschreiben durch neuen Upload möglich)")
            up_pdf = st.file_uploader("Lebenslauf hochladen (Nur PDF)", type=["pdf"])
            
            if st.form_submit_button("Profil & Lebenslauf speichern"):
                up_dict = {"id": st.session_state.user.id, "full_name": fn, "street": st_n, "city": ct, "phone": ph}
                if up_pdf:
                    reader = PdfReader(up_pdf)
                    txt = ""
                    for page in reader.pages: txt += page.extract_text() + "\n"
                    up_dict["resume_text"] = txt
                supabase.table("profiles").upsert(up_dict).execute()
                st.success("Profil erfolgreich gesichert!")
                st.rerun()

    with st.expander("🔑 Mein Passwort ändern"):
        with st.form("pwd_reset_form"):
            new_pwd = st.text_input("Neues Passwort (min. 6 Zeichen)", type="password")
            if st.form_submit_button("Passwort aktualisieren"):
                try:
                    supabase.auth.update_user({"password": new_pwd})
                    st.success("Passwort erfolgreich geändert!")
                except Exception as e: st.error(f"Fehler beim Ändern: {e}")

    # SEKTION 2: LIVE JOB-BOARD
    st.divider()
    st.header("🎯 Live Job-Börse")
    cj1, cj2 = st.columns(2)
    q_job = cj1.text_input("Welchen Job suchst du?", placeholder="z.B. Maurer")
    q_loc = cj2.text_input("Wo?", value=cur_city if cur_city else "Schweiz")
    
    JOOBLE_KEY = "19414f40-206a-4cf6-ac1b-0106e96f7f8d"
    
    if st.button("Jobs live suchen"):
        with st.spinner("Suche Inserate..."):
            try:
                url = f"https://ch.jooble.org/api/{JOOBLE_KEY}"
                resp = requests.post(url, json={"keywords": q_job, "location": q_loc})
                if resp.status_code == 200:
                    jobs = resp.json().get("jobs", [])
                    if not jobs: st.info("Für diese Suchanfrage wurden keine Jobs gefunden.")
                    else:
                        st.success(f"{len(jobs)} brandneue Stellen gefunden!")
                        for i, j in enumerate(jobs[:5]):
                            with st.container(border=True):
                                st.subheader(j.get("title"))
                                st.write(f"🏢 **{j.get('company')}** | 📍 {j.get('location')}")
                                snip = j.get("snippet", "").replace("<b>", "").replace("</b>", "")
                                st.write(f"> {snip}")
                                b1, b2 = st.columns(2)
                                b1.link_button("🌐 Inserat öffnen", j.get("link", "#"), use_container_width=True)
                                
                                # BOMENSICHERE DATENÜBERGABE
                                if b2.button("📄 Daten übernehmen", key=f"take_{i}", use_container_width=True):
                                    st.session_state.selected_company = j.get("company", "")
                                    st.session_state.selected_job = j.get("title", "")
                                    st.session_state.selected_desc = snip
                                    st.rerun()
                else: st.error(f"API Fehler: {resp.status_code}")
            except Exception as e: st.error(str(e))

    # SEKTION 3: KI-GENERATOR
    st.divider()
    st.header("🚀 KI-Bewerbungstool")
    st.write("Wähle oben einen Job aus oder gib die Daten manuell ein.")
    col_g1, col_g2 = st.columns(2)
    
    # HIER GREIFEN WIR DIREKT AUF DEN SPEICHER ZU (value=...)
    g_comp = col_g1.text_input("Firma", value=st.session_state.selected_company, placeholder="z.B. Swisscom")
    g_title = col_g2.text_input("Stelle", value=st.session_state.selected_job, placeholder="z.B. Projektleiter")
    g_desc = st.text_area("Stellenbeschreibung", value=st.session_state.selected_desc, height=150)

    if st.button("Bewerbung generieren & prüfen"):
        if not g_comp or not g_title: st.warning("Bitte Firma und Jobtitel angeben.")
        else:
            with st.spinner("KI schreibt und prüft Rechtschreibung..."):
                try:
                    head = SwissLetterHeader(full_name=cur_name, street=p_data.get("street", ""), postal_code="", city=cur_city, email=st.session_state.user.email)
                    
                    # 1. Erstellung des Briefs
                    prompt = build_single_call_prompt({"personal": {"full_name": cur_name}}, {"title": g_title, "company": g_comp, "location": "CH", "requirements": {"keywords": [g_desc[:100]]}})
                    if cur_resume:
                        prompt += f"\n\nWICHTIGE ZUSATZINFO: Hier ist der Lebenslauf des Bewerbers. Beziehe echte Erfahrungen daraus ein:\n{cur_resume}"
                    
                    initial_res = generate_cover_letter_body_only(prompt=prompt)
                    
                    # 2. AUTOMATISCHE RECHTSCHREIBPRÜFUNG & CH-ANPASSUNG
                    check_prompt = f"""
                    Du bist ein Schweizer Korrektor. Korrigiere den folgenden Bewerbungstext auf Rechtschreibung, Grammatik und Stil.
                    WICHTIG: Verwende Schweizer Rechtschreibung (KEIN 'ß', sondern immer 'ss').
                    Behalte den Inhalt exakt bei, verbessere nur die Form.
                    
                    TEXT:
                    {initial_res.body_text}
                    """
                    corrected_res = generate_cover_letter_body_only(prompt=check_prompt)
                    
                    # 3. DOCX Erstellung & Speichern
                    docx_out = build_cover_letter_docx(header=head, recipient_block=f"{g_comp}\nPersonalabteilung", place_and_date=f"{cur_city or 'Schweiz'}, 05.03.2026", subject=f"Bewerbung als {g_title}", body_text=corrected_res.body_text, signature_name=cur_name)
                    
                    fn_clean = re.sub(r'\W+', '', g_comp)
                    path = f"web_generiert/{st.session_state.user.id}/{fn_clean}.docx"
                    supabase.storage.from_("letters").upload(path=path, file=docx_out, file_options={"upsert": "true"})
                    supabase.table("applications").insert({"user_id": st.session_state.user.id, "company_name": g_comp, "job_title": g_title, "status": "generated"}).execute()
                    
                    st.success("✅ Brief generiert, auf Rechtschreibung geprüft und archiviert!")
                    st.download_button("📂 Korrigiertes Word laden", data=docx_out, file_name=f"Bewerbung_{fn_clean}.docx")
                except Exception as e: st.error(str(e))

    # SEKTION 4: ARCHIV & RAV
    st.divider()
    st.header("📊 Dein Archiv & RAV-Nachweis")
    try:
        a_res = supabase.table("applications").select("*").eq("user_id", st.session_state.user.id).order("applied_at", desc=True).execute()
        apps = a_res.data if a_res.data else []
        
        c_met1, c_met2 = st.columns(2)
        c_met1.metric("Bewerbungen (Gesamt)", len(apps), f"{len(apps)}/10 Ziel")
        c_met2.progress(min(len(apps)/10, 1.0), text="Fortschritt RAV-Ziel")

        if apps and st.button("📄 RAV-Beiblatt generieren"):
            st.download_button("📥 RAV Nachweis laden", data=create_rav_docx(apps), file_name="RAV_Nachweis.docx")
        
        st.subheader("📂 Gespeicherte Dokumente")
        user_path = f"web_generiert/{st.session_state.user.id}/"
        files = supabase.storage.from_("letters").list(path=user_path)
        if files:
            for f in files:
                if f['name'] == '.empty': continue
                with st.container(border=True):
                    cl1, cl2 = st.columns([4, 1])
                    cl1.write(f"📄 **{f['name']}**")
                    f_dl = supabase.storage.from_("letters").download(f"{user_path}{f['name']}")
                    cl2.download_button("📥 Laden", data=f_dl, file_name=f['name'], key=f"dl_{f['name']}")
        else:
            st.info("Noch keine Dokumente generiert.")
    except: pass