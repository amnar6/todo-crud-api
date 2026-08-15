import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Find root directory .env file
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

base_url = os.getenv("LLM_BASE_URL")
api_key = os.getenv("LLM_API_KEY")
model = os.getenv("LLM_MODEL")

if not api_key:
    raise ValueError(f"LLM_API_KEY is empty or missing! Checked env path: {env_path}")

client = OpenAI(
    base_url=base_url,
    api_key=api_key
)

def verify_provider():
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "Reply with exactly the word: ready"}
            ],
            temperature=0.0
        )
        content = response.choices[0].message.content
        print(f"Provider Response: {content}")
        return content
    except Exception as e:
        print(f"Provider Verification Failed: {e}")
        raise e

if __name__ == "__main__":
    verify_provider()