from CTFd.models import db
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

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
            "mark": self.mark,
            "comment": self.comment,
            "markedAt": self.marked_at.strftime("%Y-%m-%d %H:%M:%S") if self.marked_at else None,
            "markedBy": self.marker.name if self.marker else None,
        }