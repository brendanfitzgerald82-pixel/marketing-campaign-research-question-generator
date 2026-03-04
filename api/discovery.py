"""
Discovery endpoint for the Research Question Generator (standalone deploy).
GET /api/discovery returns this tool only.
"""
import json
from http.server import BaseHTTPRequestHandler

TOOLS = [
    {
        "id": "generate_research_questions",
        "name": "Generate Research Questions",
        "description": "Takes a strategic brief (or summary) and returns a structured list of research questions grouped by the 4C's (Culture, Competition, Consumer, Company). Use at the start of the 4C's Research step to get a consistent set of questions to answer via web research or other tools.",
        "endpoint": "/api/tools/research_question_generator",
        "method": "POST",
        "parameters": {
            "brief": {
                "type": "string",
                "description": "Full strategic brief text (or key sections). Markdown or plain text.",
                "required": True,
            },
        },
    },
]


def _send_json(handler: BaseHTTPRequestHandler, data: dict, status: int = 200) -> None:
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(json.dumps(data).encode("utf-8"))


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        _send_json(
            self,
            {
                "version": "1.0",
                "name": "Research Question Generator",
                "description": "Generate 4C's research questions from a strategic brief.",
                "tools": TOOLS,
            },
        )

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()
