from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak


def build_report(payload):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=14*mm, leftMargin=14*mm, topMargin=14*mm, bottomMargin=14*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Small', parent=styles['BodyText'], fontSize=8, leading=10, textColor=colors.HexColor('#5c6575')))
    story = [Paragraph('Developer Skill Drift Report', styles['Title']), Paragraph(f"{payload.get('repository','')} · {payload.get('developer','')}", styles['Heading2']), Spacer(1, 8)]
    results = payload.get('results', [])
    alerts = sum(1 for r in results if r.get('alert'))
    avg = sum(float(r.get('drift_score',0)) for r in results)/len(results) if results else 0
    story.append(Table([["Events", payload.get('events_collected',0), "Dimensions", len(results), "Active drift", alerts, "Avg MSDI", f"{avg:.1f}"]], style=[('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#eef2ff')),('BOX',(0,0),(-1,-1),0.5,colors.HexColor('#dbe3ff')),('INNERGRID',(0,0),(-1,-1),0.25,colors.HexColor('#dbe3ff')),('ALIGN',(0,0),(-1,-1),'CENTER'),('FONTNAME',(0,0),(-1,-1),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),8)]))
    story.append(Spacer(1, 12))
    table = [["Category","Current","Baseline","MSDI","Trajectory","Alert"]]
    for r in results:
        table.append([r['category'],f"{r['current_score']:.1f}",f"{r['baseline_mean']:.1f}",f"{r['drift_score']:.1f}",r['trajectory'].replace('-',' '),"YES" if r['alert'] else "No"])
    story.append(Table(table, repeatRows=1, style=[('BACKGROUND',(0,0),(-1,0),colors.HexColor('#182033')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#d9dee8')),('FONTSIZE',(0,0),(-1,-1),8),('ALIGN',(1,1),(-1,-1),'CENTER'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f8f9fc')])]))
    for r in results:
        story += [Spacer(1,10), Paragraph(r['category'], styles['Heading2']), Paragraph(f"Trajectory: <b>{r['trajectory'].replace('-',' ')}</b> · Slope: {r['slope']:.2f} points/period · Drift Index: {r['drift_score']:.1f}/100", styles['BodyText'])]
        story.append(Paragraph('Why: ' + ' '.join(r.get('explanation', [])), styles['Small']))
        story.append(Paragraph('Recommendation: ' + r.get('recommendation',''), styles['Small']))
        if r.get('forecast',{}).get('points'):
            f = r['forecast']['points']
            ft = [["Forecast","Predicted","Lower","Upper"]] + [[p['period'],f"{p['predicted']:.1f}",f"{p['lower']:.1f}",f"{p['upper']:.1f}"] for p in f]
            story.append(Spacer(1,5)); story.append(Table(ft, style=[('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eef2ff')),('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#d9dee8')),('FONTSIZE',(0,0),(-1,-1),8)]))
    doc.build(story)
    return buf.getvalue()
