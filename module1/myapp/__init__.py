from flask import Flask 

from jhu_software_concepts.module1.myapp import pages

def create_app():
    app = Flask(__name__)
    app.register_blueprint(pages.bp)
    return app
