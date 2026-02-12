import os
from flask import render_template, send_from_directory, jsonify, request, send_file
from CTFd.models import db, Users
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.utils.user import get_current_user, is_admin
from CTFd.plugins import bypass_csrf_protection
from .models import MarkingSubmission, MarkingAssignment, MarkingTutor, MarkingDeadline, StudentReport
from .utils.report_generator import generate_and_send_student_report, generate_weekly_reports, get_available_categories
from .utils.pdf_generator import generate_student_report_pdf
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

    # API: Generate and send report for a specific student
    @app.route("/api/marking_hub/reports/send/<int:user_id>", methods=["POST"])
    @admins_only
    @bypass_csrf_protection
    def send_student_report(user_id):
        from flask import request
        user = get_current_user()
        category = request.args.get('category', None)
        success, message = generate_and_send_student_report(user_id, triggered_by_user_id=user.id, category=category)
        
        if success:
            return jsonify({"success": True, "message": message})
        else:
            return jsonify({"success": False, "message": message}), 400

    # API: Download student report as PDF
    @app.route("/api/marking_hub/reports/download/<int:user_id>", methods=["GET"])
    @admins_only
    def download_student_report(user_id):
        from CTFd.models import Users
        from .utils.report_generator import get_student_submissions_for_report
        from CTFd.utils import get_config
        
        student = Users.query.get_or_404(user_id)
        submissions = get_student_submissions_for_report(user_id)
        
        if not submissions:
            return jsonify({"error": "No marked submissions for this student"}), 404
        
        ctf_name = get_config('ctf_name', 'CTF')
        pdf_buffer = generate_student_report_pdf(
            student_name=student.name,
            student_email=student.email,
            submissions=submissions,
            ctf_name=ctf_name
        )
        
        filename = f"report_{student.name.replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    # API: Get all student reports (admin only, for tracking)
    @app.route("/api/marking_hub/reports", methods=["GET"])
    @admins_only
    def get_student_reports():
        reports = StudentReport.query.order_by(StudentReport.sent_at.desc()).all()
        return jsonify([report.to_dict() for report in reports])

    # API: Get reports for a specific student
    @app.route("/api/marking_hub/reports/student/<int:user_id>", methods=["GET"])
    @admins_only
    def get_student_reports_for_user(user_id):
        reports = StudentReport.query.filter_by(user_id=user_id).order_by(StudentReport.sent_at.desc()).all()
        return jsonify([report.to_dict() for report in reports])

    # API: Trigger weekly reports for all students
    @app.route("/api/marking_hub/reports/send-weekly", methods=["POST"])
    @admins_only
    @bypass_csrf_protection
    def trigger_weekly_reports():
        try:
            results = generate_weekly_reports()
            return jsonify({
                "success": True,
                "message": f"Reports sent to {results['sent']} students, {results['failed']} failed",
                "details": results
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"Error generating reports: {str(e)}"
            }), 500

    # API: Get available challenge categories (weeks)
    @app.route("/api/marking_hub/categories", methods=["GET"])
    @admins_only
    def get_categories():
        try:
            categories = get_available_categories()
            return jsonify({
                "success": True,
                "categories": categories
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"Error fetching categories: {str(e)}"
            }), 500

    # API: Get categories with unmarked submission counts
    @app.route("/api/marking_hub/categories-with-counts", methods=["GET"])
    @authed_only
    def get_categories_with_counts():
        try:
            from CTFd.models import Submissions, Challenges
            from sqlalchemy import func
            
            user = get_current_user()
            
            # Get submissions visible to this user
            if is_admin():
                submissions_query = MarkingSubmission.query.join(
                    Submissions, MarkingSubmission.submission_id == Submissions.id
                ).join(
                    Challenges, Submissions.challenge_id == Challenges.id
                )
            else:
                if not _is_tutor(user.id):
                    return jsonify({"message": "Forbidden"}), 403
                
                assigned_user_ids = [
                    row.user_id
                    for row in MarkingAssignment.query.filter_by(tutor_id=user.id).all()
                ]
                
                if not assigned_user_ids:
                    return jsonify({
                        "success": True,
                        "categories": []
                    })
                
                submissions_query = MarkingSubmission.query.join(
                    Submissions, MarkingSubmission.submission_id == Submissions.id
                ).join(
                    Challenges, Submissions.challenge_id == Challenges.id
                ).filter(Submissions.user_id.in_(assigned_user_ids))
            
            # Get all submissions with their categories
            submissions = submissions_query.all()
            
            # Group by category and count marked/unmarked
            category_counts = {}
            for sub in submissions:
                category = sub.submission.challenge.category if sub.submission.challenge else "Uncategorized"
                if category not in category_counts:
                    category_counts[category] = {"total": 0, "unmarked": 0}
                category_counts[category]["total"] += 1
                if sub.mark is None:
                    category_counts[category]["unmarked"] += 1
            
            # Format response
            categories = [
                {
                    "category": cat,
                    "unmarkedCount": counts["unmarked"],
                    "totalCount": counts["total"]
                }
                for cat, counts in sorted(category_counts.items())
            ]
            
            return jsonify({
                "success": True,
                "categories": categories
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"Error fetching categories with counts: {str(e)}"
            }), 500

    # API: Trigger reports for a specific category (week)
    @app.route("/api/marking_hub/reports/send-by-category/<category>", methods=["POST"])
    @admins_only
    @bypass_csrf_protection
    def trigger_category_reports(category):
        try:
            results = generate_weekly_reports(category=category)
            return jsonify({
                "success": True,
                "message": f"Reports sent to {results['sent']} students for {category}, {results['failed']} failed",
                "details": results
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"Error generating reports for {category}: {str(e)}"
            }), 500

