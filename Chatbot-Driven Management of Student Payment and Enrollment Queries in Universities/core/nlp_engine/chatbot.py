import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAQ_PATH = os.path.join(BASE_DIR, 'knowledge_base', 'faq.json')

def get_bot_response(user_message):
    import re
    user_message = user_message.lower()
    # Clean user message to just alphabetic words
    user_words = set(re.findall(r'\b\w+\b', user_message))

    if os.path.exists(FAQ_PATH):
        try:
            with open(FAQ_PATH, 'r', encoding='utf-8') as f:
                faq_data = json.load(f)
            
            best_match_intent = None
            max_matches = 0
            
            for intent, data in faq_data.items():
                faq_keywords = data.get('keywords', [])
                score = 0
                for kw in faq_keywords:
                    kw_lower = kw.lower()
                    
                    # Exact phrase match in the user string gives a massive boost
                    if kw_lower in user_message:
                        score += 10 if ' ' in kw_lower else 3
                    
                    # Also check standalone word intersection for partial matches
                    if kw_lower in user_words:
                        score += 1
                        
                if score > max_matches:
                    max_matches = score
                    best_match_intent = data
            
            # Return response if at least one meaningful keyword matched
            if best_match_intent and max_matches > 0:
                return best_match_intent.get('response', "Sorry, I couldn't understand that.")
        except Exception as e:
            print(f"Error reading faq.json: {e}")

    # Fallback message
    return "Sorry, I could not find information related to your question."

