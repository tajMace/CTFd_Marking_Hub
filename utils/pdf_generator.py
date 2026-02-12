"""
Student performance report PDF generator.
Creates a PDF with student's marking feedback for each submission.
"""

from io import BytesIO
from datetime import datetime
from html import escape as html_escape

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def generate_student_report_pdf(student_name, student_email, submissions, ctf_name="CTF", subtitle="Performance Report"):
    """
    Generate a PDF report of student's marked submissions.
    
    Args:
        student_name (str): Student's full name
        student_email (str): Student's email address
        submissions (list): List of dicts with keys:
            - challenge: Challenge name
            - submitted_at: Submission date string
            - flag: The submitted flag/answer
            - mark: Mark score (0-100)
            - comment: Tutor feedback
        ctf_name (str): Name of the CTF platform
        subtitle (str): Report subtitle (e.g., "Performance Report" or "Week1 Performance Report")
        
    Returns:
        BytesIO: PDF file as bytes
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError("reportlab is required for PDF generation. Install with: pip install reportlab")
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=0.75*inch, leftMargin=0.75*inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    
    # Create styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=HexColor('#1a1a1a'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=HexColor('#555555'),
        spaceAfter=12,
        alignment=TA_CENTER,
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=HexColor('#1a1a1a'),
        spaceAfter=10,
        spaceBefore=10,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        textColor=HexColor('#333333'),
        spaceAfter=6,
    )
    
    # Build content
    content = []
    
    # Header
    safe_ctf_name = html_escape(ctf_name)
    safe_student_name = html_escape(student_name)
    safe_student_email = html_escape(student_email)
    safe_subtitle = html_escape(subtitle)
    
    content.append(Paragraph(f"{safe_ctf_name} - {safe_subtitle}", title_style))
    content.append(Paragraph(
        f"Student: <b>{safe_student_name}</b> ({safe_student_email}) | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        subtitle_style
    ))
    content.append(Spacer(1, 0.2*inch))
    
    # Summary stats
    if submissions:
        marked = sum(1 for s in submissions if s.get('mark') is not None)
        avg_mark = sum(s.get('mark', 0) for s in submissions if s.get('mark') is not None) / marked if marked > 0 else 0
        
        summary_text = f"<b>Summary:</b> {len(submissions)} submission(s), {marked} marked, Average: {avg_mark:.1f}%"
        content.append(Paragraph(summary_text, normal_style))
        content.append(Spacer(1, 0.2*inch))
    
    # Submissions table
    if submissions:
        content.append(Paragraph("Detailed Feedback", heading_style))
        
        for idx, sub in enumerate(submissions, 1):
            challenge = html_escape(sub.get('challenge', 'Unknown Challenge'))
            mark = sub.get('mark')
            comment = html_escape(sub.get('comment', ''))
            submitted_at = html_escape(sub.get('submitted_at', 'N/A'))
            flag = html_escape(sub.get('flag', ''))
            
            # Create mini table for this submission
            mark_text = f"{mark}%" if mark is not None else "Not marked"
            mark_color = HexColor('#27ae60') if mark is not None and mark >= 70 else HexColor('#e74c3c') if mark is not None else HexColor('#95a5a6')
            
            submission_data = [
                [Paragraph(f"<b>{idx}. {challenge}</b>", normal_style)],
                [Paragraph(f"<b>Submitted:</b> {submitted_at}", normal_style)],
                [Paragraph(f"<b>Your answer:</b> {flag[:100]}{'...' if len(flag) > 100 else ''}", normal_style)],
                [Paragraph(f"<b>Mark: <font color='{mark_color.hexval()}'>{mark_text}</font></b>", normal_style)],
                [Paragraph(f"<b>Feedback:</b> {comment if comment else '(No feedback provided)'}", normal_style)],
            ]
            
            table = Table(submission_data, colWidths=[6.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), HexColor('#f5f5f5')),
                ('BORDER', (0, 0), (-1, -1), 1, HexColor('#cccccc')),
                ('PADDING', (0, 0), (-1, -1), 10),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            
            content.append(table)
            content.append(Spacer(1, 0.2*inch))
    else:
        content.append(Paragraph("No submissions to display.", normal_style))
    
    # Footer
    content.append(Spacer(1, 0.3*inch))
    content.append(Paragraph(
        "This is an automated report. For questions about your marks, please contact your tutor.",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=9, textColor=HexColor('#999999'), alignment=TA_CENTER)
    ))
    
    # Build PDF
    doc.build(content)
    buffer.seek(0)
    return buffer
