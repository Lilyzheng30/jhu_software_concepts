from myweb import create_app

app = create_app()

# Ensures the web server only starts when this file is run directly.
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)