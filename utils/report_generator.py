"""
Utility functions for generating and sending student reports.
"""

from datetime import datetime, timedelta
from CTFd.models import db, Users, Submissions
from CTFd.utils.email import sendmail
from CTFd.utils import get_config
from ..models import MarkingSubmission, StudentReport
from .pdf_generator import generate_student_report_pdf
import logging

logger = logging.getLogger(__name__)


def get_student_submissions_for_report(user_id, category=None):
    """
    Get all marked submissions for a student.
    Optionally filter by challenge category (e.g., 'Week1', 'Week2').
    
    Args:
        user_id (int): Student user ID
        category (str): Optional category to filter by
        
    Returns:
        list: of dicts with submission info
    """
    from CTFd.models import Submissions, Users, Challenges
    
    student = Users.query.get(user_id)
    if not student:
        print(f"[REPORT DEBUG] Student {user_id} not found", flush=True)
        return []
    
    query = (
        MarkingSubmission.query
        .join(Submissions, MarkingSubmission.submission_id == Submissions.id)
        .join(Challenges, Submissions.challenge_id == Challenges.id)
        .filter(Submissions.user_id == user_id)
    )
    
    if category:
        query = query.filter(Challenges.category == category)
    
    marking_subs = query.all()
    print(f"[REPORT DEBUG] Found {len(marking_subs)} marking submissions for user {user_id}", flush=True)
    
    report_data = []
    for marking_sub in marking_subs:
        sub = marking_sub.submission
        challenge = sub.challenge
        challenge_name = challenge.name if challenge else "Unknown"
        stripped_name = challenge_name.lstrip()
        is_technical = stripped_name.upper().startswith("TECH")

        print(f"[REPORT DEBUG] Processing submission {marking_sub.id}: challenge={challenge_name}, mark={marking_sub.mark}, is_technical={is_technical}", flush=True)

        if not is_technical and marking_sub.mark is None:
            print(f"[REPORT DEBUG] Skipping unmarked non-technical submission {marking_sub.id}", flush=True)
            continue

        display_name = challenge_name
        if is_technical:
            remainder = stripped_name[4:].lstrip(" :-_")
            display_name = remainder or challenge_name
        
        report_data.append({
            'challenge': display_name,
            'submitted_at': sub.date.strftime("%Y-%m-%d %H:%M") if sub.date else 'N/A',
            'flag': sub.provided or '',
            'mark': marking_sub.mark,
            'challengeValue': challenge.value if challenge else 100,  # Max points for the challenge
            'comment': marking_sub.comment or '',
            'is_technical': is_technical,
        })
    
    print(f"[REPORT DEBUG] Returning {len(report_data)} submissions for report", flush=True)
    return sorted(report_data, key=lambda x: x['submitted_at'])


