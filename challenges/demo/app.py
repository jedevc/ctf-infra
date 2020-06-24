import flask
from flask import Flask

app = Flask(__name__)


@app.route("/")
def index():
    return "There's nothing here..."


@app.route("/flag")
def flag():
    with open("flag.txt") as f:
        return f.read()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
