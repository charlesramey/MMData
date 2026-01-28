from flask import Flask, send_from_directory
import os

# Set the static folder to 'web_app' so files like style.css and main.js are served correctly
# The static_url_path='' ensures they are served from the root URL (e.g. /style.css)
app = Flask(__name__, static_url_path='', static_folder='web_app')

@app.route('/')
def index():
    # Serve the index.html file when the root URL is accessed
    return send_from_directory('web_app', 'index.html')

if __name__ == '__main__':
    # This block is for running locally for testing purposes
    app.run(debug=True, port=8000)
