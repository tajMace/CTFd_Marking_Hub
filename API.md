# CTFd Marking Hub - API Documentation

Complete API reference for the CTFd Marking Hub plugin. All API endpoints require proper authentication.

---

## Base URL

```
/api/marking_hub/
```

## Authentication

Most endpoints require one of the following:
- **Admin user**: Full access to all endpoints
- **Tutor user**: Limited access (marked as tutor in the system)
- **Normal user**: Access to personal data only

**Special cases:**
- **Generate Submission Token** (`POST /api/marking_hub/submissions/generate-token`): Requires `X-Automarker-Secret` header (shared secret for automated systems)
- **Submit on Behalf** (`POST /api/marking_hub/submissions/on-behalf-of`): No authentication required (uses secure token instead)

---

## Configuration

### Automarker Secret

To enable the automarker to generate submission tokens, set the `MARKING_HUB_AUTOMARKER_SECRET` environment variable:

```bash
export MARKING_HUB_AUTOMARKER_SECRET="your_random_secret_key_here"
```

Or in CTFd's configuration file:

```python
MARKING_HUB_AUTOMARKER_SECRET = "your_random_secret_key_here"
```

**Security best practices:**
- Use a strong, random secret (at least 32 characters)
- Store it in environment variables or a secure configuration file
- Never commit it to version control
- Rotate periodically
- Only accessible over HTTPS

---

## Table of Contents

