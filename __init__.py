import os
from flask import render_template, send_from_directory

from CTFd.plugins import register_plugin_assets_directory

def load(app):

    # Custom asset route
    dir_path = os.path.dirname(os.path.realpath(__file__))
    assets_path = os.path.join(dir_path, "assets", "dist")
    
    @app.route("/marking_hub_assets/<path:filename>")
    def marking_hub_assets(filename):
        return send_from_directory(assets_path, filename)
    
    # marking hub dashboard route
    @app.route("/marking_hub", methods=["GET"])
    def marking_hub():
        return render_template("plugins/CTFd_Marking_Hub/templates/marking_dashboard.html")
