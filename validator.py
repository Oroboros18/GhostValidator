from flask import Flask, request, jsonify
import os
from openai import OpenAI
from dotenv import load_dotenv
import json
import re

load_dotenv()

app = Flask(__name__)

SUPPORTED_LANGUAGES = ["en", "fr", "es", "pt", "ar", "hi", "zh"]

LANGUAGE_NAMES = {
    "en": "English",
    "fr": "French",
    "es": "Spanish",
    "pt": "Portuguese",
    "ar": "Arabic",
    "hi": "Hindi",
    "zh": "Chinese"
}

CONTENT_TYPES = [
    "product_description",
    "blog_post",
    "seo_article",
    "landing_page",
    "social_post",
    "email",
    "general"
]

def get_client():
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def validate_content(text, language, content_type, target_audience, brand_rules=None):
    lang_name = LANGUAGE_NAMES.get(language, "English")
    brand_context = f"\nBrand rules to check: {brand_rules}" if brand_rules else ""

    prompt = f"""You are an expert AI content quality auditor specializing in SEO and publishing risk assessment.

Analyze the following {content_type} written in {lang_name} for a {target_audience} audience.{brand_context}

Text to analyze:
\"\"\"{text}\"\"\"

Return ONLY a valid JSON object with this exact structure:
{{
  "verdict": "VALID" or "WARNING" or "DANGER",
  "risk_score": integer from 0 to 100,
  "language_detected": "{language}",
  "content_type": "{content_type}",
  "word_count": integer,
  "issues": [
    {{
      "type": "issue_type",
      "severity": "low" or "medium" or "high",
      "description": "clear explanation"
    }}
  ],
  "fixes": ["fix 1", "fix 2"],
  "strengths": ["strength 1"],
  "seo_signals": {{
    "thin_content": true or false,
    "generic_ai_style": true or false,
    "missing_examples": true or false,
    "weak_eeat": true or false,
    "duplicate_structure": true or false,
    "good_readability": true or false
  }},
  "summary": "2-3 sentence assessment in {lang_name}"
}}

Verdict: VALID=0-30, WARNING=31-60, DANGER=61-100. Return ONLY JSON."""

    response = get_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
        temperature=0.2
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    return json.loads(raw)


@app.route('/validate', methods=['POST'])
def validate():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body provided"}), 400

    text = data.get("text", "").strip()
    language = data.get("language", "en").lower()
    content_type = data.get("content_type", "general")
    target_audience = data.get("target_audience", "general audience")
    brand_rules = data.get("brand_rules", None)

    if not text:
        return jsonify({"error": "text field is required"}), 400
    if len(text) < 10:
        return jsonify({"error": "text too short (minimum 10 characters)"}), 400
    if len(text) > 10000:
        return jsonify({"error": "text too long (maximum 10000 characters)"}), 400
    if language not in SUPPORTED_LANGUAGES:
        return jsonify({"error": f"Language '{language}' not supported", "supported_languages": SUPPORTED_LANGUAGES}), 400
    if content_type not in CONTENT_TYPES:
        content_type = "general"

    try:
        result = validate_content(text, language, content_type, target_audience, brand_rules)
        return jsonify(result), 200
    except json.JSONDecodeError:
        return jsonify({"error": "Failed to parse AI response. Please retry."}), 500
    except Exception as e:
        return jsonify({"error": f"Validation failed: {str(e)}"}), 500


@app.route('/languages', methods=['GET'])
def get_languages():
    return jsonify({"supported_languages": SUPPORTED_LANGUAGES, "language_names": LANGUAGE_NAMES})


@app.route('/content-types', methods=['GET'])
def get_content_types():
    return jsonify({"supported_content_types": CONTENT_TYPES})


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "Ghost-Validator", "version": "1.0.0"})


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
