import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Load Gemini model
model = genai.GenerativeModel("gemini-1.5-flash")


def generate_competitor_analysis(startup_idea):
    prompt = f"""
You are an expert startup consultant.

Analyze the startup idea below.

Startup Idea:
{startup_idea}

Generate a competitor analysis in the following format:

1. Top 3 Competitors
2. Strengths of Each Competitor
3. Weaknesses of Each Competitor
4. Competitive Gap in the Market
5. Suggested Unique Selling Proposition (USP)
6. Recommendations for the Startup

Present the answer in a clear, structured format with headings and bullet points.
"""

    response = model.generate_content(prompt)

    return response.text