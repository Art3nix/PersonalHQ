"""Global service for handling interactions with Large Language Models."""

import os
import json
import time
import random
from google import genai
from google.genai import types
from google.genai.errors import APIError

# The Routing Chain: Try the fastest/smartest first, then fall back to stable older models.
FALLBACK_MODELS = [
    'gemini-2.5-flash', # Primary: Fast, but prone to high-demand spikes
    'gemini-1.5-flash', # Backup 1: Older, highly stable, huge capacity
    'gemini-2.5-pro'    # Backup 2: Slower and more expensive, but different compute cluster
]

def generate_json(system_prompt, models=FALLBACK_MODELS, max_retries_per_model=3):
    """
    Sends a prompt to the AI model and strictly returns the parsed JSON response.
    Includes Exponential Backoff with Jitter and Automatic Multi-Model Fallback.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("CRITICAL: GEMINI_API_KEY is missing from .env")
        raise ValueError("AI configuration missing.")
        
    client = genai.Client(api_key=api_key)
    
    # 1. Loop through the Fallback Chain
    for model_name in models:
        print(f"Attempting AI Generation with model: {model_name}")
        
        # 2. The Retry Loop for the current model
        for attempt in range(max_retries_per_model):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=system_prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                    )
                )
                
                # If successful, parse and return immediately
                return json.loads(response.text)
                
            except APIError as e:
                # Check for 503 (High Demand) or 429 (Rate Limit)
                if e.code in [503, 429] and attempt < max_retries_per_model - 1:
                    
                    # Exponential Backoff (2s, 4s, 8s) + Random Jitter (0.0 to 1.0s)
                    sleep_time = (2 ** (attempt + 1)) + random.uniform(0, 1)
                    print(f"{model_name} API Error ({e.code}). Retrying in {sleep_time:.2f}s (Attempt {attempt + 1}/{max_retries_per_model})...")
                    
                    time.sleep(sleep_time)
                    continue # Try this specific model again
                else:
                    # We ran out of retries, or hit a fatal error (like 400 Bad Request).
                    # Break out of the retry loop so Python can fall back to the NEXT model.
                    print(f"{model_name} failed completely: {e}")
                    break 
                    
            except Exception as e:
                # Catches JSON parsing errors if the AI hallucinates the format
                print(f"{model_name} JSON format error: {e}")
                break 

    # 3. The Fatal Catch
    # If the code escapes both loops, EVERY model in the fallback chain has failed.
    print("FATAL: All fallback models failed.")
    raise Exception("The AI service is experiencing global outages. Please try again later.")
    
def generate_daily_context(user, logical_date_to_prep):
    ...