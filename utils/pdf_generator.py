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
            - is_technical: True if TECH challenge
        ctf_name (str): Name of the CTF platform
        subtitle (str): Report subtitle (e.g., "Performance Report" or "Week1 Performance Report")
        
    Returns:
        BytesIO: PDF file as bytes
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError("reportlab is required for PDF generation. Install with: pip install reportlab")
    
    print(f"[PDF GEN] Starting PDF generation for {student_name}, {len(submissions)} submissions", flush=True)
    
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
        technical_subs = [s for s in submissions if s.get('is_technical')]
        non_technical_subs = [s for s in submissions if not s.get('is_technical')]

        marked_subs = [s for s in submissions if s.get('mark') is not None]
        marked = len(marked_subs)
        
        # Calculate average as percentage
        if marked > 0:
            percentages = [
                (s.get('mark', 0) / s.get('challengeValue', 100)) * 100 if s.get('challengeValue', 100) != 0 else 0
                for s in marked_subs
            ]
            avg_mark = sum(percentages) / len(percentages) if len(percentages) > 0 else 0
        else:
            avg_mark = 0

        summary_text = (
            f"<b>Summary:</b> {len(submissions)} submission(s) "
            f"({len(non_technical_subs)} non-technical, {len(technical_subs)} technical), "
            f"{marked} marked, Average: {avg_mark:.1f}%"
        )
        content.append(Paragraph(summary_text, normal_style))
        content.append(Spacer(1, 0.2*inch))
    
    def render_submissions_section(section_title, section_submissions):
        # Mark percentage to name mapping
        percent_to_name = {
            0: "Incomplete",
            30: "Attempted",
            60: "Okay",
            90: "Great",
            100: "HoF",
        }
        print(f"[PDF GEN] Rendering section '{section_title}' with {len(section_submissions)} submissions", flush=True)
        if not section_submissions:
            content.append(Paragraph(f"{section_title}: None", normal_style))
            content.append(Spacer(1, 0.15*inch))
            return

        content.append(Paragraph(section_title, heading_style))

        for idx, sub in enumerate(section_submissions, 1):
            print(f"[PDF GEN] Processing submission {idx}: {sub.get('challenge')}", flush=True)
            challenge = html_escape(sub.get('challenge', 'Unknown Challenge'))
            mark = sub.get('mark')
            mark_name = sub.get('mark_name') or percent_to_name.get(mark, str(mark) if mark is not None else None)
            challenge_value = sub.get('challengeValue', 100)
            comment = html_escape(sub.get('comment', ''))
            submitted_at = html_escape(sub.get('submitted_at', 'N/A'))
            flag = html_escape(sub.get('flag', ''))
            is_technical = sub.get('is_technical', False)

            # Calculate percentage
            if mark is not None:
                percentage = (mark / challenge_value) * 100 if challenge_value else 0
                mark_text = f"{mark_name} ({percentage:.1f}%)"
                mark_color = HexColor('#27ae60') if percentage >= 70 else HexColor('#e74c3c')
            else:
                mark_text = "Not marked"
                mark_color = HexColor('#95a5a6')

            # Technical submissions show only name, submitted time, and mark
            if is_technical:
                submission_data = [
                    [Paragraph(f"<b>{idx}. {challenge}</b>", normal_style)],
                    [Paragraph(f"<b>Submitted:</b> {submitted_at}", normal_style)],
                    [Paragraph(f"<b>Mark: <font color='{mark_color.hexval()}'>{mark_text}</font></b>", normal_style)],
                ]
            else:
                # Non-technical submissions show full details
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

    # Submissions sections
    if submissions:
        print(f"[PDF GEN] Building detailed feedback section with {len(submissions)} submissions", flush=True)
        content.append(Paragraph("Detailed Feedback", heading_style))
        technical_subs = [s for s in submissions if s.get('is_technical')]
        non_technical_subs = [s for s in submissions if not s.get('is_technical')]
        
        print(f"[PDF GEN] Technical: {len(technical_subs)}, Non-technical: {len(non_technical_subs)}", flush=True)

        render_submissions_section("non-technical", non_technical_subs)
        
        # Add page break before technical section if both sections exist
        if non_technical_subs and technical_subs:
            content.append(PageBreak())
        
        render_submissions_section("technical", technical_subs)
    else:
        content.append(Paragraph("No submissions to display.", normal_style))
    
    # Footer
    content.append(Spacer(1, 0.3*inch))
    content.append(Paragraph(
        "This is an automated report. For questions about your marks, please contact your tutor.",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=9, textColor=HexColor('#999999'), alignment=TA_CENTER)
    ))
    
    # Build PDF
    print(f"[PDF GEN] Building PDF with {len(content)} content elements", flush=True)
    try:
        doc.build(content)
        print(f"[PDF GEN] PDF build successful, buffer size: {buffer.tell()}", flush=True)
    except Exception as e:
        print(f"[PDF GEN ERROR] Failed to build PDF: {e}", flush=True)
        import traceback
        print(f"[PDF GEN ERROR] Traceback: {traceback.format_exc()}", flush=True)
        raise
    buffer.seek(0)
    return buffer
