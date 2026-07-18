import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Load Gemini model
model = genai.GenerativeModel("gemini-1.5-flash")


def generate_market_analysis(startup_idea):
    prompt = f"""
You are a startup market research expert.

Analyze the following startup idea:

Startup Idea:
{startup_idea}

Generate a detailed market analysis with the following sections:

1. Market Size
2. Target Audience
3. Current Market Trends
4. Opportunities
5. Challenges
6. Growth Potential
7. Suggested Pricing Strategy

Give the response in clear bullet points.
"""

    response = model.generate_content(prompt)

    return response.text