def generate_and_send_student_report(user_id, triggered_by_user_id=None, category=None):
    """
    Generate a PDF report for a student and send via email.
    Optionally filter submissions by category (week).
    
    Args:
        user_id (int): Student user ID
        triggered_by_user_id (int): Admin user ID who triggered this (optional)
        category (str): Optional category to filter by (e.g., 'Week1')
        
    Returns:
        tuple: (success: bool, message: str)
    """
    student = Users.query.get(user_id)
    if not student:
        return False, "Student not found"
    
    if not student.email:
        return False, "Student has no email address"
    
    try:
        # Get submissions (optionally filtered by category)
        submissions = get_student_submissions_for_report(user_id, category=category)
        
        if not submissions:
            return False, f"No marked submissions for this student{f' in {category}' if category else ''}"
        
        # Generate PDF
        ctf_name = get_config('ctf_name', 'CTF')
        category_label = f" - {category}" if category else ""
        pdf_buffer = generate_student_report_pdf(
            student_name=student.name,
            student_email=student.email,
            submissions=submissions,
            ctf_name=ctf_name,
            subtitle=f"Performance Report{category_label}"
        )
        
        # Create email with PDF attachment
        # Note: CTFd's sendmail doesn't support attachments directly,
        # so we'll send a plain text summary with a link to view the full report
        subject = f"{ctf_name} - Your{category_label} Performance Report"
        
        # Get the base URL for the report link
        from flask import request
        base_url = get_config('ctf_url') or 'http://localhost:8000'
        # Remove trailing slash if present
        base_url = base_url.rstrip('/')
        
        # Include category in URL if specified
        if category:
            report_url = f"{base_url}/api/marking_hub/reports/view/my-report?category={category}"
        else:
            report_url = f"{base_url}/api/marking_hub/reports/view/my-report"
        
        email_text = f"""Hello {student.name},

Here's your performance report from {ctf_name}{category_label}.

Submissions Reviewed: {len(submissions)}
Marked: {sum(1 for s in submissions if s['mark'] is not None)}

Summary:
"""
        for s in submissions[:10]:
            mark = s['mark']
            if mark is not None:
                percentage = (mark / s.get('challengeValue', 100)) * 100
                email_text += f"\n- {s['challenge']}: {mark}/{s.get('challengeValue', 100)} ({percentage:.1f}%)"
            else:
                email_text += f"\n- {s['challenge']}: Not yet marked"
        
        email_text += f"""

View your full detailed report here:
{report_url}

(You must be logged in to view your report)

Best regards,
{ctf_name} Team
"""
        
        # Send email (basic text version)
        success, message = sendmail(student.email, email_text, subject)
        
        if success:
            # Record in database
            report = StudentReport(
                user_id=user_id,
                category=category,
                sent_by=triggered_by_user_id,
                email_sent=student.email,
                submission_count=len(submissions),
                marked_count=sum(1 for s in submissions if s.get('mark') is not None),
            )
            db.session.add(report)
            db.session.commit()
            
            logger.info(f"Report sent to {student.email} ({student.name}){category_label}")
            return True, f"Report sent to {student.email}"
        else:
            return False, f"Failed to send email: {message}"
            
    except Exception as e:
        logger.error(f"Error generating report for user {user_id}: {str(e)}")
        return False, f"Error: {str(e)}"
        
        if not submissions:
            return False, "No marked submissions for this student"
        
        # Generate PDF
        ctf_name = get_config('ctf_name', 'CTF')


def get_available_categories():
    """
    Get all unique challenge categories (weeks).
    
    Returns:
        list: of category names sorted alphabetically
    """
    from CTFd.models import Challenges
    
    categories = (
        db.session.query(Challenges.category)
        .filter(Challenges.category.isnot(None))
        .distinct()
        .all()
    )
    
    return sorted([cat[0] for cat in categories if cat[0]])


def generate_weekly_reports(category=None):
    """
    Generate and send reports for all students with marked submissions.
    Optionally filter by category (week).
    Called manually via admin API endpoint.
    
    Args:
        category (str): Optional category to filter by (e.g., 'Week1')
    
    Returns:
        dict: Summary of reports sent
    """
    from CTFd.models import Users, Challenges
    
    # Build query for marked submissions
    query = (
        MarkingSubmission.query
        .filter(MarkingSubmission.mark.isnot(None))
        .join(Submissions, MarkingSubmission.submission_id == Submissions.id)
    )
    
    # Filter by category if specified
    if category:
        query = (
            query
            .join(Challenges, Submissions.challenge_id == Challenges.id)
            .filter(Challenges.category == category)
        )
    
    marked_submissions = query.all()
    
    student_ids = set(sub.submission.user_id for sub in marked_submissions)
    
    results = {
        'category': category,
        'total': len(student_ids),
        'sent': 0,
        'failed': 0,
        'errors': []
    }
    
    for user_id in student_ids:
        success, message = generate_and_send_student_report(user_id, category=category)
        if success:
            results['sent'] += 1
        else:
            results['failed'] += 1
            results['errors'].append(f"User {user_id}: {message}")
    
    category_label = f" for {category}" if category else ""
    logger.info(f"Reports generated{category_label}: {results['sent']} sent, {results['failed']} failed")
    return results
