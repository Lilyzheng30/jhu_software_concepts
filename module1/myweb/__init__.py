from flask import Flask
from .pages import bp

# Creates and configures the Flask application.
def create_app():
    app = Flask(__name__)
    app.register_blueprint(bp)
    return app