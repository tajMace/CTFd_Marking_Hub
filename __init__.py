from flask import render_template

def load(app):

    # marking hub dashboard route (homepage)
    @app.route("/marking_hub", methods=["GET"])
    def marking_hub():
        return render_template("dashboard.html")
    
    # submission viewing route

    # mark table route
    