"""
Research Question Generator — Vercel serverless function.
POST with a strategic brief; returns research questions grouped by 4C's (Culture, Competition, Consumer, Company).
Stateless, no external API keys required. Uses rule-based extraction + question templates.
"""
import json
import re
from http.server import BaseHTTPRequestHandler

# Default placeholders when brief doesn't contain a value
DEFAULTS = {
    "campaign": "this campaign",
    "target": "the target audience",
    "category": "this category",
    "timeframe": "the campaign period",
    "competitors": "competitors",
    "challenge": "the desired behavior change",
}


def _extract(brief: str) -> dict:
    """Extract key fields from strategic brief text for filling question templates."""
    text = brief.strip()
    out = {k: None for k in DEFAULTS}
    out["open_questions"] = []

    # Campaign / initiative name
    m = re.search(r"(?:Campaign Name|Initiative Name|Campaign/Initiative)\s*[:\*]+\s*([^\n#]+)", text, re.I)
    if m:
        out["campaign"] = m.group(1).strip().strip("_")
    if not out["campaign"]:
        m = re.search(r"#\s*Marketing Strategy Brief[:\s]+([^\n#]+)", text, re.I)
        if m:
            out["campaign"] = m.group(1).strip()

    # Primary target (segment name + descriptor)
    m = re.search(r"Primary Target\s*\n\s*\*\*[\"\']?([^\"\*\n]+)[\"\']?\s*[-—]", text, re.I | re.M)
    if m:
        out["target"] = m.group(1).strip()
    if not out["target"]:
        m = re.search(r"Target (?:Audience|Segment)[:\s]+\*\*([^\*\n]+)\*\*", text, re.I)
        if m:
            out["target"] = m.group(1).strip()
    if not out["target"]:
        m = re.search(r"(?:Primary Target|Target Audience)\s*\n([^\n#]+)", text, re.I | re.M)
        if m:
            out["target"] = m.group(1).strip()[:80]

    # Category / product (one line, strip bullets)
    m = re.search(r"What We're Marketing\s*\n([^\n#]+)", text, re.I | re.M)
    if m:
        out["category"] = re.sub(r"^\s*[-*]\s*", "", m.group(1).strip())[:100]
    if not out["category"]:
        m = re.search(r"Product/Service Overview\s*\n(?:###?\s*\n)?([^\n#]+)", text, re.I | re.M)
        if m:
            out["category"] = re.sub(r"^\s*[-*]\s*", "", m.group(1).strip())[:100]

    # Timeframe (first line only, strip list bullets and markdown)
    m = re.search(r"Timeframe\s*\n([^\n#]+)", text, re.I | re.M)
    if m:
        raw = m.group(1).strip()
        raw = re.sub(r"^\s*[-*]\s*", "", raw)
        raw = re.sub(r"\*\*[^*]*\*\*:?\s*", "", raw)  # remove **bold**: 
        out["timeframe"] = raw[:80].strip()
    if not out["timeframe"]:
        m = re.search(r"(?:August|September|October|November|Q[1-4]|202[4-9]|launch)", text, re.I)
        if m:
            out["timeframe"] = "campaign launch period"

    # Competitors (first bullet line after Direct Competitors; allow - or * or unicode dash)
    m = re.search(r"Direct Competitors\s*\n\s*[-*\u2013\u2014]\s*([^\n#]+)", text, re.I | re.M)
    if m:
        raw = m.group(1).strip()
        out["competitors"] = raw[:120].strip()

    # Strategic challenge / desired behavior
    m = re.search(r"Desired Behavior Change\s*\n([^\n#]+)", text, re.I | re.M)
    if m:
        out["challenge"] = m.group(1).strip()[:150]
    if not out["challenge"]:
        m = re.search(r"The Problem to Solve\s*\n([^\n#]+)", text, re.I | re.M)
        if m:
            out["challenge"] = m.group(1).strip()[:150]

    # Open questions (bulleted list under Open Questions / Research Needs)
    open_section = re.search(
        r"Open Questions[^\n]*\n([\s\S]*?)(?=\n##|\n#\s*\d|$)",
        text,
        re.I,
    )
    if open_section:
        block = open_section.group(1)
        for line in re.findall(r"^\s*[-*]\s+(.+)", block, re.M):
            q = line.strip()
            if len(q) > 15 and "?" not in q:
                q = q + "?"
            if q:
                out["open_questions"].append(q)

    for k, v in DEFAULTS.items():
        if k == "open_questions":
            continue
        if out.get(k) is None or (isinstance(out[k], str) and not out[k].strip()):
            out[k] = v
    return out


