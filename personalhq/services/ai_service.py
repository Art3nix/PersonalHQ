"""Global service for handling interactions with Large Language Models."""

import os
import json
from google import genai
from google.genai import types

def generate_json(system_prompt, model_name='gemini-2.5-flash'):
    """
    Sends a prompt to the AI model and strictly returns the parsed JSON response.
    
    Args:
        system_prompt (str): The complete instructions and JSON schema constraint.
        model_name (str): The Gemini model to use. Defaults to 2.5 Flash.
        
    Returns:
        dict | list: The parsed JSON response from the AI.
        
    Raises:
        ValueError: If the API key is missing.
        Exception: If the AI call or JSON parsing fails.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("CRITICAL: GEMINI_API_KEY is missing from .env")
        raise ValueError("AI configuration missing.")
        
    client = genai.Client(api_key=api_key)
    
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=system_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        
        # Parse and return the JSON directly so the routes don't have to deal with string conversion
        return json.loads(response.text)
        
    except Exception as e:
        print(f"AI Service Execution Error: {e}")
        raise e