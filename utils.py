import os
import time
import logging
from groq import Groq
from dotenv import load_dotenv
from flask import session, flash, redirect, url_for, jsonify
from functools import wraps
import bleach

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_project_idea(messages, max_retries=3):
    '''Generate project idea using Groq API with error handling and retries'''
    if not os.getenv("GROQ_API_KEY"):
        logger.error("GROQ_API_KEY not found in environment variables")
        return "Error: GROQ_API_KEY not found in environment variables"
    
    if len(messages) == 1 and messages[0]["role"] == "user":
        system_prompt = {
            "role": "system",
            "content": (
                "You are an experienced software developer and mentor. Provide creative, practical,"
                "and detailed coding project ideas in response to user suggestions. "
                "Respond with the following structure for new ideas:"
                "Project Title, Description, Tech Stack, Key Features, Implementation Steps, Learning Challenges"
                ", Target Audience, Difficulty and estimated time."
                "For follow-up questions, give direct and useful advice"
            )
        }
        messages = [system_prompt] + messages

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=messages,
                max_tokens=1000,
                temperature=0.7,
                top_p=0.9,
                stream=False
            )

            if response and response.choices:
                idea = response.choices[0].message.content.strip()
                if idea:
                    logger.info("Successfully generated project idea/response")
                    return idea
                else:
                    logger.warning("Empty response from Groq API")
                    return "Error: Empty response from AI"
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Attempt {attempt + 1} failed: {error_msg}")
            if "rate_limit" in error_msg.lower() or "429" in error_msg:
                if attempt < max_retries - 1:
                    time.sleep((attempt + 1) * 2)
                    continue
                return "Error: Rate limit exceeded. Please try later."
            elif "api_key" in error_msg.lower() or "401" in error_msg:
                return "Error: Invalid API key. Please check Groq API configuration."
            elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return "Error: Network connection issue. Please check your internet."
            elif attempt == max_retries - 1:
                return f"Error: Failed to generate project idea after {max_retries} attempts."
            else:
                time.sleep(1)
    
    return "Error: Unable to generate idea."

def login_required(f):
    '''Decorator to require login for routes'''
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

def validate_input(data, required_fields):
    '''Validate form input'''
    errors = []
    for field in required_fields:
        if not data.get(field) or not data.get(field).strip():
            errors.append(f"{field.replace('_', ' ').title()} is required")
    return errors