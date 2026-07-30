import sys
import os

# Make the project root importable (db.py, config.py, etc.) whether this
# is run directly (`python webapp/app.py`) or via flask run.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, abort
import db

app = Flask(__name__)


@app.route("/")
def dashboard():
    return render_template("dashboard.html", stats=db.stats())


@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    results = db.search_fts(q) if q else []
    return render_template("search.html", query=q, results=results)


@app.route("/document/<int:doc_id>")
def document(doc_id):
    doc = db.get_document(doc_id)
    if not doc:
        abort(404)
    entities = db.entities_for_document(doc_id)
    related = db.related_by_entities(doc_id)
    return render_template("document.html", doc=doc, entities=entities, related=related)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
