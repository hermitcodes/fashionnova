"""Test the stable Gemini model"""
from google import genai

API_KEY = "AIzaSyD4GIP_1Pr663R9DE8oksTUqj4GOeXRo48"

def test_stable_model():
    try:
        client = genai.Client(api_key=API_KEY)
        
        # Test with stable model
        response = client.models.generate_content(
            model="gemini-2.0-flash-001",  # Stable model
            contents="Say 'Hello FashionNova! I am working!'"
        )
        
        print("✅ Stable model is working!")
        print(f"Response: {response.text}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_stable_model()