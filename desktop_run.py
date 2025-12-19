# File: IT12 Law_Office/desktop_run.py
import os
import sys
import webbrowser
from threading import Timer
from app import create_app # Imports from your app folder

# Create the app instance
app = create_app()

def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000")

if __name__ == '__main__':
    # Determine the path for the database so it sits NEXT to the .exe, not inside it
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))

    # Force the database path to be external
    # Note: Ensure your config uses this, or set it directly here:
    db_path = os.path.join(application_path, 'rbj_law.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"

    Timer(1.5, open_browser).start()
    app.run(host='127.0.0.1', port=5000, debug=False)