# ai_stylist/fashion_knowledge.py
FASHION_KNOWLEDGE = {
    "color_combinations": {
        "red": ["white", "black", "navy", "beige"],
        "blue": ["white", "gray", "brown", "yellow"],
        "black": ["any color", "especially white, red, gold"],
        # Add more color combinations
    },
    "body_types": {
        "hourglass": "Fitted waist, wrap dresses, belted styles",
        "pear": "A-line skirts, dark bottoms, bright tops",
        "apple": "V-necks, empire waist, vertical lines",
        "rectangle": "Peplum, ruffles, belted waists"
    },
    "occasion_guide": {
        "wedding": "Formal wear, pastel colors, elegant accessories",
        "work": "Professional attire, neutral colors, minimal accessories",
        "party": "Bold colors, sequins, statement jewelry",
        "casual": "Comfortable fabrics, relaxed fits, simple accessories"
    }
}

def enhance_prompt_with_knowledge(product_type, occasion):
    """Add fashion knowledge to AI prompts"""
    knowledge_context = ""
    
    # Add color knowledge
    knowledge_context += "Color pairing guidelines:\n"
    for color, pairs in FASHION_KNOWLEDGE["color_combinations"].items():
        knowledge_context += f"- {color} pairs well with {', '.join(pairs)}\n"
    
    # Add occasion knowledge
    if occasion in FASHION_KNOWLEDGE["occasion_guide"]:
        knowledge_context += f"\nFor {occasion} occasions: {FASHION_KNOWLEDGE['occasion_guide'][occasion]}\n"
    
    return knowledge_context