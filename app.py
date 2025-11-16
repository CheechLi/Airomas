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
    max_price_text = (
        f"Only suggest fragrances priced below ${max_price}." if max_price else ""
    )
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

Suggest 3 real perfumes or colognes that fit this user.

For each suggestion provide:
- name
- brand
- reason (1-2 sentences)
- Construct the official product URL by using the brand's official website domain. If unsure, give the most likely official homepage URL for that brand.
- retail price in USD for common bottle sizes: 30ml, 50ml, 100ml (if no prices, use N/A)
- top, middle, and base notes as lists

designer_brands = {
    "Tom Ford": "https://www.tomford.com/beauty/fragrance/",
    "Chanel": "https://www.chanel.com/us/fragrance/",
    "Dior": "https://www.dior.com/en_us/beauty/womens-fragrance",
    "Yves Saint Laurent": "https://www.yslbeauty.com/int/fragrances.html",
    "Armani": "https://www.armani.com/beauty/fragrance",
    "Gucci": "https://www.gucci.com/us/en/ca/beauty/fragrance-c-beauty",
    "Hermès": "https://www.hermes.com/us/en/category/beauty/fragrances/",
    "Prada": "https://www.prada.com/us/en/beauty/fragrance.html",
    "Valentino": "https://www.valentino.com/en-us/beauty/fragrance.html",
    "Versace": "https://www.versace.com/us/en-us/women/versace-collection/fragrances/",
    "Hugo Boss": "https://www.hugoboss.com/us/boss-bottled",
    "Bvlgari": "https://www.bulgari.com/en-us/beauty/fragrances",
    "Burberry": "https://www.burberry.com/us/fragrance/",
    "Givenchy": "https://www.givenchy.com/us/fragrance",
    "Calvin Klein": "https://www.calvinklein.us/en/fragrances",
    "Kenzo": "https://www.kenzo.com/fragrance",
    "Marc Jacobs": "https://www.marcjacobs.com/fragrance/",
    "Coach": "https://www.coach.com/beauty/fragrance",
    "Lancome": "https://www.lancome-usa.com/fragrance",
    "Estée Lauder": "https://www.esteelauder.com/fragrance",
    "Viktor & Rolf": "https://www.viktor-rolf.com/fragrance",
    "Jean Paul Gaultier": "https://www.jeanpaulgaultier.com/fragrance",
    "Dolce & Gabbana": "https://www.dolcegabbana.com/en/beauty/fragrance/",
    "Miu Miu": "https://www.miumiu.com/us/en/beauty/fragrance.html",
    "Valentino Beauty": "https://www.valentino.com/en-us/beauty/fragrance.html",
    "Maison Margiela": "https://www.maisonmargiela-fragrances.us/",
    "Tommy Hilfiger": "https://usa.tommy.com/fragrance",
    "Ralph Lauren": "https://www.ralphlauren.com/fragrance",
    "Issey Miyake": "https://www.isseymiyakeparfums.com/",
    "Montblanc": "https://www.montblanc.com/en-us/fragrance",
    "Elie Saab": "https://www.eliesaabfragrance.com/",
    "Jo Malone": "https://www.jomalone.com/",
    "Creed": "https://www.creedboutique.com/",
    "Maison Francis Kurkdjian": "https://www.franciskurkdjian.com/",
    "Byredo": "https://www.byredo.com/",
    "Diptyque": "https://www.diptyqueparis.com/en_us/",
    "Acqua di Parma": "https://www.acquadiparma.com/us_en/",
    "Penhaligon's": "https://www.penhaligons.com/us/",
    "Giorgio Armani": "https://www.armani.com/beauty/fragrance",
    "Bottega Veneta": "https://www.bottegaveneta.com/beauty/fragrance",
    "Fendi": "https://www.fendi.com/us/beauty/fragrance",
    "Celine": "https://www.celine.com/en-us/beauty/fragrance",
    "Hermione": "https://www.hermioneparfum.com/",  # niche/lesser-known
    "Cartier": "https://www.cartier.com/en-us/collections/jewelry-and-watches/fragrance.html",
    "Chloé": "https://www.chloe.com/us/fragrance",
    "Balenciaga": "https://www.balenciaga.com/us/beauty/fragrance",
    "Coach Fragrance": "https://www.coach.com/beauty/fragrance",
    "Givenchy Beauty": "https://www.givenchybeauty.com/fragrance",
    "Tommy Girl": "https://usa.tommy.com/fragrance",
    "Prada Beauty": "https://www.prada.com/us/en/beauty/fragrance.html",
    "Dolce&Gabbana Beauty": "https://www.dolcegabbana.com/en/beauty/fragrance/",
    "Gucci Beauty": "https://www.gucci.com/us/en/ca/beauty/fragrance-c-beauty",
}

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