import os
from flask import Flask, request, Response, render_template, stream_with_context
from agent import run_agent

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/run", methods=["POST"])
def run():
    goal = request.form.get("goal", "")

    if not goal:
        return "No goal provided", 400

    def generate():
        for update in run_agent(goal):
            # The old code sent the entire update as one event
            # If the update had multiple lines, the browser ignored everything
            # after the first line because they did not start with "data:"
            #
            # The fix — split every update into individual lines
            # Send each line as its own separate event
            # Now every single line reaches the browser correctly
            lines = update.split("\n")
            for line in lines:
                yield f"data: {line}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)