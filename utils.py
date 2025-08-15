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

def generate_project_idea(prompt, max_retries=3):
    '''Generate project idea using Groq API with error handling and retries'''
    if not os.getenv("GROQ_API_KEY"):
        logger.error("GROQ_API_KEY not found in environment variables")
        return "Error: GROQ_API_KEY not found in environment variables"
    
    # Sanitize the prompt
    sanitized_prompt = bleach.clean(prompt, tags=['p', 'strong', 'em'], strip=True)
    
    for attempt in range(max_retries):
        try:
            full_prompt = f"""{sanitized_prompt}
            Please provide a detailed coding project idea with the following structure:

            **Project Title:** [Creative and descriptive title]

            **Description:** 
            [Brief overview of what the project does and its purpose]

            **Programming Languages/Technologies:**
            [List the recommended languages and frameworks]

            **Key Features:**
            • [Feature 1]
            • [Feature 2]
            • [Feature 3]
            • [Additional features as needed]

            **Implementation Steps:**
            1. [Step 1]
            2. [Step 2]
            3. [Step 3]
            4. [Additional steps as needed]

            **Challenges & Learning Opportunities:**
            • [Challenge/Learning point 1]
            • [Challenge/Learning point 2]
            • [Challenge/Learning point 3]

            **Target Audience:**
            [Who would benefit from or use this project]

            **Difficulty Level:** [Beginner/Intermediate/Advanced]

            **Estimated Time:** [Time estimate for completion]

            Please make the response comprehensive but concise, suitable for a developer looking for their next project."""

            response = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[
                    {"role": "system", "content": "You are an experienced software developer and mentor who creates detailed, practical coding project ideas. Your suggestions should be creative, educational, and implementable."},
                    {"role": "user", "content": full_prompt},
                ],
                max_tokens=1000,
                temperature=0.7,
                top_p=0.9,
                stream=False
            )

            if response and response.choices:
                idea = response.choices[0].message.content.strip()
                if idea:
                    logger.info("Successfully generated project idea")
                    return idea
                else:
                    logger.warning("Empty response from Groq API")
                    return "Error: Empty response from AI"
            else:
                logger.error("Invalid response from Groq API")
                return "Error: Invalid response from AI"
    
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Attempt {attempt + 1} failed: {error_msg}")
            if "rate_limit" in error_msg.lower() or "429" in error_msg:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    time.sleep(wait_time)
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