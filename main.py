"""Post api"""
from flask import Flask

app = Flask(__name__)

@app.route("/")
def health_check():
    """server health check
    Returns:
        _type_: json
    """
    return {'message': 'ok'}
