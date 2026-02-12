from CTFd.models import db
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime


class MarkingAssignment(db.Model):
    """
    Assigns a registered user to a specific admin/tutor.
    One user can be assigned to at most one tutor.
    """
    __tablename__ = "marking_assignments"
    __table_args__ = (UniqueConstraint("user_id", name="uq_marking_assignments_user_id"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tutor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_at = Column(DateTime, nullable=True)

    user = relationship("Users", foreign_keys=[user_id], lazy="joined")
    tutor = relationship("Users", foreign_keys=[tutor_id], lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "userId": self.user_id,
            "userName": self.user.name if self.user else None,
            "userEmail": self.user.email if self.user else None,
            "tutorId": self.tutor_id,
            "tutorName": self.tutor.name if self.tutor else None,
            "tutorEmail": self.tutor.email if self.tutor else None,
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
        assignment = MarkingAssignment.query.filter_by(user_id=sub.user_id).first()

        return {
            "id": self.id,
            "submissionId": sub.id,
            "userId": sub.user_id,
            "challengeId": sub.challenge_id,
            "name": user.name if user else "Unknown",
            "zid": user.email.split("@")[0] if user and "@" in user.email else "N/A",
            "submittedAt": sub.date.strftime("%Y-%m-%d %H:%M:%S") if sub.date else None,
            "flag": sub.provided,  # The submitted flag/answer
            "challenge": challenge.name if challenge else "Unknown",
            "challengeUrl": f"/challenges#{challenge.id}" if challenge else None,
            "challengeHtml": challenge.html if challenge else None,
            "challengeConnectionInfo": challenge.connection_info if challenge else None,
            "category": challenge.category if challenge else "Uncategorized",
            "mark": self.mark,
            "comment": self.comment,
            "markedAt": self.marked_at.strftime("%Y-%m-%d %H:%M:%S") if self.marked_at else None,
            "markedBy": self.marker.name if self.marker else None,
            "assignedTutorId": assignment.tutor_id if assignment else None,
            "assignedTutorName": assignment.tutor.name if assignment and assignment.tutor else None,
        }


class StudentReport(db.Model):
    """
    Tracks when student performance reports were generated and sent.
    """
    __tablename__ = "student_reports"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
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
            "sentAt": self.sent_at.strftime("%Y-%m-%d %H:%M:%S"),
            "emailSent": self.email_sent,
            "submissionCount": self.submission_count,
            "markedCount": self.marked_count,
            "sentBy": self.trigger_user.name if self.trigger_user else "System",
        }
