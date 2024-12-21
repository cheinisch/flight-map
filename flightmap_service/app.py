from flask import Flask, jsonify, render_template, request
from adsb_fetcher import ADSBDataFetcher

app = Flask(__name__)
fetcher = ADSBDataFetcher("config.json")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/data")
def data():
    source = request.args.get("source", "all")
    return jsonify(fetcher.get_combined_data(source))

@app.route("/sources")
def sources():
    return jsonify(fetcher.get_sources())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=fetcher.config["port"])
