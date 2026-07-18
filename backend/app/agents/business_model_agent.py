import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Load Gemini model
model = genai.GenerativeModel("gemini-1.5-flash")


def generate_business_model(startup_idea):
    prompt = f"""
You are a startup consultant.

Create a Business Model Canvas for the following startup idea.

Startup Idea:
{startup_idea}

Generate the following sections:

1. Value Proposition
2. Customer Segments
3. Revenue Streams
4. Key Activities
5. Key Resources
6. Key Partners
7. Channels
8. Customer Relationships
9. Cost Structure

Present the response with headings and bullet points.
"""

    response = model.generate_content(prompt)

    return response.text