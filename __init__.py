import os
from flask import render_template, send_from_directory, jsonify, request
from CTFd.models import db
from CTFd.utils.decorators import admins_only
from CTFd.plugins import bypass_csrf_protection
from .models import MarkingSubmission
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
    
    # API: Get all marking submissions
    @app.route("/api/marking_hub/submissions", methods=["GET"])
    @admins_only
    def get_marking_submissions():
        submissions = MarkingSubmission.query.all()
        return jsonify([sub.to_dict() for sub in submissions])
    
    # API: Get single submission
    @app.route("/api/marking_hub/submissions/<int:submission_id>", methods=["GET"])
    @admins_only
    def get_marking_submission(submission_id):
        submission = MarkingSubmission.query.get_or_404(submission_id)
        return jsonify(submission.to_dict())
    
    # API: Save mark and comment
    @app.route("/api/marking_hub/submissions/<int:submission_id>", methods=["PUT"])
    @admins_only
    @bypass_csrf_protection
    def update_marking_submission(submission_id):
        from CTFd.utils.user import get_current_user
        
        submission = MarkingSubmission.query.get_or_404(submission_id)
        data = request.get_json()
        
        submission.mark = data.get('mark')
        submission.comment = data.get('comment')
        submission.marked_at = datetime.utcnow()
        submission.marked_by = get_current_user().id
        
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
