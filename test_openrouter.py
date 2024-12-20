import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from a .env file (if you're using dotenv)
load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

completion = client.chat.completions.create(
    model="google/gemini-2.0-flash-exp:free",
    messages=[
        {
            "role": "user",
            "content": "Test connection"
        }
    ]
)

print(completion.choices[0].message.content)