"""
AI Fashion Stylist Module for FashionNova
Uses Google Gen AI SDK with stable Gemini models
"""

from django.conf import settings
from PIL import Image
import io
import logging
import re
import time

# Import the new SDK
try:
    from google import genai
    from google.genai import types
    NEW_SDK_AVAILABLE = True
except ImportError:
    NEW_SDK_AVAILABLE = False

logger = logging.getLogger(__name__)

if NEW_SDK_AVAILABLE:
    logger.info("Google Gen AI SDK loaded successfully")
else:
    logger.warning("Google Gen AI SDK not found. Install with: pip install google-genai")

class AIFashionStylist:
    """AI-powered fashion stylist using Google Gen AI SDK"""
    
    def __init__(self):
        """Initialize Gemini API with stable model"""
        self.api_configured = False
        
        if not NEW_SDK_AVAILABLE:
            logger.warning("New SDK not available. Install with: pip install google-genai")
            return
        
        try:
            # Get API key from settings
            api_key = getattr(settings, 'GEMINI_API_KEY', None)
            
            if not api_key:
                logger.warning("GEMINI_API_KEY not found in settings")
                return
            
            # Initialize client with new SDK
            self.client = genai.Client(api_key=api_key)
            
            # USE STABLE MODEL - NOT experimental
            self.model_name = getattr(settings, 'GEMINI_MODEL', 'gemini-2.0-flash-001')
            
            # Verify model is accessible
            self._verify_model()
            
            self.api_configured = True
            logger.info("Gemini API configured successfully with model: %s", self.model_name)
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {str(e)}")
    
    def _verify_model(self):
        """Verify that the model is accessible"""
        try:
            # Simple test call to verify model works
            response = self.client.models.generate_content(
                model=self.model_name,
                contents="Say 'OK'"
            )
            logger.info("Model %s verified successfully", self.model_name)
        except Exception as e:
            logger.warning("Model verification failed: %s", str(e))
            # Fall back to another stable model
            fallback_models = ['gemini-2.0-flash-001', 'gemini-1.5-flash']
            for fallback in fallback_models:
                if fallback != self.model_name:
                    try:
                        response = self.client.models.generate_content(
                            model=fallback,
                            contents="Say 'OK'"
                        )
                        self.model_name = fallback
                        logger.info("Using fallback model: %s", self.model_name)
                        return
                    except:
                        continue

    def _generate_content_with_fallback(self, contents):
        """
        Generate content with retry and model fallback for transient API overload.
        """
        candidate_models = [self.model_name, 'gemini-2.0-flash-001', 'gemini-1.5-flash']
        candidate_models = list(dict.fromkeys(candidate_models))
        last_error = None

        for model in candidate_models:
            for attempt in range(2):
                try:
                    response = self.client.models.generate_content(
                        model=model,
                        contents=contents
                    )
                    if model != self.model_name:
                        logger.info("Switching active Gemini model to: %s", model)
                        self.model_name = model
                    return response
                except Exception as e:
                    last_error = e
                    message = str(e).upper()
                    if ("503" in message or "UNAVAILABLE" in message or "TIMEOUT" in message) and attempt == 0:
                        time.sleep(0.8)
                        continue
                    break

        raise RuntimeError(str(last_error) if last_error else "Gemini request failed")
    
    def analyze_product_image(self, image_file):
        """
        Analyze a product image and extract clothing attributes
        """
        if not self.api_configured:
            return {
                "success": False,
                "error": "AI service not configured. Please add GEMINI_API_KEY to settings."
            }
        
        try:
            # Open and prepare image
            img = Image.open(image_file)
            
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize image to reduce API load
            max_size = 1024
            if max(img.size) > max_size:
                ratio = max_size / max(img.size)
                new_size = tuple(int(dim * ratio) for dim in img.size)
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Convert image to bytes
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG')
            img_bytes = img_byte_arr.getvalue()
            
            # Create prompt for analysis
            prompt = """
            Analyze this clothing/fashion item image and answer with ONLY these details:
            
            Product Type: [what type of clothing - dress, shirt, pants, jacket, etc.]
            Color: [main color(s) of the item]
            Pattern: [pattern type - solid, floral, striped, checkered, etc.]
            Material: [likely material - cotton, denim, silk, polyester, etc.]
            Style: [style - casual, formal, sporty, bohemian, etc.]
            Occasion: [suitable occasion - daily wear, party, office, beach, etc.]
            Season: [suitable season - summer, winter, spring, fall, all-season]
            Features: [list 2-3 key features separated by commas]
            
            Keep responses brief and factual. No markdown or special formatting.
            """
            
            # Use new SDK for content generation
            response = self._generate_content_with_fallback([
                prompt,
                types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
            ])
            
            # Parse the response
            response_text = response.text.strip()
            analysis = self._parse_analysis_response(response_text)
            
            return {
                "success": True,
                "analysis": analysis,
                "raw_response": response_text
            }
            
        except Exception as e:
            logger.error(f"Image analysis failed: {str(e)}")
            return {
                "success": False,
                "error": f"Analysis failed: {str(e)}"
            }
    
    def _parse_analysis_response(self, text):
        """Parse the text response into a dictionary"""
        analysis = {
            "product_type": "clothing item",
            "color": "various",
            "pattern": "solid",
            "material": "fabric",
            "style": "casual",
            "occasion": "daily wear",
            "season": "all-season",
            "key_features": ["comfortable", "stylish"]
        }
        
        # Extract using regex patterns
        patterns = {
            "product_type": r'Product Type:\s*(.+?)(?:\n|$)',
            "color": r'Color:\s*(.+?)(?:\n|$)',
            "pattern": r'Pattern:\s*(.+?)(?:\n|$)',
            "material": r'Material:\s*(.+?)(?:\n|$)',
            "style": r'Style:\s*(.+?)(?:\n|$)',
            "occasion": r'Occasion:\s*(.+?)(?:\n|$)',
            "season": r'Season:\s*(.+?)(?:\n|$)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                analysis[key] = match.group(1).strip()
        
        # Extract features
        features_match = re.search(r'Features:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
        if features_match:
            features_text = features_match.group(1).strip()
            analysis["key_features"] = [f.strip() for f in features_text.split(',') if f.strip()]
        
        return analysis
    
    def get_styling_recommendations(self, product_attributes, user_context=None):
        """
        Get styling recommendations based on product attributes
        """
        if not self.api_configured:
            return {
                "success": False,
                "error": "AI service not configured"
            }
        
        try:
            # Build prompt
            prompt = f"""
            As a fashion stylist, give styling advice for this item:
            
            Item: {product_attributes.get('product_type', 'clothing item')}
            Color: {product_attributes.get('color', 'various')}
            Pattern: {product_attributes.get('pattern', 'solid')}
            Style: {product_attributes.get('style', 'casual')}
            
            Provide:
            1. Casual outfit: [one sentence]
            2. Formal outfit: [one sentence]
            3. Colors that go well: [list 3 colors]
            4. Accessories to pair: [list 3 accessories]
            5. Best shoes: [list 2 shoe types]
            6. Care tip: [one sentence]
            
            Keep each point on a new line. No markdown.
            """
            
            response = self._generate_content_with_fallback(prompt)
            
            recommendations = self._parse_styling_response(response.text)
            
            return {
                "success": True,
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"Styling recommendation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _parse_styling_response(self, text):
        """Parse styling response into structured format"""
        recommendations = {
            "occasion_outfits": {
                "casual": "Pair with jeans and sneakers for a relaxed look",
                "formal": "Combine with dress pants and blazer for a polished appearance",
                "party": "Add statement jewelry and heels for evening events"
            },
            "color_pairings": ["black", "white", "beige"],
            "accessories": ["watch", "minimal jewelry", "crossbody bag"],
            "footwear": ["sneakers", "loafers"],
            "layering": "Add a light jacket or cardigan",
            "seasonal_tips": "Versatile for all seasons",
            "care_instructions": "Follow care label instructions"
        }
        
        lines = text.strip().split('\n')
        
        for line in lines:
            line_lower = line.lower()
            
            if 'casual outfit' in line_lower:
                if ':' in line:
                    recommendations["occasion_outfits"]["casual"] = line.split(':', 1)[1].strip()[:150]
            
            elif 'formal outfit' in line_lower:
                if ':' in line:
                    recommendations["occasion_outfits"]["formal"] = line.split(':', 1)[1].strip()[:150]
            
            elif 'colors' in line_lower and 'go' in line_lower:
                if ':' in line:
                    colors_text = line.split(':', 1)[1].strip()
                    colors = [c.strip() for c in colors_text.split(',')[:3]]
                    if colors:
                        recommendations["color_pairings"] = colors
            
            elif 'accessories' in line_lower:
                if ':' in line:
                    accessories_text = line.split(':', 1)[1].strip()
                    accessories = [a.strip() for a in accessories_text.split(',')[:3]]
                    if accessories:
                        recommendations["accessories"] = accessories
            
            elif 'shoes' in line_lower:
                if ':' in line:
                    shoes_text = line.split(':', 1)[1].strip()
                    shoes = [s.strip() for s in shoes_text.split(',')[:2]]
                    if shoes:
                        recommendations["footwear"] = shoes
            
            elif 'care' in line_lower:
                if ':' in line:
                    recommendations["care_instructions"] = line.split(':', 1)[1].strip()[:150]
        
        return recommendations
    
    def chat_stylist(self, user_message, conversation_history=None):
        """
        Interactive chat with AI stylist
        """
        if not self.api_configured:
            return "AI Fashion Stylist is not configured. Please contact the administrator."
        
        try:
            system_prompt = """
            You are Styla, a friendly AI fashion stylist for FashionNova.
            
            Rules:
            - Keep responses short (2-3 sentences)
            - Be helpful and practical
            - Use simple, clear language
            - No markdown or special formatting
            - Be positive and encouraging
            
            Help with: styling outfits, color coordination, accessories, occasion dressing, fashion trends.
            """
            
            if conversation_history and len(conversation_history) > 1500:
                conversation_history = conversation_history[-1200:]
            
            full_prompt = system_prompt + "\n\n" + (f"Previous: {conversation_history}\n\n" if conversation_history else "") + f"User: {user_message}\n\nStyla:"
            
            response = self._generate_content_with_fallback(full_prompt)
            
            response_text = response.text.strip()
            response_text = re.sub(r'[*_`#]', '', response_text)
            
            return response_text[:500]
            
        except Exception as e:
            logger.error(f"Chat failed: {str(e)}")
            return f"I'm having trouble right now. Please try again. (Error: {str(e)[:50]})"

    def describe_product(self, product):
        """
        Generate a concise product description for seller listings.
        """
        if not self.api_configured:
            return None

        try:
            product_name = getattr(product, "name", "Fashion item")
            category_name = getattr(getattr(product, "category", None), "name", "")
            brand_name = getattr(getattr(product, "brand", None), "name", "")
            color = getattr(product, "color", "")
            material = getattr(product, "material", "")

            prompt = f"""
            Write a concise ecommerce product description (2-3 sentences) for this item:
            Name: {product_name}
            Category: {category_name}
            Brand: {brand_name}
            Color: {color}
            Material: {material}

            Requirements:
            - Friendly and persuasive tone
            - Mention comfort, style, and likely use-case
            - No markdown
            """

            response = self._generate_content_with_fallback(prompt)

            text = (response.text or "").strip()
            text = re.sub(r'[*_`#]', '', text)
            return text[:700] if text else None
        except Exception as e:
            logger.error("Product description generation failed: %s", str(e))
            return None


# Create singleton instance
try:
    ai_stylist = AIFashionStylist()
except Exception as e:
    logger.error("Failed to create AI Stylist: %s", str(e))
    ai_stylist = None