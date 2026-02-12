# CTFd_Marking_Hub

A comprehensive marking dashboard for non-flagged answers, including submission viewing, marking, comments, tutor assignment, and automated student performance reports.

## Features

### Core Marking
- **Submission Dashboard** - View all submissions organized by user or challenge
- **Detailed Marking** - Grade submissions (0-100) with detailed feedback comments
- **Tutor Assignment** - Assign students to specific tutors for distributed marking
- **Progress Tracking** - Visual progress bar showing marking completion
- **Unmarked Filter** - Quickly see what still needs grading

### Student Reports
- **Weekly Performance Reports** - Automatically generate and email PDF reports to students
- **PDF Generation** - Beautiful formatted reports with:
  - Challenge name
  - Submitted answer/flag
  - Awarded mark
  - Tutor feedback
  - Summary statistics
- **Manual Triggering** - Admin can generate reports on-demand via UI
- **Report History** - Track all sent reports with metadata

### Admin Features
- **Sync Submissions** - Sync all CTFd submissions to marking system
- **Marking Deadlines** - Set per-challenge marking deadlines
- **Report Management** - View report history and send weekly batch reports

## Installation

1. Install required dependencies:
```bash
pip install reportlab
```

2. Enable the plugin in CTFd

3. The plugin will automatically create necessary database tables on first run

## Usage

### Accessing the Dashboard
- Navigate to `/marking_hub` (admin only by default)
- Tutors can login at `/marking_hub/login` if they're registered as tutors

### Sending Student Reports

#### Manual Report Send (Admin)
1. Click "Student Reports" button in dashboard
2. Go to "Send Reports" tab
3. Click "Send Weekly Reports" to email all marked submissions to students

#### Manual Report Triggering
Reports are sent manually by admins. Trigger them:
- **Via Dashboard**: Click "Send Weekly Reports" button
- **Via API**: Use `/api/marking_hub/reports/send-weekly` endpoint
- **Via Cron Job**: Schedule the API endpoint to run periodically

### API Endpoints

#### Submissions
- `GET /api/marking_hub/submissions` - Get all submissions
- `GET /api/marking_hub/submissions/<id>` - Get specific submission
- `PUT /api/marking_hub/submissions/<id>` - Update mark and comment
- `POST /api/marking_hub/sync` - Sync CTFd submissions

#### Reports
- `POST /api/marking_hub/reports/send/<user_id>` - Send report to specific student
- `GET /api/marking_hub/reports/download/<user_id>` - Download report as PDF
- `GET /api/marking_hub/reports` - Get all report history
- `GET /api/marking_hub/reports/student/<user_id>` - Get reports for user
- `POST /api/marking_hub/reports/send-weekly` - Trigger weekly reports for all students

#### Assignments
- `GET /api/marking_hub/assignments` - Get all assignments
- `PUT /api/marking_hub/assignments/<user_id>` - Assign tutor to student
- `DELETE /api/marking_hub/assignments/<user_id>` - Remove assignment

#### Tutors
- `GET /api/marking_hub/tutors` - List all tutors
- `POST /api/marking_hub/tutors` - Add tutor
- `DELETE /api/marking_hub/tutors/<user_id>` - Remove tutor

#### Deadlines
- `GET /api/marking_hub/deadlines` - Get all deadlines
- `PUT /api/marking_hub/deadlines/<challenge_id>` - Set deadline
- `DELETE /api/marking_hub/deadlines/<challenge_id>` - Remove deadline

## Database Models

### MarkingSubmission
Extends CTFd submissions with marking data:
- `mark` (0-100, nullable)
- `comment` (feedback text)
- `marked_at` (timestamp)
- `marked_by` (tutor user_id)

### StudentReport
Tracks sent performance reports:
- `user_id` - Student who received report
- `sent_at` - When report was sent
- `sent_by` - Admin who triggered it
- `email_sent` - Email address it was sent to
- `submission_count` - Number of submissions in report
- `marked_count` - Number that were marked

### MarkingAssignment
Links students to tutors for distributed marking

### MarkingTutor
Identifies which users are marked as tutors

### MarkingDeadline
Stores per-challenge marking due dates

## Configuration

Reports are sent via the configured CTFd email provider (SMTP or Mailgun). Ensure your CTFd instance has email configured in `config.ini`:

```ini
[CTFd]
MAIL_SERVER=your-mail-server
MAIL_PORT=587
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-password
```

## Architecture Notes

The plugin uses simple PDF generation with [reportlab](https://www.reportlab.com/) to avoid external binary dependencies.

Weekly report scheduling can work in two modes:
**Reports are sent manually by admins** via:
- The dashboard "Send Reports" button
- API endpoints (`/api/marking_hub/reports/send-weekly` or `/api/marking_hub/reports/send/<user_id>`)
- Cron jobs that call the API endpoint regularly

All report data is stored for audit trails and history tracking.
