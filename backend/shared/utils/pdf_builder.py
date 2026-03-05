from __future__ import annotations
from io import BytesIO
from typing import List, Dict
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

def build_rav_pdf(title: str, subtitle: str, rows: List[Dict]) -> bytes:
    styles = getSampleStyleSheet(); bio = BytesIO()
    doc = SimpleDocTemplate(bio, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    story = [Paragraph(title, styles["Title"]), Spacer(1,8), Paragraph(subtitle, styles["Normal"]), Spacer(1,12)]
    data = [["Datum","Firma","Stelle","Ort","Kanal","Status"]]
    for r in rows:
        data.append([r.get("date",""), r.get("company",""), r.get("title",""), r.get("location",""), r.get("channel",""), r.get("status","")])
    tbl = Table(data, repeatRows=1)
    tbl.setStyle(TableStyle([("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),9),("GRID",(0,0),(-1,-1),0.5,colors.grey),("BACKGROUND",(0,0),(-1,0),colors.whitesmoke)]))
    story.append(tbl); doc.build(story)
    return bio.getvalue()
