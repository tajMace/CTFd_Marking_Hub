import os
from flask import render_template, send_from_directory, jsonify, request, send_file
from CTFd.models import db, Users
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.utils.user import get_current_user, is_admin
from CTFd.plugins import bypass_csrf_protection
from .models import MarkingSubmission, MarkingAssignmentHelper, MarkingTutor, MarkingDeadline, StudentReport, SubmissionToken
from .utils.report_generator import generate_and_send_student_report, generate_weekly_reports, get_available_categories
from .utils.pdf_generator import generate_student_report_pdf
from datetime import datetime

def load(app):
    # Load automarker secret from environment
    app.config['MARKING_HUB_AUTOMARKER_SECRET'] = os.getenv('MARKING_HUB_AUTOMARKER_SECRET')
    
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
    
    # Student reports page route
    @app.route("/my-reports", methods=["GET"])
    @authed_only
    def student_reports():
        return render_template("plugins/CTFd_Marking_Hub/templates/student_reports.html")
    
    def _is_tutor(user_id):
        return MarkingTutor.query.filter_by(user_id=user_id).first() is not None

    def _is_technical_challenge(challenge):
        if not challenge or not challenge.name:
            return False
        return challenge.name.lstrip().upper().startswith("TECH")

    # API: Get all marking submissions (admin = all, tutor = assigned only)
    @app.route("/api/marking_hub/submissions", methods=["GET"])
    @authed_only
    def get_marking_submissions():
        user = get_current_user()
        include_tech = request.args.get("include_tech", "false").lower() in {"1", "true", "yes"}

        if is_admin():
            submissions = MarkingSubmission.query.all()
            if include_tech:
                return jsonify([sub.to_dict() for sub in submissions])
            visible = [sub for sub in submissions if not _is_technical_challenge(sub.submission.challenge)]
            return jsonify([sub.to_dict() for sub in visible])

        if not _is_tutor(user.id):
            return jsonify({"message": "Forbidden"}), 403


        # Get all students assigned to this tutor (many-to-many)
        assigned_user_ids = [student.id for student in user.students]

        if not assigned_user_ids:
            return jsonify([])

        from CTFd.models import Submissions

        submissions = (
            MarkingSubmission.query
            .join(Submissions, MarkingSubmission.submission_id == Submissions.id)
            .filter(Submissions.user_id.in_(assigned_user_ids))
            .all()
        )
        if include_tech:
            return jsonify([sub.to_dict() for sub in submissions])
        visible = [sub for sub in submissions if not _is_technical_challenge(sub.submission.challenge)]
        return jsonify([sub.to_dict() for sub in visible])
    
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


        # Check if this tutor is assigned to the student
        student = Users.query.get(submission.submission.user_id)
        if not student or user not in student.tutors:
            return jsonify({"message": "Forbidden"}), 403

        return jsonify(submission.to_dict())
    
    # API: Save mark and comment
    @app.route("/api/marking_hub/submissions/<int:submission_id>", methods=["PUT"])
    @authed_only
    @bypass_csrf_protection
    def update_marking_submission(submission_id):
        user = get_current_user()

        submission = MarkingSubmission.query.get_or_404(submission_id)

        if _is_technical_challenge(submission.submission.challenge):
            return jsonify({"message": "Technical submissions are not manually marked"}), 400

        if not is_admin():
            if not _is_tutor(user.id):
                return jsonify({"message": "Forbidden"}), 403


            student = Users.query.get(submission.submission.user_id)
            if not student or user not in student.tutors:
                return jsonify({"message": "Forbidden"}), 403

        data = request.get_json()

        submission.mark = data.get('mark')
        submission.comment = data.get('comment')
        submission.marked_at = datetime.utcnow()
        submission.marked_by = user.id

        db.session.commit()

        return jsonify(submission.to_dict())
    
    # API: Sync CTFd submissions to marking table (with auto-mark for TECH)
    @app.route("/api/marking_hub/sync", methods=["POST"])
    @admins_only
    @bypass_csrf_protection
    def sync_submissions():
        from CTFd.models import Submissions

        all_submissions = Submissions.query.all()
        synced = 0
        auto_marked = 0

        for sub in all_submissions:
            existing = MarkingSubmission.query.filter_by(submission_id=sub.id).first()

            # Determine correctness by type
            is_correct = getattr(sub, 'correct', None)
            if is_correct is None:
                # Fails/incorrect submissions do not have .correct, but type is 'incorrect'
                is_correct = getattr(sub, 'type', None) == 'correct'

            if not existing:
                # Create new marking submission
                marking_sub = MarkingSubmission(
                    submission_id=sub.id,
                    mark=None,
                    comment=None
                )

                # Auto-mark TECH submissions based on correctness
                if _is_technical_challenge(sub.challenge):
                    challenge_max = sub.challenge.value if sub.challenge else 100
                    marking_sub.mark = challenge_max if is_correct else 0
                    marking_sub.marked_at = datetime.utcnow()
                    # Mark as auto-marked by system (get first admin user)
                    autotest_user = Users.query.filter_by(id=6).first()
                    if autotest_user:
                        marking_sub.marked_by = autotest_user.id
                    auto_marked += 1

                db.session.add(marking_sub)
                synced += 1
            else:
                # Update existing TECH submissions if correctness changed
                if _is_technical_challenge(sub.challenge):
                    challenge_max = sub.challenge.value if sub.challenge else 100
                    new_mark = challenge_max if is_correct else 0
                    # Update mark if it differs from current (student may have submitted correct flag after initial rejection)
                    if existing.mark != new_mark:
                        existing.mark = new_mark
                        existing.marked_at = datetime.utcnow()
                        first_admin = Users.query.filter_by(type="admin").order_by(Users.id).first()
                        if first_admin:
                            existing.marked_by = first_admin.id
                        db.session.add(existing)

        db.session.commit()
        return jsonify({
            "message": f"Synced {synced} new submissions",
            "auto_marked_tech": auto_marked
        })

    # API: Generate secure token for submitting on behalf of student
    @app.route("/api/marking_hub/submissions/generate-token", methods=["POST"])
    @bypass_csrf_protection
    def generate_submission_token():
        import hmac
        import hashlib
        import secrets
        from datetime import timedelta
        from .models import SubmissionToken
        
        # Validate automarker secret header
        automarker_secret = app.config.get('MARKING_HUB_AUTOMARKER_SECRET')
        if not automarker_secret:
            return jsonify({"message": "Automarker secret not configured on server"}), 500
        
        provided_secret = request.headers.get('X-Automarker-Secret', '')
        if not hmac.compare_digest(provided_secret, automarker_secret):
            return jsonify({"message": "Invalid or missing automarker secret"}), 403
        
        data = request.get_json() or {}
        user_id = data.get("user_id")
        challenge_id = data.get("challenge_id")
        expires_in_hours = data.get("expires_in_hours", 24)  # Default 24 hours

        if not user_id or not challenge_id:
            return jsonify({"message": "user_id and challenge_id are required"}), 400

        from CTFd.models import Users, Challenges
        
        user = Users.query.filter_by(id=user_id).first_or_404()
        challenge = Challenges.query.filter_by(id=challenge_id).first_or_404()

        # Generate random token
        random_token = secrets.token_urlsafe(32)
        
        # Create HMAC hash (this is what the client will send back)
        # Use automarker secret key for signing (must be stable)
        secret = app.config.get('MARKING_HUB_AUTOMARKER_SECRET')
        if not secret:
            return jsonify({"message": "Automarker secret not configured on server"}), 500
        secret_bytes = secret.encode() if isinstance(secret, str) else secret
        token_hash = hmac.new(
            secret_bytes,
            f"{user_id}:{challenge_id}:{random_token}".encode(),
            hashlib.sha256
        ).hexdigest()

        # Create expiration timestamp
        expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)

        submission_token = SubmissionToken(
            user_id=user_id,
            challenge_id=challenge_id,
            token_hash=token_hash,
            created_by=None,  # System-generated token, not tied to a specific admin user
            expires_at=expires_at
        )

        db.session.add(submission_token)
        db.session.commit()

        return jsonify({
            "token": random_token,
            "token_id": submission_token.id,
            "user_id": user_id,
            "user_name": user.name,
            "challenge_id": challenge_id,
            "challenge_name": challenge.name,
            "hash": token_hash,
            "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    # API: Post submission on behalf of student using secure token
    @app.route("/api/marking_hub/submissions/on-behalf-of", methods=["POST"])
    @bypass_csrf_protection
    def post_submission_on_behalf():
        import hmac
        import hashlib
        from .models import SubmissionToken
        from CTFd.models import Submissions, Users, Challenges, Teams
        
        data = request.get_json() or {}
        user_id = data.get("user_id")
        challenge_id = data.get("challenge_id")
        flag = data.get("flag")
        token = data.get("token")
        token_hash = data.get("hash")

        if not all([user_id, challenge_id, flag, token, token_hash]):
            return jsonify({"message": "user_id, challenge_id, flag, token, and hash are required"}), 400

        if not isinstance(flag, str):
            return jsonify({"message": "flag must be a string"}), 400

        provided_flag = flag.strip()
        if not provided_flag:
            return jsonify({"message": "flag cannot be empty"}), 400

        # Verify the token
        secret = app.config.get('MARKING_HUB_AUTOMARKER_SECRET')
        if not secret:
            return jsonify({"message": "Automarker secret not configured on server"}), 500
        secret_bytes = secret.encode() if isinstance(secret, str) else secret
        expected_hash = hmac.new(
            secret_bytes,
            f"{user_id}:{challenge_id}:{token}".encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_hash, token_hash):
            return jsonify({"message": "Invalid security hash"}), 403

        # Find and validate the token
        submission_token = SubmissionToken.query.filter_by(
            user_id=user_id,
            challenge_id=challenge_id,
            token_hash=token_hash
        ).first()

        if not submission_token:
            return jsonify({"message": "Token not found or invalid"}), 404

        # Check if token is already used
        if submission_token.used:
            return jsonify({"message": "Token already used"}), 403

        # Check if token is expired
        if submission_token.expires_at < datetime.utcnow():
            return jsonify({"message": "Token expired"}), 403

        # Verify user and challenge exist
        user = Users.query.filter_by(id=user_id).first_or_404()
        challenge = Challenges.query.filter_by(id=challenge_id).first_or_404()

        try:
            # Auto-evaluate the flag by checking against challenge flags
            try:
                import re
                from CTFd.models import Flags
                # Get all valid flags for this challenge
                challenge_flags = Flags.query.filter_by(challenge_id=challenge_id).all()
                is_correct = False

                app.logger.info(f"Validating flag for challenge {challenge_id}: '{provided_flag}'")
                app.logger.info(f"Found {len(challenge_flags)} flags for challenge")

                if challenge_flags:
                    for challenge_flag in challenge_flags:
                        # Log all attributes to understand the data structure
                        flag_content = getattr(challenge_flag, 'content', None)  # CTFd uses 'content' attribute
                        flag_type = getattr(challenge_flag, 'type', 'static')

                        app.logger.info(f"Flag content: '{flag_content}', Type: {flag_type}")

                        if not flag_content:
                            continue

                        # Handle different flag types
                        if flag_type == 'regex':
                            # Regex flag matching
                            try:
                                if re.match(flag_content, provided_flag):
                                    app.logger.info("Flag matched regex pattern")
                                    is_correct = True
                                    break
                            except re.error as e:
                                app.logger.error(f"Invalid regex pattern: {str(e)}")
                                continue
                        else:
                            # Literal flag matching (case-insensitive, trimmed)
                            if flag_content.strip().lower() == provided_flag.lower():
                                app.logger.info("Flag matched literal pattern")
                                is_correct = True
                                break

                app.logger.info(f"Final result: correct={is_correct}")
            except Exception as e:
                app.logger.error(f"Error validating flag: {str(e)}")
                import traceback
                app.logger.error(traceback.format_exc())
                is_correct = False

            # Create submission in CTFd
            if is_correct:
                from CTFd.models import Solves
                submission = Solves(
                    user_id=user_id,
                    team_id=user.team_id if hasattr(user, 'team_id') else None,
                    challenge_id=challenge_id,
                    ip='127.0.0.1',  # Internal submission
                    provided=provided_flag,
                    date=datetime.utcnow()
                )
            else:
                from CTFd.models import Fails
                submission = Fails(
                    user_id=user_id,
                    team_id=user.team_id if hasattr(user, 'team_id') else None,
                    challenge_id=challenge_id,
                    ip='127.0.0.1',  # Internal submission
                    provided=provided_flag,
                    date=datetime.utcnow()
                )

            db.session.add(submission)
            db.session.flush()  # Get the submission ID

            # Create corresponding marking submission
            marking_sub = MarkingSubmission(
                submission_id=submission.id,
                mark=None,
                comment=None
            )

            # Auto-mark TECH submissions
            if _is_technical_challenge(challenge):
                challenge_max = challenge.value if challenge else 100
                marking_sub.mark = challenge_max if is_correct else 0
                marking_sub.marked_at = datetime.utcnow()

            db.session.add(marking_sub)

            # Mark token as used
            submission_token.used = True
            submission_token.used_at = datetime.utcnow()

            db.session.commit()

            return jsonify({
                "success": True,
                "submission_id": submission.id,
                "user_id": user_id,
                "user_name": user.name,
                "challenge_id": challenge_id,
                "challenge_name": challenge.name,
                "flag": flag,
                "correct": is_correct,
                "submitted_at": submission.date.strftime("%Y-%m-%d %H:%M:%S")
            }), 201

        except Exception as e:
            db.session.rollback()
            import traceback
            app.logger.error(f"Error posting submission on behalf of user {user_id}: {str(e)}")
            app.logger.error(traceback.format_exc())
            return jsonify({"message": f"Failed to submit: {str(e)}"}), 500


    # API: Get all tutor assignments (many-to-many)
    @app.route("/api/marking_hub/assignments", methods=["GET"])
    @admins_only
    def get_marking_assignments():
        users = Users.query.all()
        results = []
        for student in users:
            for tutor in student.tutors:
                # Find assigned_at from association table
                assigned_at = None
                for row in db.session.execute(
                    "SELECT assigned_at FROM marking_assignments WHERE student_id = :sid AND tutor_id = :tid",
                    {"sid": student.id, "tid": tutor.id}
                ):
                    assigned_at = row[0]
                results.append(MarkingAssignmentHelper(student, tutor, assigned_at).to_dict())
        return jsonify(results)


    # API: Get all tutors for a specific student
    @app.route("/api/marking_hub/assignments/<int:user_id>", methods=["GET"])
    @admins_only
    def get_marking_assignment(user_id):
        student = Users.query.get_or_404(user_id)
        results = []
        for tutor in student.tutors:
            assigned_at = None
            for row in db.session.execute(
                "SELECT assigned_at FROM marking_assignments WHERE student_id = :sid AND tutor_id = :tid",
                {"sid": student.id, "tid": tutor.id}
            ):
                assigned_at = row[0]
            results.append(MarkingAssignmentHelper(student, tutor, assigned_at).to_dict())
        if not results:
            return jsonify({"message": "No tutors assigned"}), 404
        return jsonify(results)


    # API: Get all students assigned to the current tutor
    @app.route("/api/marking_hub/assignments/mine", methods=["GET"])
    @authed_only
    def get_marking_assignments_for_current_tutor():
        user = get_current_user()

        if not is_admin() and not _is_tutor(user.id):
            return jsonify({"message": "Forbidden"}), 403

        results = []
        for student in user.students:
            assigned_at = None
            for row in db.session.execute(
                "SELECT assigned_at FROM marking_assignments WHERE student_id = :sid AND tutor_id = :tid",
                {"sid": student.id, "tid": user.id}
            ):
                assigned_at = row[0]
            results.append(MarkingAssignmentHelper(student, user, assigned_at).to_dict())
        return jsonify(results)


    # API: Assign or update tutors for a user (student)
    @app.route("/api/marking_hub/assignments/<int:user_id>", methods=["PUT"])
    @admins_only
    @bypass_csrf_protection
    def set_marking_assignment(user_id):
        data = request.get_json() or {}
        tutor_ids = data.get("tutor_ids", [])
        student = Users.query.filter_by(id=user_id).first_or_404()

        # Remove all current tutors
        student.tutors = []
        db.session.commit()

        # Add new tutors
        for tid in tutor_ids:
            tutor = Users.query.filter_by(id=tid).first()
            if tutor and (tutor.type == "admin" or _is_tutor(tutor.id)):
                student.tutors.append(tutor)
                # Set assigned_at in association table
                db.session.execute(
                    "UPDATE marking_assignments SET assigned_at = :assigned_at WHERE student_id = :sid AND tutor_id = :tid",
                    {"assigned_at": datetime.utcnow(), "sid": student.id, "tid": tutor.id}
                )
        db.session.commit()

        # Return updated assignments
        results = []
        for tutor in student.tutors:
            assigned_at = None
            for row in db.session.execute(
                "SELECT assigned_at FROM marking_assignments WHERE student_id = :sid AND tutor_id = :tid",
                {"sid": student.id, "tid": tutor.id}
            ):
                assigned_at = row[0]
            results.append(MarkingAssignmentHelper(student, tutor, assigned_at).to_dict())
        return jsonify(results)


    # API: Remove all tutor assignments for a user (student)
    @app.route("/api/marking_hub/assignments/<int:user_id>", methods=["DELETE"])
    @admins_only
    @bypass_csrf_protection
    def delete_marking_assignment(user_id):
        student = Users.query.filter_by(id=user_id).first_or_404()
        student.tutors = []
        db.session.commit()
        return jsonify({"message": "All tutor assignments removed"})

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

    # API: Download student report as PDF (admin only)
    @app.route("/api/marking_hub/reports/download/<int:user_id>", methods=["GET"])
    @admins_only
    def download_student_report(user_id):
        try:
            import traceback
            from io import BytesIO
            from CTFd.models import Users
            from .utils.report_generator import get_student_submissions_for_report
            from CTFd.utils import get_config
            from flask import request
            
            # Get optional category parameter
            category = request.args.get('category', None)
            
            student = Users.query.get_or_404(user_id)
            submissions = get_student_submissions_for_report(user_id, category=category)
            
            print(f"[PDF DEBUG] Download for user {user_id}, category={category}: Found {len(submissions)} submissions", flush=True)
            print(f"[PDF DEBUG] Submissions data: {submissions}", flush=True)
            
            if not submissions:
                category_msg = f" for {category}" if category else ""
                return jsonify({"error": f"No marked submissions for this student{category_msg}"}), 404
            
            ctf_name = get_config('ctf_name', 'CTF')
            subtitle = f"{category} Report" if category else "Full Performance Report"
            pdf_buffer = generate_student_report_pdf(
                student_name=student.name,
                student_email=student.email,
                submissions=submissions,
                ctf_name=ctf_name,
                subtitle=subtitle
            )
            
            filename = f"report_{student.name.replace(' ', '_')}_{category or 'full'}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
            
            print(f"[PDF DEBUG] Creating response for {filename}", flush=True)
            
            # Read entire buffer and create response
            pdf_data = pdf_buffer.read()
            print(f"[PDF DEBUG] PDF data size: {len(pdf_data)} bytes", flush=True)
            print(f"[PDF DEBUG] First 20 bytes: {pdf_data[:20]}", flush=True)
            
            from flask import make_response
            response = make_response(pdf_data)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
            response.headers['Content-Length'] = str(len(pdf_data))
            print(f"[PDF DEBUG] Response headers set, returning", flush=True)
            return response
        except Exception as e:
            import traceback
            app.logger.error(f"PDF download error for user {user_id}: {str(e)}")
            app.logger.error(traceback.format_exc())
            return jsonify({"error": f"Failed to generate report: {str(e)}", "traceback": traceback.format_exc()}), 500

    # API: View own report (students can view their own reports)
    @app.route("/api/marking_hub/reports/view/my-report", methods=["GET"])
    @authed_only
    def view_my_report():
        try:
            from io import BytesIO
            from CTFd.models import Users
            from .utils.report_generator import get_student_submissions_for_report
            from CTFd.utils import get_config
            from flask import request
            
            current_user = get_current_user()
            if not current_user:
                return jsonify({"error": "Not authenticated"}), 401
            
            # Get optional category parameter
            category = request.args.get('category', None)
            
            user_id = current_user.id
            student = Users.query.get_or_404(user_id)
            submissions = get_student_submissions_for_report(user_id, category=category)
            
            if not submissions:
                category_msg = f" for {category}" if category else ""
                return jsonify({"error": f"No marked submissions available yet{category_msg}"}), 404
            
            ctf_name = get_config('ctf_name', 'CTF')
            subtitle = f"{category} Report" if category else "Full Performance Report"
            pdf_buffer = generate_student_report_pdf(
                student_name=student.name,
                student_email=student.email,
                submissions=submissions,
                ctf_name=ctf_name,
                subtitle=subtitle
            )
            
            filename = f"report_{student.name.replace(' ', '_')}_{category or 'full'}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
            
            # Read entire buffer and create response
            pdf_data = pdf_buffer.read()
            
            from flask import make_response
            response = make_response(pdf_data)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
            response.headers['Content-Length'] = str(len(pdf_data))
            return response
        except Exception as e:
            import traceback
            app.logger.error(f"Student report view error for user {current_user.id}: {str(e)}")
            app.logger.error(traceback.format_exc())
            return jsonify({"error": f"Failed to generate report: {str(e)}"}), 500

    # API: List available reports for current user
    @app.route("/api/marking_hub/reports/my-reports", methods=["GET"])
    @authed_only
    def list_my_reports():
        current_user = get_current_user()
        if not current_user:
            return jsonify({"error": "Not authenticated"}), 401
        
        reports = StudentReport.query.filter_by(user_id=current_user.id).order_by(StudentReport.sent_at.desc()).all()
        return jsonify([report.to_dict() for report in reports])

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
                

                # Use new many-to-many relationship
                assigned_user_ids = [student.id for student in user.students]
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
            include_tech = request.args.get("include_tech", "false").lower() in {"1", "true", "yes"}

            for sub in submissions:
                if not include_tech and _is_technical_challenge(sub.submission.challenge):
                    continue
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

    # API: Get tutor marking statistics
    @app.route("/api/marking_hub/statistics/tutors", methods=["GET"])
    @admins_only
    def get_tutor_statistics():
        from CTFd.models import Submissions, Challenges
        from sqlalchemy import func
        
        try:
            # Get all tutors
            tutors = MarkingTutor.query.all()
            
            stats = []
            for tutor in tutors:
                # Count submitted submissions assigned to this tutor
                marked_subs = (
                    MarkingSubmission.query
                    .filter_by(marked_by=tutor.user_id)
                    .all()
                )
                
                marked_count = len(marked_subs)
                # Calculate percentages: (mark / challenge.value) * 100
                percentages = []
                for s in marked_subs:
                    if s.mark is not None:
                        submission = Submissions.query.get(s.submission_id)
                        if submission and submission.challenge:
                            challenge_value = submission.challenge.value or 100
                            percentage = (s.mark / challenge_value) * 100
                            percentages.append(percentage)
                
                avg_mark = sum(percentages) / len(percentages) if percentages else 0
                
                # Calculate standard deviation
                std_dev = 0
                if len(percentages) > 1:
                    variance = sum((x - avg_mark) ** 2 for x in percentages) / len(percentages)
                    std_dev = round(variance ** 0.5, 1)
                
                # Get last marked date
                last_marked = None
                if marked_subs:
                    last_marked_sub = max(marked_subs, key=lambda x: x.marked_at or datetime.min)
                    if last_marked_sub.marked_at:
                        last_marked = last_marked_sub.marked_at.strftime("%Y-%m-%d %H:%M")
                
                stats.append({
                    "tutor_id": tutor.user_id,
                    "name": tutor.user.name if tutor.user else "Unknown",
                    "email": tutor.user.email if tutor.user else "",
                    "submissions_marked": marked_count,
                    "avg_mark": round(avg_mark, 1),
                    "std_dev": std_dev,
                    "last_marked": last_marked,
                })
            
            # Global stats
            all_marked = MarkingSubmission.query.filter(MarkingSubmission.mark.isnot(None)).all()
            all_subs = MarkingSubmission.query.all()
            
            # Count unique student/challenge pairs (not total submissions)
            from CTFd.models import Submissions
            all_submissions = Submissions.query.all()
            unique_solutions = set()
            for sub in all_submissions:
                # Create unique key for each student/challenge combo
                unique_solutions.add((sub.user_id, sub.challenge_id))
            
            # Count unique marked submissions (student/challenge pairs that have been marked)
            unique_marked = set()
            percentages_global = []
            for marking_sub in all_marked:
                submission = Submissions.query.get(marking_sub.submission_id)
                if submission:
                    unique_marked.add((submission.user_id, submission.challenge_id))
                    if marking_sub.mark is not None and submission.challenge:
                        challenge_value = submission.challenge.value or 100
                        percentage = (marking_sub.mark / challenge_value) * 100
                        percentages_global.append(percentage)
            
            avg_mark_overall = sum(percentages_global) / len(percentages_global) if percentages_global else 0
            
            global_stats = {
                "total_submitted": len(unique_solutions),
                "total_marked": len(unique_marked),
                "marking_percentage": round((len(unique_marked) / len(unique_solutions) * 100) if unique_solutions else 0, 1),
                "avg_mark_overall": round(avg_mark_overall, 1),
            }
            
            return jsonify({
                "success": True,
                "tutors": sorted(stats, key=lambda x: x["submissions_marked"], reverse=True),
                "global": global_stats,
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"Error fetching statistics: {str(e)}"
            }), 500

    # API: Get marking statistics by category
    @app.route("/api/marking_hub/statistics/categories", methods=["GET"])
    @admins_only
    def get_category_statistics():
        from CTFd.models import Submissions, Challenges
        
        try:
            # Get all challenges grouped by category
            challenges = Challenges.query.all()
            categories_dict = {}
            
            for challenge in challenges:
                cat = challenge.category or "Uncategorized"
                if cat not in categories_dict:
                    categories_dict[cat] = []
                categories_dict[cat].append(challenge.id)
            
            # For each category, count unique solutions and marked
            category_stats = []
            for category, challenge_ids in categories_dict.items():
                # Get all submissions for challenges in this category
                subs_in_cat = Submissions.query.filter(Submissions.challenge_id.in_(challenge_ids)).all()
                
                # Count unique student/challenge pairs
                unique_solutions = set()
                for sub in subs_in_cat:
                    unique_solutions.add((sub.user_id, sub.challenge_id))
                
                # Get marking submissions for solutions in this category
                marking_subs_in_cat = (
                    MarkingSubmission.query
                    .join(Submissions, MarkingSubmission.submission_id == Submissions.id)
                    .filter(Submissions.challenge_id.in_(challenge_ids))
                    .all()
                )
                
                # Count unique marked pairs and calculate percentages
                unique_marked = set()
                percentages = []
                for marking_sub in marking_subs_in_cat:
                    submission = Submissions.query.get(marking_sub.submission_id)
                    if submission:
                        unique_marked.add((submission.user_id, submission.challenge_id))
                    if marking_sub.mark is not None and submission and submission.challenge:
                        challenge_value = submission.challenge.value or 100
                        percentage = (marking_sub.mark / challenge_value) * 100
                        percentages.append(percentage)
                
                # Calculate stats for this category
                avg_mark = sum(percentages) / len(percentages) if percentages else 0
                
                category_stats.append({
                    "category": category,
                    "total_submitted": len(unique_solutions),
                    "total_marked": len(unique_marked),
                    "marking_percentage": round((len(unique_marked) / len(unique_solutions) * 100) if unique_solutions else 0, 1),
                    "avg_mark": round(avg_mark, 1),
                })
            
            return jsonify({
                "success": True,
                "categories": sorted(category_stats, key=lambda x: x["category"]),
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"Error fetching category statistics: {str(e)}"
            }), 500

    # API: Get marking statistics by exercise for a specific category
    @app.route("/api/marking_hub/statistics/category/<category>/exercises", methods=["GET"])
    @admins_only
    def get_exercise_statistics_by_category(category):
        from CTFd.models import Submissions, Challenges
        
        try:
            # Get all challenges in this category
            challenges = Challenges.query.filter_by(category=category).all()
            challenge_ids = [c.id for c in challenges]
            
            if not challenge_ids:
                return jsonify({
                    "success": True,
                    "category": category,
                    "exercises": [],
                })
            
            # Get all tutors for per-tutor stats
            tutors = MarkingTutor.query.all()
            
            exercise_stats = []
            for challenge in challenges:
                # Get submissions for this exercise
                subs = Submissions.query.filter_by(challenge_id=challenge.id).all()
                
                # Count unique students who submitted
                unique_students = set(sub.user_id for sub in subs)
                
                # Get marking submissions for this exercise
                marking_subs = (
                    MarkingSubmission.query
                    .join(Submissions, MarkingSubmission.submission_id == Submissions.id)
                    .filter(Submissions.challenge_id == challenge.id)
                    .all()
                )
                
                # Count unique marked students and calculate percentages
                unique_marked_students = set()
                percentages = []
                for marking_sub in marking_subs:
                    submission = Submissions.query.get(marking_sub.submission_id)
                    if submission:
                        unique_marked_students.add(submission.user_id)
                    if marking_sub.mark is not None:
                        challenge_value = challenge.value or 100
                        percentage = (marking_sub.mark / challenge_value) * 100
                        percentages.append(percentage)
                
                avg_mark = sum(percentages) / len(percentages) if percentages else 0
                
                # Per-tutor breakdown
                per_tutor_marks = []
                for tutor in tutors:
                    tutor_marking_subs = (
                        MarkingSubmission.query
                        .join(Submissions, MarkingSubmission.submission_id == Submissions.id)
                        .filter(Submissions.challenge_id == challenge.id)
                        .filter(MarkingSubmission.marked_by == tutor.user_id)
                        .all()
                    )
                    
                    tutor_percentages = []
                    for ms in tutor_marking_subs:
                        if ms.mark is not None:
                            challenge_value = challenge.value or 100
                            percentage = (ms.mark / challenge_value) * 100
                            tutor_percentages.append(percentage)
                    
                    tutor_avg_mark = sum(tutor_percentages) / len(tutor_percentages) if tutor_percentages else None
                    
                    if tutor_percentages:  # Only include tutors who marked this exercise
                        per_tutor_marks.append({
                            "tutor_id": tutor.user_id,
                            "tutor_name": tutor.user.name if tutor.user else "Unknown",
                            "marked_count": len(tutor_percentages),
                            "avg_mark": round(tutor_avg_mark, 1) if tutor_avg_mark else 0,
                        })
                
                exercise_stats.append({
                    "challenge_id": challenge.id,
                    "challenge_name": challenge.name,
                    "total_submitted": len(unique_students),
                    "total_marked": len(unique_marked_students),
                    "marking_percentage": round((len(unique_marked_students) / len(unique_students) * 100) if unique_students else 0, 1),
                    "avg_mark": round(avg_mark, 1),
                    "per_tutor": sorted(per_tutor_marks, key=lambda x: x["tutor_name"]),
                })
            
            return jsonify({
                "success": True,
                "category": category,
                "exercises": sorted(exercise_stats, key=lambda x: x["challenge_name"]),
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"Error fetching exercise statistics: {str(e)}"
            }), 500


