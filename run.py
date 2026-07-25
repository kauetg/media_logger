# run.py
from app import app
import webbrowser
from threading import Timer

def open_browser():
    webbrowser.open_new("http://localhost:5000")

if __name__ == "__main__":
    Timer(1, open_browser).start()
