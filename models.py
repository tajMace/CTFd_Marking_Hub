from CTFd.models import db
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, UniqueConstraint, Boolean, Table
from sqlalchemy.orm import relationship, backref
from datetime import datetime



# Association table for many-to-many tutor-student assignments
marking_assignments = Table(
    "marking_assignments",
    db.Model.metadata,
    Column("student_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("tutor_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("assigned_at", DateTime, nullable=True, default=datetime.utcnow)
)

# Extend Users model with relationships for tutors and students
from CTFd.models import Users
Users.tutors = relationship(
    "Users",
    secondary=marking_assignments,
    primaryjoin=Users.id == marking_assignments.c.student_id,
    secondaryjoin=Users.id == marking_assignments.c.tutor_id,
    backref=backref("students", lazy="dynamic"),
    lazy="dynamic"
)

# Helper class for API compatibility (not a real table)
class MarkingAssignmentHelper:
    def __init__(self, student, tutor, assigned_at=None):
        self.student = student
        self.tutor = tutor
        self.assigned_at = assigned_at

    def to_dict(self):
        return {
            "studentId": self.student.id,
            "studentName": self.student.name,
            "studentEmail": self.student.email,
            "tutorId": self.tutor.id,
            "tutorName": self.tutor.name,
            "tutorEmail": self.tutor.email,
            "assignedAt": self.assigned_at.strftime("%Y-%m-%d %H:%M:%S") if self.assigned_at else None,
        }


class MarkingTutor(db.Model):
    """
    Explicitly marks a user as a tutor (separate from admins).
    """
    __tablename__ = "marking_tutors"
    __table_args__ = (UniqueConstraint("user_id", name="uq_marking_tutors_user_id"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, nullable=True, default=datetime.utcnow)

    user = relationship("Users", foreign_keys=[user_id], lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "userId": self.user_id,
            "userName": self.user.name if self.user else None,
            "userEmail": self.user.email if self.user else None,
            "createdAt": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }

class MarkingDeadline(db.Model):
    """
    Stores marking due dates for challenges.
    """
    __tablename__ = "marking_deadlines"
    __table_args__ = (UniqueConstraint("challenge_id", name="uq_marking_deadlines_challenge_id"),)

    id = Column(Integer, primary_key=True)
    challenge_id = Column(Integer, ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False)
    due_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=True, default=datetime.utcnow)

    challenge = relationship("Challenges", foreign_keys=[challenge_id], lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "challengeId": self.challenge_id,
            "challengeName": self.challenge.name if self.challenge else None,
            "dueDate": self.due_date.strftime("%Y-%m-%d %H:%M:%S") if self.due_date else None,
            "createdAt": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }


class MarkingSubmission(db.Model):
    """
    Extends CTFd's Submissions with marking data.
    Links to the original submission for all challenge/user data.
    """
    __tablename__ = "marking_submissions"

    id = Column(Integer, primary_key=True)
    submission_id = Column(Integer, ForeignKey("submissions.id", ondelete="CASCADE"), unique=True, nullable=False)
    mark = Column(Integer, nullable=True)  # null = unmarked, 0-100 when marked
    comment = Column(Text, nullable=True)  # Feedback for student
    marked_at = Column(DateTime, nullable=True)  # When marking was completed
    marked_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Which tutor marked it

    # Relationships
    submission = relationship("Submissions", foreign_keys=[submission_id], lazy="joined")
    marker = relationship("Users", foreign_keys=[marked_by], lazy="select")

    def __repr__(self):
        return f"<MarkingSubmission {self.id} - Submission {self.submission_id}>"

    @property
    def is_marked(self):
        return self.mark is not None
    
    def to_dict(self):
        """
        Convert to dictionary for API responses.
        Includes all relevant data from the base submission.
        """
        sub = self.submission
        user = sub.user
        challenge = sub.challenge
        # Get all tutors for this student (user)
        tutors = []
        if user:
            for tutor in user.tutors:
                tutors.append({
                    "tutorId": tutor.id,
                    "tutorName": tutor.name,
                    "tutorEmail": tutor.email
                })
        challenge_name = challenge.name if challenge else ""
        is_technical = challenge_name.lstrip().upper().startswith("TECH")

        return {
            "id": self.id,
            "submissionId": sub.id,
            "userId": sub.user_id,
            "challengeId": sub.challenge_id,
            "name": user.name if user and user.name else "Unknown",
            "submittedAt": sub.date.strftime("%Y-%m-%d %H:%M:%S") if sub.date else None,
            "flag": sub.provided,  # The submitted flag/answer
            "challenge": challenge.name if challenge else "Unknown",
            "challengeUrl": f"/challenges#{challenge.id}" if challenge else None,
            "challengeHtml": challenge.html if challenge else None,
            "challengeConnectionInfo": challenge.connection_info if challenge else None,
            "category": challenge.category if challenge else "Uncategorized",
            "challengeValue": challenge.value if challenge else 100,  # Max points for this challenge
            "isTechnical": is_technical,
            "mark": self.mark,
            "comment": self.comment,
            "markedAt": self.marked_at.strftime("%Y-%m-%d %H:%M:%S") if self.marked_at else None,
            "markedBy": self.marker.name if self.marker else None,
            "assignedTutors": tutors,
        }


class StudentReport(db.Model):
    """
    Tracks when student performance reports were generated and sent.
    """
    __tablename__ = "student_reports"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category = Column(String(100), nullable=True)  # Week/category (e.g., 'Week1', 'Week2', or None for full report)
    sent_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    sent_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # Which admin triggered it
    email_sent = Column(String(255), nullable=True)  # The email address it was sent to
    submission_count = Column(Integer, nullable=False, default=0)  # How many submissions were in the report
    marked_count = Column(Integer, nullable=False, default=0)  # How many were marked

    user = relationship("Users", foreign_keys=[user_id], lazy="joined")
    trigger_user = relationship("Users", foreign_keys=[sent_by], lazy="select")

    def to_dict(self):
        return {
            "id": self.id,
            "userId": self.user_id,
            "userName": self.user.name if self.user else None,
            "userEmail": self.user.email if self.user else None,
            "category": self.category,
            "sentAt": self.sent_at.strftime("%Y-%m-%d %H:%M:%S"),
            "emailSent": self.email_sent,
            "submissionCount": self.submission_count,
            "markedCount": self.marked_count,
            "sentBy": self.trigger_user.name if self.trigger_user else "System",
        }

class SubmissionToken(db.Model):
    """
    Secure tokens for posting submissions on behalf of students.
    Each token is single-use and tied to a specific student and challenge.
    Uses HMAC-based security to prevent forgery.
    """
    __tablename__ = "submission_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    challenge_id = Column(Integer, ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(256), nullable=False, unique=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # Admin/tutor who created it
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)  # Token expiration time
    used_at = Column(DateTime, nullable=True)  # When token was used (null = unused)
    used = Column(Boolean, default=False)  # Whether this token has been used

    user = relationship("Users", foreign_keys=[user_id], lazy="joined")
    challenge = relationship("Challenges", foreign_keys=[challenge_id], lazy="joined")
    creator = relationship("Users", foreign_keys=[created_by], lazy="select")

    def to_dict(self):
        return {
            "id": self.id,
            "userId": self.user_id,
            "userName": self.user.name if self.user else None,
            "challengeId": self.challenge_id,
            "challengeName": self.challenge.name if self.challenge else None,
            "createdBy": self.creator.name if self.creator else None,
            "createdAt": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "expiresAt": self.expires_at.strftime("%Y-%m-%d %H:%M:%S"),
            "used": self.used,
            "usedAt": self.used_at.strftime("%Y-%m-%d %H:%M:%S") if self.used_at else None,
        }

    def __repr__(self):
        return f"<SubmissionToken {self.id} - User {self.user_id} Challenge {self.challenge_id}>"