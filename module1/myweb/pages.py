from flask import Blueprint, render_template

# Creates a Blueprint named "pages" to group related routes for the website.
bp = Blueprint("pages", __name__)

# Renders and returns the homepage template.
@bp.route("/")
def home():
    return render_template("pages/home.html")

# Renders and returns the contact template.
@bp.route("/contact")
def contact():
    return render_template("pages/contact.html")

# Renders and returns the projects template.
@bp.route("/projects")
def projects():
    return render_template("pages/projects.html")