1. [Authentication](#authentication)
2. [Configuration](#configuration)
3. [Dashboard Routes](#dashboard-routes)
4. [Submissions](#submissions)
5. [Assignments](#assignments)
6. [Tutors](#tutors)
7. [Deadlines](#deadlines)
8. [Reports](#reports)
9. [Statistics](#statistics)
10. [Categories](#categories)

---

## Dashboard Routes

### Get Marking Hub Dashboard

**Endpoint:** `GET /marking_hub`

**Authentication:** Admin only

**Description:** Renders the interactive marking dashboard frontend.

**Response:** HTML page with React application

**Example:**
```bash
curl -X GET http://localhost:8000/marking_hub \
  -H "Cookie: session=..."
```

---

### Get Login/Access Page

**Endpoint:** `GET /marking_hub/login`

**Authentication:** None (redirects if already logged in)

**Description:** Renders the marking hub login/access page. If user is already authenticated, redirects to dashboard.

**Response:** HTML page with React application

---

## Submissions

### Get All Submissions

**Endpoint:** `GET /api/marking_hub/submissions`

**Authentication:** Authenticated users (admin sees all, tutors see assigned only)

**Parameters:**
- `include_tech` (optional): Include technical challenges. Values: `1`, `true`, `yes` (default: `false`)

**Response:**
```json
[
  {
    "id": 1,
    "submissionId": 101,
    "userId": 42,
    "challengeId": 5,
    "name": "John Doe",
    "zid": "z1234567",
    "submittedAt": "2026-02-13 10:30:45",
    "flag": "flag{example}",
    "challenge": "TECH Web Security",
    "challengeUrl": "/challenges#5",
    "challengeHtml": "<h2>Challenge Description</h2>...",
    "challengeConnectionInfo": "ssh server.ctf.local",
    "category": "Web",
    "challengeValue": 100,
    "isTechnical": true,
    "mark": 100,
    "comment": "Great work!",
    "markedAt": "2026-02-13 11:00:00",
    "markedBy": "Jane Smith",
    "assignedTutorId": 15,
    "assignedTutorName": "Jane Smith"
  }
]
```

**Example:**
```bash
# Get all submissions (admin)
curl -X GET "http://localhost:8000/api/marking_hub/submissions" \
  -H "Cookie: session=..."

# Include technical submissions
curl -X GET "http://localhost:8000/api/marking_hub/submissions?include_tech=1" \
  -H "Cookie: session=..."
```

### Get Single Submission

**Endpoint:** `GET /api/marking_hub/submissions/<submission_id>`

**Authentication:** Authenticated users (must be assigned tutor or admin)

**Parameters:**
- `submission_id` (path): ID of the marking submission

**Response:** Single submission object (same structure as above)

**Errors:**
- `404`: Submission not found
- `403`: Forbidden (not assigned to this submission)

**Example:**
```bash
curl -X GET "http://localhost:8000/api/marking_hub/submissions/1" \
  -H "Cookie: session=..."
```

### Save Submission Mark and Comment

**Endpoint:** `PUT /api/marking_hub/submissions/<submission_id>`

**Authentication:** Authenticated users (admin or assigned tutor)

**Parameters:**
- `submission_id` (path): ID of the marking submission

**Request Body:**
```json
{
  "mark": 85,
  "comment": "Good effort, but needs improvement in error handling."
}
```

**Response:** Updated submission object

**Errors:**
- `400`: Technical submissions cannot be manually marked, or invalid mark value
- `403`: Forbidden (not assigned to this submission)
- `404`: Submission not found

**Notes:**
- Mark must be between 0 and the challenge's max points (stored in `challengeValue`)
- Comment is optional
- Technical submissions (TECH prefix) are auto-assessed and cannot be manually edited
- Automatically sets `markedAt` timestamp and `markedBy` user

**Example:**
```bash
curl -X PUT "http://localhost:8000/api/marking_hub/submissions/1" \
  -H "Cookie: session=..." \
  -H "Content-Type: application/json" \
  -d '{
    "mark": 85,
    "comment": "Good work!"
  }'
```

### Sync Submissions from CTFd

**Endpoint:** `POST /api/marking_hub/sync`

**Authentication:** Admin only

**Description:** Synchronizes all submissions from CTFd's submission table into the marking system. Automatically marks all TECH submissions based on flag correctness.

**Request Body:** None

**Response:**
```json
{
  "message": "Synced 42 new submissions",
  "auto_marked_tech": 8
}
```

**Notes:**
- TECH submissions are automatically marked:
  - **Full points** if the submitted flag is correct
  - **Zero points** if the submitted flag is incorrect
- Only creates entries for submissions that don't already exist in the marking system
- Updates existing TECH submissions if correctness changes
- Mark is determined by: `challenge.value` (full) or `0` (incorrect)

**Example:**
```bash
curl -X POST "http://localhost:8000/api/marking_hub/sync" \
  -H "Cookie: session=..." \
  -H "Content-Type: application/json"
```

### Generate Submission Token

**Endpoint:** `POST /api/marking_hub/submissions/generate-token`

**Authentication:** Shared secret in `X-Automarker-Secret` header (no session required)

**Description:** Generates a secure, single-use token that allows submitting a flag on behalf of a student. The token is tied to a specific student and challenge, and includes an expiration time. Uses HMAC-SHA256 for cryptographic security. This endpoint is designed for automated systems (like autograders/automarkers) to generate submission tokens.

**Request Headers:**
```
X-Automarker-Secret: your_shared_secret_key
Content-Type: application/json
```

**Request Body:**
```json
{
  "user_id": 42,
  "challenge_id": 5,
  "expires_in_hours": 24
}
```

**Parameters:**
- `user_id` (required): ID of the student submitting the flag
- `challenge_id` (required): ID of the challenge
- `expires_in_hours` (optional): Hours until token expires (default: 24)

**Response:**
```json
{
  "token": "rg4mcA...[base64 url-safe token]...",
  "token_id": 123,
  "user_id": 42,
  "user_name": "John Doe",
  "challenge_id": 5,
  "challenge_name": "Web Security 101",
  "hash": "a7b2c1d4e5f6...[SHA256 hex]...",
  "expires_at": "2026-02-18 14:30:00"
}
```

**Errors:**
- `400`: Missing required parameters
- `403`: Invalid or missing automarker secret
- `404`: User or challenge not found
- `500`: Automarker secret not configured on server

**Notes:**
- The `token` and `hash` must both be provided when submitting the flag
- Each token is single-use and tied to one student and one challenge
- After token expiration, new tokens must be generated
- The `X-Automarker-Secret` header is validated securely (timing-attack resistant)
- `created_by` is set to `null` for system-generated tokens
- Must be sent over HTTPS for security

**Security:**
- Tokens use HMAC-SHA256 with the Flask app's SECRET_KEY
- Hash combines user_id, challenge_id, and the random token
- Tokens expire and are marked as used after submission
- Cannot be reused or modified
- Shared secret should be stored in environment variables (`MARKING_HUB_AUTOMARKER_SECRET`)
- Secret comparison uses timing-attack resistant comparison

**Example:**
```bash
curl -X POST "http://localhost:8000/api/marking_hub/submissions/generate-token" \
  -H "X-Automarker-Secret: your_shared_secret_key" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 42,
    "challenge_id": 5,
    "expires_in_hours": 48
  }'
```


### Submit Flag on Behalf of Student

**Endpoint:** `POST /api/marking_hub/submissions/on-behalf-of`

**Authentication:** None required (uses secure token instead)

**Description:** Posts a flag submission on behalf of a student using a previously generated secure token. The flag is automatically evaluated for correctness. This endpoint creates both a standard CTFd submission and a marking submission for manual scoring.

**Request Body:**
```json
{
  "user_id": 42,
  "challenge_id": 5,
  "flag": "flag{correct_answer}",
  "token": "rg4mcA...[base64 url-safe token]...",
  "hash": "a7b2c1d4e5f6...[SHA256 hex]..."
}
```

**Parameters:**
- `user_id` (required): ID of the student
- `challenge_id` (required): ID of the challenge
- `flag` (required): The flag/answer being submitted
- `token` (required): The secure token generated via `generate-token`
- `hash` (required): The HMAC hash that validates the token

**Response (201 Created):**
```json
{
  "success": true,
  "submission_id": 251,
  "user_id": 42,
  "user_name": "John Doe",
  "challenge_id": 5,
  "challenge_name": "Web Security 101",
  "flag": "flag{correct_answer}",
  "correct": true,
  "submitted_at": "2026-02-17 14:30:00"
}
```

**Errors:**
- `400`: Missing required parameters
- `403`: Invalid security hash, token already used, or token expired
- `404`: Token, user, or challenge not found
- `500`: Server error during submission processing

**Notes:**
- **Security is critical:** The hash MUST match the token cryptographically
- Submissions are auto-evaluated using the challenge handler
- For TECH (technical) challenges, automatic marking is applied:
  - Full points if flag is correct
  - Zero points if flag is incorrect
- Non-technical submissions are created but not auto-marked (tutor marks them later)
- Token is marked as used immediately after submission attempt
- Tokens cannot be reused even if submission fails

**Example:**
```bash
# First, generate a token (as admin)
TOKEN_RESPONSE=$(curl -X POST "http://localhost:8000/api/marking_hub/submissions/generate-token" \
  -H "Cookie: session=..." \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 42,
    "challenge_id": 5
  }')

# Extract token and hash
TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.token')
HASH=$(echo $TOKEN_RESPONSE | jq -r '.hash')

# Then submit the flag (no auth required)
curl -X POST "http://localhost:8000/api/marking_hub/submissions/on-behalf-of" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 42,
    "challenge_id": 5,
    "flag": "flag{my_answer}",
    "token": "'$TOKEN'",
    "hash": "'$HASH'"
  }'
```

---

## Assignments

### Get All Tutor Assignments

**Endpoint:** `GET /api/marking_hub/assignments`

**Authentication:** Admin only

**Description:** Lists all user-to-tutor assignments.

**Response:**
```json
[
  {
    "id": 1,
    "userId": 42,
    "userName": "John Doe",
    "userEmail": "john@example.com",
    "tutorId": 15,
    "tutorName": "Jane Smith",
    "tutorEmail": "jane@example.com",
    "assignedAt": "2026-02-10 09:30:00"
  }
]
```

**Example:**
```bash
curl -X GET "http://localhost:8000/api/marking_hub/assignments" \
  -H "Cookie: session=..."
```

### Get Assignment for Specific User

**Endpoint:** `GET /api/marking_hub/assignments/<user_id>`

**Authentication:** Admin only

**Parameters:**
- `user_id` (path): ID of the student to check

**Response:** Single assignment object

**Errors:**
- `404`: No assignment found for this user

**Example:**
```bash
curl -X GET "http://localhost:8000/api/marking_hub/assignments/42" \
  -H "Cookie: session=..."
```

### Get My Assignments (Current Tutor)

**Endpoint:** `GET /api/marking_hub/assignments/mine`

**Authentication:** Tutor or admin

**Description:** Returns all students assigned to the current logged-in tutor.

**Response:** Array of assignment objects

**Example:**
```bash
curl -X GET "http://localhost:8000/api/marking_hub/assignments/mine" \
  -H "Cookie: session=..."
```

### Assign Student to Tutor

**Endpoint:** `PUT /api/marking_hub/assignments/<user_id>`

**Authentication:** Admin only

**Parameters:**
- `user_id` (path): ID of the student to assign

**Request Body:**
```json
{
  "tutor_id": 15
}
```

**Response:** Updated assignment object

**Errors:**
- `400`: Tutor must be registered as a marking tutor or admin
- `404`: User or tutor not found

**Notes:**
- Tutor must be registered in the marking tutors table
- Sets `assignedAt` timestamp to current time
- Use `null` for `tutor_id` to unassign

**Example:**
```bash
curl -X PUT "http://localhost:8000/api/marking_hub/assignments/42" \
  -H "Cookie: session=..." \
  -H "Content-Type: application/json" \
  -d '{
    "tutor_id": 15
  }'
```

### Remove Student Assignment

**Endpoint:** `DELETE /api/marking_hub/assignments/<user_id>`

**Authentication:** Admin only

**Parameters:**
- `user_id` (path): ID of the student to unassign

**Response:**
```json
{
  "message": "Assignment removed"
}
```

**Notes:**
- Equivalent to setting `tutor_id` to `null`

**Example:**
```bash
curl -X DELETE "http://localhost:8000/api/marking_hub/assignments/42" \
  -H "Cookie: session=..."
```

---

## Tutors

### Get All Marking Tutors

**Endpoint:** `GET /api/marking_hub/tutors`

**Authentication:** Admin only

**Description:** Lists all users registered as marking tutors.

**Response:**
```json
[
  {
    "id": 1,
    "userId": 15,
    "userName": "Jane Smith",
    "userEmail": "jane@example.com",
    "createdAt": "2026-02-01 13:15:00"
  }
]
```

**Example:**
```bash
curl -X GET "http://localhost:8000/api/marking_hub/tutors" \
  -H "Cookie: session=..."
```

### Register New Marking Tutor

**Endpoint:** `POST /api/marking_hub/tutors`

**Authentication:** Admin only

**Parameters:** None

**Request Body:**
```json
{
  "user_id": 15
}
```

**Response:** New tutor object

**Errors:**
- `400`: `user_id` is required
- `404`: User not found

**Notes:**
- User must exist in the CTFd users table
- Only registers user once (duplicate registrations return existing record)

**Example:**
```bash
curl -X POST "http://localhost:8000/api/marking_hub/tutors" \
  -H "Cookie: session=..." \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 15
  }'
```

### Remove Marking Tutor

**Endpoint:** `DELETE /api/marking_hub/tutors/<user_id>`

**Authentication:** Admin only

**Parameters:**
- `user_id` (path): ID of the tutor to remove

**Response:**
```json
{
  "message": "Tutor removed"
}
```

**Example:**
```bash
curl -X DELETE "http://localhost:8000/api/marking_hub/tutors/15" \
  -H "Cookie: session=..."
```

### Check Current User Tutor Status

**Endpoint:** `GET /api/marking_hub/tutors/me`

**Authentication:** Authenticated users

**Description:** Returns whether the current user is a tutor or admin.

**Response:**
```json
{
  "isTutor": true,
  "isAdmin": false
}
```

**Example:**
```bash
curl -X GET "http://localhost:8000/api/marking_hub/tutors/me" \
  -H "Cookie: session=..."
```

---

## Deadlines

### Get All Marking Deadlines

**Endpoint:** `GET /api/marking_hub/deadlines`

**Authentication:** Authenticated users

**Description:** Lists all marking deadlines for challenges.

**Response:**
```json
[
  {
    "id": 1,
    "challengeId": 5,
    "challengeName": "Web Security Challenge",
    "dueDate": "2026-02-20 23:59:59",
    "createdAt": "2026-02-01 10:00:00"
  }
]
```

**Example:**
```bash
curl -X GET "http://localhost:8000/api/marking_hub/deadlines" \
  -H "Cookie: session=..."
```

### Get Deadline for Specific Challenge

**Endpoint:** `GET /api/marking_hub/deadlines/<challenge_id>`

**Authentication:** Authenticated users

**Parameters:**
- `challenge_id` (path): ID of the challenge

**Response:** Single deadline object

**Errors:**
- `404`: No deadline found for this challenge

**Example:**
```bash
curl -X GET "http://localhost:8000/api/marking_hub/deadlines/5" \
  -H "Cookie: session=..."
```

### Set or Update Marking Deadline

**Endpoint:** `PUT /api/marking_hub/deadlines/<challenge_id>`

**Authentication:** Admin only

**Parameters:**
- `challenge_id` (path): ID of the challenge

**Request Body:**
```json
{
  "due_date": "2026-02-20T23:59"
}
```

**Response:** Updated deadline object

**Errors:**
- `400`: Invalid date format
- `404`: Challenge not found

**Date Format:** ISO 8601 format `YYYY-MM-DDTHH:MM` (e.g., `2026-02-20T23:59`)

**Example:**
```bash
curl -X PUT "http://localhost:8000/api/marking_hub/deadlines/5" \
  -H "Cookie: session=..." \
  -H "Content-Type: application/json" \
  -d '{
    "due_date": "2026-02-20T23:59"
  }'
```

### Delete Marking Deadline

**Endpoint:** `DELETE /api/marking_hub/deadlines/<challenge_id>`

**Authentication:** Admin only

**Parameters:**
- `challenge_id` (path): ID of the challenge

**Response:**
```json
{
  "message": "Deadline removed"
}
```

**Example:**
```bash
curl -X DELETE "http://localhost:8000/api/marking_hub/deadlines/5" \
  -H "Cookie: session=..."
```

---

## Reports

### Send Report to Specific Student

**Endpoint:** `POST /api/marking_hub/reports/send/<user_id>`

**Authentication:** Admin only

**Parameters:**
- `user_id` (path): ID of the student
- `category` (query, optional): Filter by category (week). Example: `?category=Week1`

**Request Body:** None

**Response:**
```json
{
  "success": true,
  "message": "Report sent to john@example.com"
}
```

**Errors:**
- `400`: Student not found or has no email address
- `404`: No marked submissions for this student

**Notes:**
- Sends email with performance summary
- Generates PDF with detailed feedback
- When filtering by category, the report now lists **every exercise** in that week/category.  Missing submissions are shown with a 0% mark labelled "0% (non-submission_)".
- Sending a report for a student also creates placeholder submissions/marks in the database for any exercises they never attempted (marked 0).  This makes non‑submissions appear in exercise statistics and persists the zero grade.
- Reports are tracked in the StudentReport table
- Can filter by category to send category-specific reports

**Example:**
```bash
# Send overall report
curl -X POST "http://localhost:8000/api/marking_hub/reports/send/42" \
  -H "Cookie: session=..."

# Send Week1-only report
curl -X POST "http://localhost:8000/api/marking_hub/reports/send/42?category=Week1" \
  -H "Cookie: session=..."
```

### Download Student Report as PDF

**Endpoint:** `GET /api/marking_hub/reports/download/<user_id>`

**Authentication:** Admin only

**Parameters:**
- `user_id` (path): ID of the student

**Response:** PDF file (binary)

**Content-Type:** `application/pdf`

**Errors:**
- `404`: Student not found or no marked submissions
- `500`: Error generating PDF

**Notes:**
- Returns PDF with student performance summary
- Includes all marked submissions and tutor feedback
- Category-specific reports also include unattempted exercises as zero‑marked entries so students see every assignment.
- Technical and non-technical submissions shown separately
- File is automatically generated, not pre-stored

**Example:**
```bash
curl -X GET "http://localhost:8000/api/marking_hub/reports/download/42" \
  -H "Cookie: session=..." \
  -o student_report.pdf
```

### Get All Student Reports

**Endpoint:** `GET /api/marking_hub/reports`

**Authentication:** Admin only

**Description:** Lists all reports that have been generated and sent.

**Response:**
```json
[
  {
    "id": 1,
    "userId": 42,
    "userName": "John Doe",
    "userEmail": "john@example.com",
    "sentAt": "2026-02-13 12:30:00",
    "emailSent": "john@example.com",
    "submissionCount": 12,
    "markedCount": 10,
    "sentBy": "Admin User"
  }
]
```

**Example:**
```bash
curl -X GET "http://localhost:8000/api/marking_hub/reports" \
  -H "Cookie: session=..."
```

### Get Reports for Specific Student

**Endpoint:** `GET /api/marking_hub/reports/student/<user_id>`

**Authentication:** Admin only

**Parameters:**
- `user_id` (path): ID of the student

**Response:** Array of report objects

**Example:**
```bash
curl -X GET "http://localhost:8000/api/marking_hub/reports/student/42" \
  -H "Cookie: session=..."
```

### Send Reports to All Students

**Endpoint:** `POST /api/marking_hub/reports/send-weekly`

**Authentication:** Admin only

**Request Body:** None

**Response:**
```json
{
  "success": true,
  "message": "Reports sent to 28 students, 2 failed",
  "details": {
    "category": null,
    "total": 30,
    "sent": 28,
    "failed": 2,
    "errors": [
      "User 10: Student has no email address",
      "User 15: No marked submissions for this student"
    ]
  }
}
```

**Notes:**
- Sends reports to all students with marked submissions (and, when a category is provided, any student who has submitted work at all).
- Before generating each student's report the system inserts zero‑mark entries for any challenges they missed, so unfinished exercises appear in the database and stats.
- Creates records for successful deliveries
- Errors are logged but don't stop other deliveries

**Example:**
```bash
curl -X POST "http://localhost:8000/api/marking_hub/reports/send-weekly" \
  -H "Cookie: session=..."
```

### Send Reports by Category

**Endpoint:** `POST /api/marking_hub/reports/send-by-category/<category>`

**Authentication:** Admin only

**Parameters:**
- `category` (path): Challenge category (e.g., `Week1`, `Web`, `Crypto`)

**Request Body:** None

**Response:** Same as send-weekly endpoint

**Notes:**
- Only includes submissions from challenges in the specified category
- Useful for sending weekly reports for specific weeks

**Example:**
```bash
curl -X POST "http://localhost:8000/api/marking_hub/reports/send-by-category/Week1" \
  -H "Cookie: session=..."
```

---

## Statistics

### Get Tutor Marking Statistics

**Endpoint:** `GET /api/marking_hub/statistics/tutors`

**Authentication:** Admin only

**Description:** Returns marking patterns and performance metrics for each tutor.

**Response:**
```json
{
  "success": true,
  "tutors": [
    {
      "tutor_id": 15,
      "name": "Jane Smith",
      "email": "jane@example.com",
      "submissions_marked": 42,
      "avg_mark": 78.5,
      "std_dev": 12.3,
      "last_marked": "2026-02-13 11:30:00"
    }
  ],
  "global": {
    "total_submitted": 120,
    "total_marked": 95,
    "marking_percentage": 79.2,
    "avg_mark_overall": 76.8
  }
}
```

**Metrics Explanation:**
- `submissions_marked`: Total submissions marked by this tutor
- `avg_mark`: Average mark as percentage (0-100%)
- `std_dev`: Standard deviation of marks (consistency metric)
- `marking_percentage`: Global percentage of submissions marked
- `avg_mark_overall`: Global average mark across all tutors

**Notes:**
- Marks are normalized to percentages for fair comparison across different challenge max values
- Standard deviation is calculated on percentage basis
- Unique (student, challenge) pairs are counted, not individual submissions

**Example:**
```bash
curl -X GET "http://localhost:8000/api/marking_hub/statistics/tutors" \
  -H "Cookie: session=..."
```

### Get Category Statistics

**Endpoint:** `GET /api/marking_hub/statistics/categories`

**Authentication:** Admin only

**Description:** Returns marking progress and statistics grouped by challenge category.

**Response:**
```json
{
  "success": true,
  "categories": [
    {
      "category": "Web",
      "total_submitted": 24,
      "total_marked": 20,
      "marking_percentage": 83.3,
      "avg_mark": 75.2
    },
    {
      "category": "Crypto",
      "total_submitted": 18,
      "total_marked": 15,
      "marking_percentage": 83.3,
      "avg_mark": 72.1
    }
  ]
}
```

**Metrics Explanation:**
- `total_submitted`: Unique student/challenge pairs submitted
- `total_marked`: Unique pairs that have been marked
- `marking_percentage`: Progress percentage
- `avg_mark`: Average mark as percentage

**Example:**
```bash
curl -X GET "http://localhost:8000/api/marking_hub/statistics/categories" \
  -H "Cookie: session=..."
```

### Get Exercise Statistics for Category

**Endpoint:** `GET /api/marking_hub/statistics/category/<category>/exercises`

**Authentication:** Admin only

**Parameters:**
- `category` (path): Challenge category (e.g., `Web`, `Week1`)

**Description:** Returns detailed statistics for each exercise/challenge within a category, including per-tutor breakdown.

**Response:**
```json
{
  "success": true,
  "category": "Web",
  "exercises": [
    {
      "challenge_id": 5,
      "challenge_name": "SQL Injection Basics",
      "total_submitted": 8,
      "total_marked": 7,
      "marking_percentage": 87.5,
      "avg_mark": 82.1,
      "per_tutor": [
        {
          "tutor_id": 15,
          "tutor_name": "Jane Smith",
          "marked_count": 5,
          "avg_mark": 84.0
        },
        {
          "tutor_id": 16,
          "tutor_name": "John Tutor",
          "marked_count": 2,
          "avg_mark": 78.5
        }
      ]
    }
  ]
}
```

**Metrics Explanation:**
- Per-tutor marks show individual tutor's marking patterns
- `marked_count`: Number of submissions marked by this tutor for this exercise
- `avg_mark`: Average mark given by this tutor (as percentage)
- Tutors with 0 marks for an exercise are not included

**Example:**
```bash
curl -X GET "http://localhost:8000/api/marking_hub/statistics/category/Web/exercises" \
  -H "Cookie: session=..."
```

---

## Categories

### Get All Challenge Categories

**Endpoint:** `GET /api/marking_hub/categories`

**Authentication:** Admin only

**Description:** Lists all unique challenge categories from the system.

**Response:**
```json
{
  "success": true,
  "categories": ["Web", "Crypto", "Forensics", "Week1", "Week2"]
}
```

**Example:**
```bash
curl -X GET "http://localhost:8000/api/marking_hub/categories" \
  -H "Cookie: session=..."
```

### Get Categories with Submission Counts

**Endpoint:** `GET /api/marking_hub/categories-with-counts`

**Authentication:** Authenticated users (admin sees all, tutors see assigned students only)

**Parameters:**
- `include_tech` (optional): Include technical challenges. Values: `1`, `true`, `yes` (default: `false`)

**Description:** Lists all categories with counts of total and unmarked submissions.

**Response:**
```json
{
  "success": true,
  "categories": [
    {
      "category": "Web",
      "unmarkedCount": 5,
      "totalCount": 12
    },
    {
      "category": "Crypto",
      "unmarkedCount": 2,
      "totalCount": 8
    }
  ]
}
```

**Notes:**
- Tutor users only see submissions from their assigned students
- Admin users see all submissions
- Useful for displaying marking progress in UI

**Example:**
```bash
# Get all categories
curl -X GET "http://localhost:8000/api/marking_hub/categories-with-counts" \
  -H "Cookie: session=..."

# Include technical submissions
curl -X GET "http://localhost:8000/api/marking_hub/categories-with-counts?include_tech=1" \
  -H "Cookie: session=..."
```

---

## Common Response Patterns

### Success Response
```json
{
  "success": true,
  "message": "Operation completed successfully"
}
```

### Error Response
```json
{
  "success": false,
  "message": "Error description"
}
```

### HTTP Status Codes
- `200 OK`: Successful GET or successful mutation
- `201 Created`: Resource created (not typically used, returns 200)
- `400 Bad Request`: Invalid parameters or validation error
- `403 Forbidden`: User lacks permission for operation
- `404 Not Found`: Resource does not exist
- `500 Internal Server Error`: Server-side error

---

## Authentication Notes

### Admin Access
- Required for: All `/tutors`, `/assignments`, `/deadlines`, `/statistics`, `/reports` endpoints (except GET reports for personal use)
- Identified by CTFd's `admin` user flag

### Tutor Access
- Required for: Marking submissions, viewing assigned students' submissions
- Identified by registration in `marking_tutors` table
- Can only view/mark submissions assigned to them

### All Authenticated Users
- Can access: Their own data, categories, general information
- Required check: User must be logged in to CTFd

---

## Marking Scale

### Dynamic Challenge Values
- Each challenge has a configurable max point value (`challenge.value`)
- Marks are stored as absolute values (0 to challenge.value)
- Statistics convert marks to percentages for fair comparison: `(mark / challenge_value) * 100`

### Default Values
- If challenge has no `value` set, defaults to 100 points
- TECH submissions always score: full points (correct) or 0 (incorrect)

### Mark Validation
- Mark must be a number
- Mark must be >= 0
- Mark must be <= challenge.value
- Request fails with 400 if validation fails

---

## Technical Submissions (TECH Prefix)

### Characteristics
- Identified by `TECH` prefix in challenge name (case-insensitive)
- Cannot be manually marked by tutors
- Automatically marked during sync based on flag correctness
- Only show submission name, time, and auto-assessed mark in reports

### Auto-Marking Behavior
- Triggered by `POST /api/marking_hub/sync`
- Mark = `challenge.value` if submitted flag is correct
- Mark = `0` if submitted flag is incorrect
- Marked by system admin user
- Updates if student resubmits with different flag result

---

## Examples Workflow

### Complete Marking Workflow

1. **Register Tutors**
   ```bash
   # Register tutor
   POST /api/marking_hub/tutors
   { "user_id": 15 }
   ```

2. **Assign Students**
   ```bash
   # Assign student to tutor
   PUT /api/marking_hub/assignments/42
   { "tutor_id": 15 }
   ```

3. **Sync Submissions**
   ```bash
   # Bring in all submissions from CTFd (including auto-mark TECH)
   POST /api/marking_hub/sync
   ```

4. **View Submissions**
   ```bash
   # Get unmarked submissions
   GET /api/marking_hub/submissions
   ```

5. **Mark Submissions**
   ```bash
   # Mark a submission
   PUT /api/marking_hub/submissions/1
   { "mark": 85, "comment": "Good work!" }
   ```

6. **Check Progress**
   ```bash
   # See statistics by tutor
   GET /api/marking_hub/statistics/tutors
   
   # See progress by category
   GET /api/marking_hub/statistics/categories
   ```

7. **Send Reports**
   ```bash
   # Send individual report
   POST /api/marking_hub/reports/send/42
   
   # Send all reports
   POST /api/marking_hub/reports/send-weekly
   ```

### Admin Dashboard Workflow

1. Get all categories with progress
   ```bash
   GET /api/marking_hub/categories-with-counts
   ```

2. Click category to see exercises
   ```bash
   GET /api/marking_hub/statistics/category/Web/exercises
   ```

3. View per-tutor breakdown for each exercise
   - See which tutor marked what
   - See marking consistency (avg mark per tutor)

4. View tutor patterns
   ```bash
   GET /api/marking_hub/statistics/tutors
   ```

---

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `403 Forbidden` | User is not admin/tutor or not assigned to this student | Check user permissions and assignments |
| `404 Not Found` | Resource doesn't exist | Verify ID and ensure resource was created |
| `400 Bad Request` | Invalid parameters (mark out of range, bad date format) | Check parameter types and ranges |
| `500 Internal Server Error` | Server error, check logs | Contact admin, check server logs |

---

## Rate Limiting

No rate limiting is currently implemented. For production deployment, consider adding rate limiting to prevent abuse of reporting and statistics endpoints.

---

## Pagination

No pagination is currently implemented. All list endpoints return complete results. For large deployments with thousands of submissions, consider adding pagination support.

---

## Version

- **API Version:** 1.0
- **Plugin Version:** See plugin manifest
- **Last Updated:** February 13, 2026

