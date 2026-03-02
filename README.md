# CTFd_Marking_Hub

A comprehensive marking dashboard for non-flagged answers, including submission viewing, marking, comments, tutor assignment, and automated student performance reports.

**📚 Complete API Documentation**: See [API.md](API.md) for detailed endpoint reference with examples.

## Features

### Core Marking
- **Submission Dashboard** - View all submissions organized by user or challenge
- **Detailed Marking** - Grade submissions with dynamic max points and detailed feedback comments
- **Tutor Assignment** - Assign students to specific tutors for distributed marking
- **Progress Tracking** - Visual progress bar showing marking completion
- **Unmarked Filter** - Quickly see what still needs grading
  - Navigation arrows now traverse the full list of visible submissions, so you can move from an unmarked to a marked entry without toggling any filters.
  - When working “by exercise” the next/previous buttons correctly advance through the filtered exercise list, and after saving a mark the interface will skip to the next unmarked submission (if requested) rather than getting stuck.
- **Dynamic Marking Scales** - Support for challenges with custom max point values (not just 0-100)
- **TECH Auto-Assessment** - Technical challenges (TECH prefix) are automatically marked based on flag correctness

### Student Reports
- **Weekly Performance Reports** - Automatically generate and email PDF reports to students
  - Reports for a given week/category now include every exercise in that bucket.  Unattempted challenges appear with a 0% mark (labelled "0% (non-submission_)").
  - When a report is generated for a student the system will also insert zero‑mark entries in the database for every exercise they skipped.  These records are visible in the dashboard stats and help you track completion.
- **PDF Generation** - Beautiful formatted reports with:
  - Challenge name
  - Submitted answer/flag
  - Awarded mark (with percentage based on challenge max points)
  - Tutor feedback
  - Summary statistics
- **Manual Triggering** - Admin can generate reports on-demand via UI
- **Report History** - Track all sent reports with metadata
- **Category Filtering** - Send reports for specific weeks/categories

### Admin Features
- **Sync Submissions** - Sync all CTFd submissions to marking system (auto-marks TECH challenges)
- **Marking Deadlines** - Set per-challenge marking deadlines
- **Report Management** - View report history and send weekly batch reports
- **Tutor Statistics** - Track marking patterns, consistency, and performance per tutor
- **Category Analytics** - View progress and statistics by challenge category
- **Exercise Breakdown** - Detailed statistics per exercise with per-tutor marks

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

## API Quick Reference

**📖 For complete API documentation with examples, see [API.md](API.md)**

### Most Common Endpoints

**Submissions**
```bash
GET /api/marking_hub/submissions              # Get all submissions
PUT /api/marking_hub/submissions/1            # Mark submission (mark + comment)
POST /api/marking_hub/sync                    # Sync and auto-mark TECH challenges
```

**Tutor Management**
```bash
GET /api/marking_hub/tutors                   # List all tutors (admin)
POST /api/marking_hub/tutors                  # Register new tutor (admin)
GET /api/marking_hub/assignments              # List student-tutor assignments (admin)
PUT /api/marking_hub/assignments/42           # Assign student to tutor (admin)
```

**Reports**
```bash
POST /api/marking_hub/reports/send/42         # Send report to specific student (admin)
GET /api/marking_hub/reports/download/42      # Download report as PDF (admin)
POST /api/marking_hub/reports/send-weekly     # Send all reports (admin)
```

**Statistics & Progress**
```bash
GET /api/marking_hub/categories-with-counts   # Get category progress
GET /api/marking_hub/statistics/tutors        # Tutor performance stats (admin)
GET /api/marking_hub/statistics/categories    # By-category stats (admin)
GET /api/marking_hub/statistics/category/Web/exercises  # Per-exercise breakdown (admin)
```

### Example: Complete Marking Workflow

```bash
# 1. Register a tutor
curl -X POST /api/marking_hub/tutors \
  -d '{"user_id": 15}'

# 2. Assign students to tutor
curl -X PUT /api/marking_hub/assignments/42 \
  -d '{"tutor_id": 15}'

# 3. Sync all submissions from CTFd (auto-marks TECH)
curl -X POST /api/marking_hub/sync

# 4. Get unmarked submissions
curl -X GET /api/marking_hub/submissions

# 5. Mark a submission
curl -X PUT /api/marking_hub/submissions/1 \
  -d '{"mark": 85, "comment": "Well done!"}'

# 6. Send report to student
curl -X POST /api/marking_hub/reports/send/42

# 7. Check tutor statistics
curl -X GET /api/marking_hub/statistics/tutors
```

### Key Features in API

- **Dynamic Marking Scales**: Marks validated against `challenge.value` (not hardcoded 100)
- **Percentage Normalization**: Statistics display marks as percentages for fair comparison
- **TECH Auto-Assessment**: POST `/sync` automatically marks technical submissions (full or zero)
- **Per-Tutor Analytics**: See individual tutor patterns, consistency (std dev), and performance
- **Category Filtering**: Reports and stats can be filtered by challenge category (Week1, Web, etc.)
- **Latest Submission Only**: Only the most recent submission per student/challenge is marked

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