def _templates() -> dict:
    """Return question templates per 4C. Use {campaign}, {target}, {category}, {timeframe}, {competitors}, {challenge}."""
    return {
        "culture": [
            "What cultural or societal trends are relevant to {category} and {target}?",
            "What is happening in media or public discourse that could impact {campaign}?",
            "What economic or political factors might influence {target} attitudes or behavior during {timeframe}?",
            "What seasonal or timing factors around {timeframe} could affect launch or messaging?",
            "What cultural moments or events during {timeframe} could we leverage or need to account for?",
        ],
        "competition": [
            "Who are the main {competitors} and what are they doing for similar campaigns?",
            "What messaging and creative approaches are {competitors} using?",
            "What is the competitive landscape in terms of share, positioning, and white space?",
            "Where are {competitors} not playing that we could own?",
            "What competitive threats or opportunities should inform our positioning?",
        ],
        "consumer": [
            "What are the current behaviors of {target} related to {category}?",
            "What are the attitudes and perceptions of {target} toward {category} and our brand?",
            "What are the top needs and motivations that drive {target} in this space?",
            "What are the main barriers and concerns preventing {target} from taking action?",
            "How does {target} make decisions—what sources, factors, and triggers matter?",
            "What are the media consumption habits and trusted sources of {target}?",
            "Are there meaningful segment differences within {target} we should address?",
        ],
        "company": [
            "How is our brand currently positioned in the market versus {competitors}?",
            "What are our unique strengths and assets we can leverage for {campaign}?",
            "What limitations or constraints do we need to work within?",
            "What have we learned from past campaigns—what worked and what did not?",
            "What is our brand equity and trust level with {target}?",
            "Are we operationally ready to deliver on what we promise for {campaign}?",
        ],
    }


def generate_questions(brief: str) -> dict:
    """
    Generate research questions from a strategic brief.
    Returns dict with campaign_name, extracted (optional), questions { culture, competition, consumer, company }, markdown.
    """
    extracted = _extract(brief)
    templates = _templates()
    questions = {}
    campaign_name = extracted.get("campaign") or DEFAULTS["campaign"]

    for c, qlist in templates.items():
        filled = []
        for t in qlist:
            try:
                q = t.format(
                    campaign=extracted.get("campaign") or DEFAULTS["campaign"],
                    target=extracted.get("target") or DEFAULTS["target"],
                    category=extracted.get("category") or DEFAULTS["category"],
                    timeframe=extracted.get("timeframe") or DEFAULTS["timeframe"],
                    competitors=extracted.get("competitors") or DEFAULTS["competitors"],
                    challenge=extracted.get("challenge") or DEFAULTS["challenge"],
                )
            except KeyError:
                q = t
            filled.append(q)
        questions[c] = filled

    # Append any explicit open questions into the appropriate C (spread across consumer/company/culture/competition)
    open_q = extracted.get("open_questions") or []
    if open_q:
        n = len(open_q)
        keys = ["consumer", "company", "culture", "competition"]
        for i, oq in enumerate(open_q):
            questions[keys[i % 4]].append(oq)

    # Build markdown
    md_lines = ["## Derived Research Questions", ""]
    labels = [
        ("culture", "CULTURE"),
        ("competition", "COMPETITION"),
        ("consumer", "CONSUMER"),
        ("company", "COMPANY"),
    ]
    for key, label in labels:
        md_lines.append(f"### {label}")
        for q in questions[key]:
            md_lines.append(f"- {q}")
        md_lines.append("")

    return {
        "campaign_name": campaign_name,
        "extracted": {
            "campaign": extracted.get("campaign"),
            "target": extracted.get("target"),
            "category": extracted.get("category"),
            "timeframe": extracted.get("timeframe"),
            "competitors": extracted.get("competitors"),
            "challenge": extracted.get("challenge"),
        },
        "questions": questions,
        "markdown": "\n".join(md_lines).strip(),
    }


def _send_json(handler: BaseHTTPRequestHandler, data: dict, status: int = 200) -> None:
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length else b"{}"
            data = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, ValueError) as e:
            _send_json(
                self,
                {"error": "Invalid JSON body", "detail": str(e)},
                status=400,
            )
            return

        brief = data.get("brief") or data.get("brief_text") or ""
        if not brief or not isinstance(brief, str):
            _send_json(
                self,
                {"error": "Missing or invalid 'brief'", "detail": "Body must include a string 'brief' or 'brief_text'."},
                status=400,
            )
            return

        try:
            result = generate_questions(brief)
            _send_json(self, result)
        except Exception as e:
            _send_json(
                self,
                {"error": "Generation failed", "detail": str(e)},
                status=500,
            )

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()
