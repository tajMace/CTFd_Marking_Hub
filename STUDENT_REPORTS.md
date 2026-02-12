# Student Performance Reports - Usage Guide

The CTFd_Marking_Hub now includes comprehensive student performance reports that can be generated and sent to students via email.

## Features

- **Weekly Reports** - Automatically email performance summaries to students
- **PDF Attachments** - Beautiful PDF reports with all marking feedback
- **Manual Triggering** - Generate reports on-demand for specific students or all students
- **Report History** - Track which students received reports and when
- **Download Reports** - Admins can download student reports as PDFs

## API Endpoints

### Send Reports

#### Trigger Weekly Reports (All Students)
```bash
POST /api/marking_hub/reports/send-weekly
```
Generates and emails reports to all students who have marked submissions.

**Response:**
```json
{
  "success": true,
  "message": "Reports sent to 45 students, 2 failed",
  "details": {
    "total": 47,
    "sent": 45,
    "failed": 2,
    "errors": ["User 123: No email address", "User 456: Email service down"]
  }
}
```

#### Send Single Student Report
```bash
POST /api/marking_hub/reports/send/<user_id>
```
Sends a report to a specific student (who must have at least one marked submission).

**Example:**
```bash
curl -X POST http://localhost:8000/api/marking_hub/reports/send/42 \
  -H "X-CSRF-Token: <token>"
```

**Response:**
```json
{
  "success": true,
  "message": "Report sent to student@example.com"
}
```

### Download/View Reports

#### Download Student Report as PDF
```bash
GET /api/marking_hub/reports/download/<user_id>
```
Returns the PDF report for download (admin only).

#### Get Report History
```bash
GET /api/marking_hub/reports
```
Returns all sent reports with metadata.

**Response:**
```json
[
  {
    "id": 1,
    "userId": 42,
    "userName": "John Smith",
    "userEmail": "john@example.com",
    "sentAt": "2026-02-12 15:30:45",
    "emailSent": "john@example.com",
    "submissionCount": 5,
    "markedCount": 5,
    "sentBy": "Prof Admin"
  }
]
```

#### Get Reports for Specific Student
```bash
GET /api/marking_hub/reports/student/<user_id>
```

## Manual Report Triggering

Reports are sent manually by admins using the API endpoints. You can trigger reports on-demand or set up a cron job for automated scheduling.

### Using the Admin Dashboard
1. Click "Send Reports" tab in the marking hub
2. Click "Send Weekly Reports" to email all students with marked work
3. Or select individual students to send targeted reports

### Using Cron Job
Set up a cron job to trigger reports on a regular schedule:

```bash
# Run every Monday at 9:00 AM
0 9 * * 1 curl -X POST https://your-ctf.example.com/api/marking_hub/reports/send-weekly \
  -H "Authorization: Bearer YOUR_ADMIN_API_TOKEN" \
  -H "X-CSRF-Token: YOUR_CSRF_TOKEN"
```

## Report Contents

Each student report includes:

### Header
- Student name and email
- Generation date/time
- CTF name

### Summary Statistics
- Total submissions reviewed
- Number marked vs unmarked
- Average mark (if any marked)

### Detailed Feedback (Per Submission)
For each submission:
- **Challenge Name** - Name of the exercise
- **Submitted At** - Date/time of submission
- **Your Answer** - The flag/answer they submitted (truncated if long)
- **Mark** - Awarded grade with color coding
  - Green (70%+): Good performance
  - Red (< 70%): Needs improvement
  - Gray: Not yet marked
- **Feedback** - Tutor's comment/feedback

## Requirements

### Python Dependencies
```
reportlab - PDF generation
```

Already included in `requirements.txt`

### Email Configuration
Reports are sent via your configured CTFd email provider. Ensure CTFd has email configured in `config.ini`:

```ini
[CTFd]
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=noreply@example.com
MAIL_PASSWORD=your_password
MAIL_USE_TLS=true
MAIL_DEFAULT_SENDER=noreply@example.com
```

## Database

Reports create a `StudentReport` record on successful send, tracking:
- Which student
- When sent
- Email address it was sent to
- How many submissions were in the report
- How many submissionswere marked
- Which admin triggered it

This allows for audit trails and resending reports if needed.

## Common Scenarios

### Send reports to all students after marking deadline
```bash
curl -X POST http://localhost:8000/api/marking_hub/reports/send-weekly \
  -H "X-CSRF-Token: YOUR_TOKEN"
```

### Check if student received report
```bash
curl http://localhost:8000/api/marking_hub/reports/student/42 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Download a student's report to review before sending
```bash
curl -o student_report.pdf \
  http://localhost:8000/api/marking_hub/reports/download/42 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Troubleshooting

### Reports not sending?
1. Check CTFd email configuration is valid
2. Verify student has an email address in the system
3. Check that at least one submission is marked for the student
4. Review server logs for email service errors

### PDF looks wrong?
- reportlab has some limitations with complex HTML/CSS
- Text is plain; HTML in comments is displayed as-is (not rendered)
- If needed, edit `utils/pdf_generator.py` to customize styling

### Want to customize report formats?
Edit `/plugins/CTFd_Marking_Hub/utils/pdf_generator.py`:
- `generate_student_report_pdf()` - Main PDF generation
- Modify styles, colors, layout as needed
- Add new sections or data fields

## Future Enhancements

Potential improvements:
- Email templates for report text
- Batch PDF export for all students
- Report scheduling UI in admin panel  
- Detailed per-rubric feedback integration
- Student report view/download in their account
