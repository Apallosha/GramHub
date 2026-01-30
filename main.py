from flask import Flask
import threading
from bot import run_bot

app = Flask(__name__)

@app.route("/")
def home():
    return "OK", 200

def web():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=web).start()
run_bot()
