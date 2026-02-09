from flask import render_template

from CTFd.plugins import register_plugin_assets_directory

def load(app):

    # marking hub dashboard route (homepage)
    @app.route("/marking_hub", methods=["GET"])
    def marking_hub():
        return render_template("dashboard.html")
    
    # submission viewing route

    # mark table route

    # plugin assets route
    register_plugin_assets_directory(
        app,
        base_path="/plugins/CTFd_Marking_Hub/assets/",
        admins_only=True
    )
