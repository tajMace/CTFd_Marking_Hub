import os
from flask import render_template, send_from_directory, jsonify, request
from CTFd.models import db, Users
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.utils.user import get_current_user, is_admin
from CTFd.plugins import bypass_csrf_protection
from .models import MarkingSubmission, MarkingAssignment, MarkingTutor, MarkingDeadline
from datetime import datetime

def load(app):
    # Create tables if they don't exist
    with app.app_context():
        db.create_all()

    # Custom asset route
    dir_path = os.path.dirname(os.path.realpath(__file__))
    assets_path = os.path.join(dir_path, "assets", "dist")
    
    @app.route("/marking_hub_assets/<path:filename>")
    def marking_hub_assets(filename):
        return send_from_directory(assets_path, filename)
    
    # Marking hub dashboard route
    @app.route("/marking_hub", methods=["GET"])
    @admins_only
    def marking_hub():
        from flask import session
        nonce = session.get('nonce')
        return render_template("plugins/CTFd_Marking_Hub/templates/marking_dashboard.html", nonce=nonce)

    # Tutor login page route
    @app.route("/marking_hub/login", methods=["GET"])
    def marking_hub_login():
        from flask import session
        nonce = session.get('nonce')
        return render_template("plugins/CTFd_Marking_Hub/templates/marking_dashboard.html", nonce=nonce)
    
    def _is_tutor(user_id):
        return MarkingTutor.query.filter_by(user_id=user_id).first() is not None

    # API: Get all marking submissions (admin = all, tutor = assigned only)
    @app.route("/api/marking_hub/submissions", methods=["GET"])
    @authed_only
    def get_marking_submissions():
        user = get_current_user()

        if is_admin():
            submissions = MarkingSubmission.query.all()
            return jsonify([sub.to_dict() for sub in submissions])

        if not _is_tutor(user.id):
            return jsonify({"message": "Forbidden"}), 403

        assigned_user_ids = [
            row.user_id
            for row in MarkingAssignment.query.filter_by(tutor_id=user.id).all()
        ]

        if not assigned_user_ids:
            return jsonify([])

        from CTFd.models import Submissions

        submissions = (
            MarkingSubmission.query
            .join(Submissions, MarkingSubmission.submission_id == Submissions.id)
            .filter(Submissions.user_id.in_(assigned_user_ids))
            .all()
        )
        return jsonify([sub.to_dict() for sub in submissions])
    
    # API: Get single submission
    @app.route("/api/marking_hub/submissions/<int:submission_id>", methods=["GET"])
    @authed_only
    def get_marking_submission(submission_id):
        user = get_current_user()
        submission = MarkingSubmission.query.get_or_404(submission_id)

        if is_admin():
            return jsonify(submission.to_dict())

        if not _is_tutor(user.id):
            return jsonify({"message": "Forbidden"}), 403

        assignment = MarkingAssignment.query.filter_by(
            user_id=submission.submission.user_id,
            tutor_id=user.id,
        ).first()

        if assignment is None:
            return jsonify({"message": "Forbidden"}), 403

        return jsonify(submission.to_dict())
    
    # API: Save mark and comment
    @app.route("/api/marking_hub/submissions/<int:submission_id>", methods=["PUT"])
    @authed_only
    @bypass_csrf_protection
    def update_marking_submission(submission_id):
        user = get_current_user()

        submission = MarkingSubmission.query.get_or_404(submission_id)

        if not is_admin():
            if not _is_tutor(user.id):
                return jsonify({"message": "Forbidden"}), 403

            assignment = MarkingAssignment.query.filter_by(
                user_id=submission.submission.user_id,
                tutor_id=user.id,
            ).first()

            if assignment is None:
                return jsonify({"message": "Forbidden"}), 403

        data = request.get_json()

        submission.mark = data.get('mark')
        submission.comment = data.get('comment')
        submission.marked_at = datetime.utcnow()
        submission.marked_by = user.id

        db.session.commit()

        return jsonify(submission.to_dict())
    
    # API: Sync CTFd submissions to marking table
    @app.route("/api/marking_hub/sync", methods=["POST"])
    @admins_only
    @bypass_csrf_protection
    def sync_submissions():
        from CTFd.models import Submissions

        all_submissions = Submissions.query.all()
        synced = 0

        for sub in all_submissions:
            existing = MarkingSubmission.query.filter_by(submission_id=sub.id).first()
            if not existing:
                marking_sub = MarkingSubmission(
                    submission_id=sub.id,
                    mark=None,
                    comment=None
                )
                db.session.add(marking_sub)
                synced += 1

        db.session.commit()
        return jsonify({"message": f"Synced {synced} submissions"})

    # API: Get all tutor assignments
    @app.route("/api/marking_hub/assignments", methods=["GET"])
    @admins_only
    def get_marking_assignments():
        assignments = MarkingAssignment.query.all()
        return jsonify([assignment.to_dict() for assignment in assignments])

    # API: Get assignment for a specific user
    @app.route("/api/marking_hub/assignments/<int:user_id>", methods=["GET"])
    @admins_only
    def get_marking_assignment(user_id):
        assignment = MarkingAssignment.query.filter_by(user_id=user_id).first()
        if not assignment:
            return jsonify({"message": "Assignment not found"}), 404
        return jsonify(assignment.to_dict())

    # API: Get assignments for the current tutor
    @app.route("/api/marking_hub/assignments/mine", methods=["GET"])
    @authed_only
    def get_marking_assignments_for_current_tutor():
        user = get_current_user()

        if not is_admin() and not _is_tutor(user.id):
            return jsonify({"message": "Forbidden"}), 403

        assignments = MarkingAssignment.query.filter_by(tutor_id=user.id).all()
        return jsonify([assignment.to_dict() for assignment in assignments])

    # API: Assign or update tutor for a user
    @app.route("/api/marking_hub/assignments/<int:user_id>", methods=["PUT"])
    @admins_only
    @bypass_csrf_protection
    def set_marking_assignment(user_id):
        data = request.get_json() or {}
        tutor_id = data.get("tutor_id")

        user = Users.query.filter_by(id=user_id).first_or_404()

        tutor = None
        if tutor_id is not None:
            tutor = Users.query.filter_by(id=tutor_id).first_or_404()
            if tutor.type != "admin" and not _is_tutor(tutor.id):
                return jsonify({"message": "Tutor must be a marked tutor or admin"}), 400

        assignment = MarkingAssignment.query.filter_by(user_id=user.id).first()
        if assignment is None:
            assignment = MarkingAssignment(user_id=user.id)
            db.session.add(assignment)

        assignment.tutor_id = tutor.id if tutor else None
        assignment.assigned_at = datetime.utcnow() if tutor else None

        db.session.commit()
        return jsonify(assignment.to_dict())

    # API: Remove tutor assignment for a user
    @app.route("/api/marking_hub/assignments/<int:user_id>", methods=["DELETE"])
    @admins_only
    @bypass_csrf_protection
    def delete_marking_assignment(user_id):
        assignment = MarkingAssignment.query.filter_by(user_id=user_id).first()
        if assignment:
            db.session.delete(assignment)
            db.session.commit()
        return jsonify({"message": "Assignment removed"})

    # API: List tutors
    @app.route("/api/marking_hub/tutors", methods=["GET"])
    @admins_only
    def get_marking_tutors():
        tutors = MarkingTutor.query.all()
        return jsonify([tutor.to_dict() for tutor in tutors])

    # API: Add tutor
    @app.route("/api/marking_hub/tutors", methods=["POST"])
    @admins_only
    @bypass_csrf_protection
    def add_marking_tutor():
        data = request.get_json() or {}
        user_id = data.get("user_id")

        if not user_id:
            return jsonify({"message": "user_id is required"}), 400

        user = Users.query.filter_by(id=user_id).first_or_404()

        existing = MarkingTutor.query.filter_by(user_id=user.id).first()
        if existing:
            return jsonify(existing.to_dict())

        tutor = MarkingTutor(user_id=user.id)
        db.session.add(tutor)
        db.session.commit()
        return jsonify(tutor.to_dict())

    # API: Remove tutor
    @app.route("/api/marking_hub/tutors/<int:user_id>", methods=["DELETE"])
    @admins_only
    @bypass_csrf_protection
    def delete_marking_tutor(user_id):
        tutor = MarkingTutor.query.filter_by(user_id=user_id).first()
        if tutor:
            db.session.delete(tutor)
            db.session.commit()
        return jsonify({"message": "Tutor removed"})

    # API: Check current tutor status
    @app.route("/api/marking_hub/tutors/me", methods=["GET"])
    @authed_only
    def get_current_tutor_status():
        user = get_current_user()
        return jsonify({"isTutor": _is_tutor(user.id), "isAdmin": is_admin()})

    # API: Get all marking deadlines
    @app.route("/api/marking_hub/deadlines", methods=["GET"])
    @authed_only
    def get_marking_deadlines():
        deadlines = MarkingDeadline.query.all()
        return jsonify([deadline.to_dict() for deadline in deadlines])

    # API: Get deadline for a specific challenge
    @app.route("/api/marking_hub/deadlines/<int:challenge_id>", methods=["GET"])
    @authed_only
    def get_marking_deadline(challenge_id):
        deadline = MarkingDeadline.query.filter_by(challenge_id=challenge_id).first()
        if not deadline:
            return jsonify({"message": "Deadline not found"}), 404
        return jsonify(deadline.to_dict())

    # API: Set or update marking deadline for a challenge
    @app.route("/api/marking_hub/deadlines/<int:challenge_id>", methods=["PUT"])
    @admins_only
    @bypass_csrf_protection
    def set_marking_deadline(challenge_id):
        from CTFd.models import Challenges

        data = request.get_json() or {}
        due_date_str = data.get("due_date")

        if not due_date_str:
            return jsonify({"message": "due_date is required"}), 400

        challenge = Challenges.query.filter_by(id=challenge_id).first_or_404()

        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%dT%H:%M")
        except ValueError:
            return jsonify({"message": "Invalid date format. Use YYYY-MM-DDTHH:MM"}), 400

        deadline = MarkingDeadline.query.filter_by(challenge_id=challenge.id).first()
        if deadline is None:
            deadline = MarkingDeadline(challenge_id=challenge.id, due_date=due_date)
            db.session.add(deadline)
        else:
            deadline.due_date = due_date

        db.session.commit()
        return jsonify(deadline.to_dict())

    # API: Remove marking deadline for a challenge
    @app.route("/api/marking_hub/deadlines/<int:challenge_id>", methods=["DELETE"])
    @admins_only
    @bypass_csrf_protection
    def delete_marking_deadline(challenge_id):
        deadline = MarkingDeadline.query.filter_by(challenge_id=challenge_id).first()
        if deadline:
            db.session.delete(deadline)
            db.session.commit()
        return jsonify({"message": "Deadline removed"})

