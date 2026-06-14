"""Quick connectivity test for AI Search and DeepSeek API."""
import os
from dotenv import load_dotenv
load_dotenv()

# ─── Test AI Search ──────────────────────────────
print("=" * 50)
print("Testing Azure AI Search (Foundry IQ)...")
print("=" * 50)

from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

endpoint = os.getenv("AI_SEARCH_ENDPOINT")
key = os.getenv("AI_SEARCH_KEY")
index = os.getenv("AI_SEARCH_INDEX", "foundry-iq-index")

print(f"  Endpoint: {endpoint}")
print(f"  Index: {index}")
print(f"  Key length: {len(key)} chars")

try:
    client = SearchClient(
        endpoint=endpoint,
        index_name=index,
        credential=AzureKeyCredential(key),
    )
    results = client.search(search_text="*", top=1)
    count = sum(1 for _ in results)
    print(f"  ✅ Connected. Documents in index: {count}")
except Exception as e:
    print(f"  ❌ Connection failed: {e}")

# ─── Test DeepSeek API ───────────────────────────
print()
print("=" * 50)
print("Testing DeepSeek API...")
print("=" * 50)

from openai import OpenAI

api_key = os.getenv("DEEPSEEK_API_KEY")
base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

print(f"  Base URL: {base_url}")
print(f"  Model: {model}")
print(f"  Key length: {len(api_key)} chars")

try:
    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Reply OK only"}],
        max_tokens=10,
    )
    msg = response.choices[0].message.content
    print(f"  ✅ Connected. Response: {msg}")
except Exception as e:
    print(f"  ❌ Connection failed: {e}")
