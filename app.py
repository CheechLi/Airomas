from flask import Flask, render_template, request
import os
import requests
import json
import re

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY is not set! Make sure it's added in Vercel Environment Variables.")

app = Flask(__name__)

def build_scent_prompt_gemini(
    age, gender, occupation, mood, activities, style, season, scent_type, max_price
):
    max_price_text = f"Only suggest fragrances priced below ${max_price}." if max_price else ""
    
    # Use only the brand names in the prompt
    brand_list_text = ", ".join(BRANDS.keys())
    
    prompt = f"""
You are a fragrance expert. Based on the following user traits:
- Age: {age}
- Gender: {gender}
- Occupation: {occupation}
- Mood: {mood}
- Activities: {activities}
- Style: {style}
- Season: {season}
- Type: {scent_type}

{max_price_text}

Suggest 3 real perfumes or colognes that fit this user. For each suggestion provide:
- name
- brand
- reason (1-2 sentences)
- Construct the official product URL using the brand's official website domain
- retail price in USD for common bottle sizes: 30ml, 50ml, 100ml
- top, middle, and base notes as lists

Respond ONLY in valid JSON, no extra text. Format:

{{
  "scents": [
    {{
      "name": "...",
      "brand": "...",
      "reason": "...",
      "official_product": "https://www.brand.com/product-name/",
      "price_usd": {{
        "30ml": "$XX",
        "50ml": "$XX",
        "100ml": "$XX"
      }},
      "notes": {{
        "top": ["..."],
        "middle": ["..."],
        "base": ["..."]
      }}
    }},
    ... (total 3 scents)
  ]
}}
"""
    return prompt

def call_gemini(prompt):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "google/gemini-2.5-flash",
        "messages": [{"role": "user", "content": prompt}],
        "modalities": ["text"],
    }

    try:
        resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
        result = resp.json()

        if not result.get("choices"):
            return None, "No choices returned from AI"

        content = result["choices"][0]["message"].get("content", "")

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                return None, "AI returned invalid JSON"

        return data, None

    except Exception as e:
        return None, str(e)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/discover", methods=["GET", "POST"])
def find_fragrance():
    if request.method == "POST":
        # Handle form submission
        age = request.form.get("age")
        gender = request.form.get("gender")
        occupation = request.form.get("occupation")
        mood = request.form.get("mood")
        activities = request.form.get("activities")
        style = request.form.get("style")
        season = request.form.get("season")
        scent_type = request.form.get("type")
        max_price = request.form.get("max_price")

        prompt = build_scent_prompt_gemini(
            age,
            gender,
            occupation,
            mood,
            activities,
            style,
            season,
            scent_type,
            max_price,
        )

        data, error = call_gemini(prompt)
        if error:
            return f"<p>Error: {error}</p><pre>Prompt:\n{prompt}</pre>"

        scents = data.get("scents", [])
        return render_template("discover.html", scents=scents)

    return render_template("discover.html")


@app.route("/chat")
def chat():
    return render_template("chat.html")


@app.route("/chat_api", methods=["POST"])
def chat_api():
    user_message = request.form.get("message")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "google/gemini-2.5-flash",
        "messages": [
            {"role": "system", "content": "You are a helpful chatbot."},
            {"role": "user", "content": user_message},
        ],
    }

    resp = requests.post(OPENROUTER_URL, headers=headers, json=payload)
    result = resp.json()

    bot = result["choices"][0]["message"]["content"]

    return {"reply": bot}