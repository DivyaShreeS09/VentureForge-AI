import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Load Gemini model
model = genai.GenerativeModel("gemini-1.5-flash")


def generate_customer_persona(startup_idea):
    prompt = f"""
You are a startup consultant.

Based on the startup idea below, generate a customer persona.

Startup Idea:
{startup_idea}

Return the answer in this format:

Target Customer:
Age Group:
Occupation:
Income Level:
Pain Points:
Goals:
Preferred Platform:
Buying Behaviour:
"""

    response = model.generate_content(prompt)

    return response.text