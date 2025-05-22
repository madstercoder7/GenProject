import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_project_idea(prompt):
    try:
        full_prompt = (
            f"""{prompt}\n\n
            Provide a detailed coding project idea that includes:\n
            - A brief decription of the project\n
            - The programming language(s) to use\n
            - Key features or functionalities\n
            - Potential challenges\n
            - Target audience or use case\n
            Format the response clearly with headings like 'Description', 'Languages', 'Features', 'Challenges', and 'Target audience'. 
            """
        )

        reponse = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": "You are a creative assistant that generates coding project ideas."},
                {"role": "user", "content": full_prompt},
            ],
            max_tokens=1000,
            temperature=0.7
        )

        idea = reponse.choices[0].message.content.strip()
        return idea

    except Exception as e:
        return f"Error generating project idea: {str(e)}"