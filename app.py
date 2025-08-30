import os, json, re
from string import Template
import random
from datetime import datetime
import hashlib

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

# Google Gen AI SDK (Gemini)
from google import genai
from google.genai import types

# -------------------- Setup --------------------
load_dotenv()
st.set_page_config(
    page_title="✨ AI Motivator & Quote Generator", 
    page_icon="✨", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2rem;
    }
    .motivation-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        margin: 1rem 0;
    }
    .quote-box {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    .step-box {
        background: rgba(255, 255, 255, 0.1);
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid #fff;
    }
    .mantra-box {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        font-size: 1.2rem;
        font-weight: bold;
        color: white;
        margin: 1rem 0;
    }
    .reflection-box {
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: #333;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">✨ AI Personal Motivator & Quote Generator</h1>', unsafe_allow_html=True)

_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not _api_key:
    st.error("⚠ No GEMINI_API_KEY found. Please add it to your .env file and restart the app.")
    st.stop()

client = genai.Client(api_key=_api_key)
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Enhanced system prompt with stronger personalization instructions
SYSTEM_PROMPT = """
You are a caring friend and motivational coach with a deep understanding of human emotions. The user will share something with you - analyze their EXACT words, tone, and emotional state.

CRITICAL RULES FOR PERSONALIZATION:
1. NEVER use generic templates or standard responses
2. Reference their SPECIFIC words and situation in your response
3. Match their emotional energy level (calm for sad, energetic for excited, etc.)
4. Use their exact language style and vocabulary level
5. Address their SPECIFIC concerns, not general ones
6. Create responses that feel like you know them personally

EMOTIONAL ANALYSIS REQUIRED:
- Identify their primary emotion (sad, excited, anxious, angry, confused, etc.)
- Determine their energy level (high, medium, low)
- Note any specific triggers or situations they mention
- Assess what type of support they need (comfort, celebration, guidance, etc.)

PERSONALIZATION CHECKLIST:
✓ Reference specific words/phrases they used
✓ Mirror their communication style  
✓ Address their exact situation
✓ Match their emotional tone
✓ Provide situation-specific advice
✓ Use relevant metaphors for their context
✓ Give actionable steps for THEIR specific challenge

You MUST return a single valid JSON object ONLY (no backticks, markdown, or extra text).

Two output shapes:

1) For mode="message":
{
  "type": "message",
  "motivation": "<Write a deeply personalized response that directly quotes or references their specific words. Mirror their tone - if they're excited, be excited with them. If they're sad, be gentle and comforting. Make them feel truly seen and understood.>",
  "steps": ["<Give them 4 specific, actionable steps that directly address their EXACT situation and challenges>"],
  "mantra": "<Create a mantra using words or themes from their message - make it personal to their situation>",
  "quotes": [{"quote":"<Choose quotes that directly relate to their specific emotion and situation>", "author":"<author>", "context":"<Explain why THIS quote is perfect for THEIR specific situation>"}, ...],
  "reflection_questions": ["<Ask questions that dig into their specific situation and help them process their exact feelings>"],
  "daily_affirmation": "<Create an affirmation that directly addresses their situation and uses language that resonates with their message>"
}

2) For mode="quote":
{
  "type": "quote",
  "quotes": [{"quote":"<Select quotes that match their emotional state and specific situation>", "author":"<author>", "context":"<Why this quote speaks to their exact circumstances>", "category":"<category that fits their need>"}, ...],
  "reflection": "<Write about how these quotes specifically relate to what they shared - use their words and reference their situation>",
  "theme": "<Identify a theme that emerges from THEIR specific message>",
  "application": "<Give specific ways they can apply these quotes to their exact situation>"
}

REMEMBER: Every word should feel like it was written specifically for this person's unique situation. NO GENERIC ADVICE ALLOWED.
"""

# -------------------- UI Controls --------------------
with st.sidebar:
    st.header("🎛️ Configuration")
    
    model = st.selectbox(
        "AI Model", 
        ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"], 
        index=0,
        help="Choose the AI model for generation"
    )
    
    tone = st.selectbox(
        "Tone & Style", 
        ["adaptive", "inspiring", "empathetic", "energetic", "calm", "practical", "philosophical"], 
        index=0,
        help="Adaptive automatically matches the user's emotional state"
    )
    
    length = st.select_slider(
        "Response Length",
        options=["concise", "detailed", "comprehensive", "extensive"],
        value="detailed",
        help="Controls the depth and length of responses"
    )
    
    num_quotes = st.slider("Number of quotes", 3, 10, 5)
    
    st.header("🎯 Features")
    include_steps = st.checkbox("Include detailed action steps", value=True)
    include_quotes_in_message = st.checkbox("Add quotes to motivational messages", value=True)
    include_reflection_questions = st.checkbox("Include reflection questions", value=True)
    include_daily_affirmation = st.checkbox("Include daily affirmation", value=True)
    auto_speak = st.checkbox("Auto-speak responses", value=False)
    
    st.header("📊 Response Quality")
    creativity = st.slider("Creativity Level", 0.1, 1.0, 0.9, 0.1, help="Higher values create more unique responses")
    detail_level = st.slider("Detail Level", 1, 5, 4)
    personalization_strength = st.slider("Personalization Intensity", 1, 5, 5, help="How specifically tailored to user's input")
    
    st.header("🔄 Session Management")
    if st.button("Clear Response", help="Clear current response"):
        st.session_state.result = {}
        st.rerun()

# Main interface
col1, col2 = st.columns([2, 1])

with col1:
    mode = st.radio(
        "Choose your experience:",
        ["message", "quote", "both"],
        horizontal=True,
        help="Message: Detailed motivation with steps. Quote: Curated quotes with reflection. Both: Complete experience."
    )
    
    mood = st.text_area(
        "Share your thoughts, feelings, or situation:",
        placeholder="e.g., I'm feeling overwhelmed with work and personal life. I have a big presentation tomorrow and I'm doubting myself. I want to find motivation and clarity...",
        height=120
    )
    
    go = st.button("✨ Generate Inspiration", type="primary", use_container_width=True)

with col2:
    st.info("💡 **Tips for better responses:**\n\n• Be specific about your situation\n• Share your emotions honestly\n• Mention what you're struggling with\n• Include context about your goals")
    

if "result" not in st.session_state:
    st.session_state.result = {}

if "response_history" not in st.session_state:
    st.session_state.response_history = {}

# -------------------- Enhanced Prompt Building --------------------
def create_context_hash(user_text: str) -> str:
    """Create a unique hash based on user input to track response uniqueness"""
    return hashlib.md5(user_text.lower().strip().encode()).hexdigest()[:8]

def analyze_user_emotion(user_text: str) -> dict:
    """Analyze user's emotional state and context"""
    text = user_text.lower().strip()
    
    emotion_indicators = {
        'excited': ['excited', 'thrilled', 'amazing', 'fantastic', 'awesome', 'great news', 'celebration', 'happy', 'joy'],
        'sad': ['sad', 'depressed', 'down', 'crying', 'hurt', 'heartbroken', 'devastated', 'miserable'],
        'anxious': ['anxious', 'worried', 'nervous', 'stress', 'fear', 'panic', 'overwhelmed', 'scared'],
        'angry': ['angry', 'frustrated', 'mad', 'upset', 'annoyed', 'furious', 'irritated'],
        'confused': ['confused', 'lost', 'unsure', 'doubt', 'uncertain', 'don\'t know', 'unclear'],
        'tired': ['tired', 'exhausted', 'burnout', 'drained', 'worn out'],
        'hopeful': ['hopeful', 'optimistic', 'looking forward', 'positive', 'motivated'],
        'grateful': ['grateful', 'thankful', 'blessed', 'appreciate', 'lucky']
    }
    
    detected_emotions = []
    for emotion, indicators in emotion_indicators.items():
        if any(indicator in text for indicator in indicators):
            detected_emotions.append(emotion)
    
    # Determine primary emotion
    primary_emotion = detected_emotions[0] if detected_emotions else 'neutral'
    
    # Determine energy level
    high_energy_words = ['excited', 'thrilled', 'amazing', 'fantastic', 'angry', 'furious', 'panic']
    low_energy_words = ['tired', 'exhausted', 'sad', 'down', 'drained']
    
    if any(word in text for word in high_energy_words):
        energy_level = 'high'
    elif any(word in text for word in low_energy_words):
        energy_level = 'low'
    else:
        energy_level = 'medium'
    
    # Extract key themes
    themes = []
    if any(word in text for word in ['work', 'job', 'career', 'boss', 'colleague']):
        themes.append('work')
    if any(word in text for word in ['relationship', 'partner', 'family', 'friend']):
        themes.append('relationships')
    if any(word in text for word in ['health', 'sick', 'medical', 'doctor']):
        themes.append('health')
    if any(word in text for word in ['money', 'financial', 'debt', 'expensive']):
        themes.append('finances')
    if any(word in text for word in ['school', 'study', 'exam', 'college', 'university']):
        themes.append('education')
    
    return {
        'primary_emotion': primary_emotion,
        'all_emotions': detected_emotions,
        'energy_level': energy_level,
        'themes': themes,
        'text_length': len(user_text),
        'is_greeting': len(text) < 20 and any(greeting in text for greeting in ['hi', 'hello', 'hey', 'good morning', 'good afternoon'])
    }

def build_instruction(user_text: str) -> str:
    requested_mode = "message" if mode in ("message", "both") else "quote"
    
    # Analyze user's emotional context
    emotion_analysis = analyze_user_emotion(user_text)
    
    # Create unique context hash
    context_hash = create_context_hash(user_text)
    
    # Add randomization seed
    random_seed = random.randint(1000, 9999)
    
    # Build highly personalized context
    personalization_context = f"""
UNIQUE RESPONSE ID: {context_hash}-{random_seed}
USER'S EXACT WORDS: "{user_text}"
EMOTIONAL ANALYSIS:
- Primary emotion: {emotion_analysis['primary_emotion']}
- Energy level: {emotion_analysis['energy_level']}
- Key themes: {', '.join(emotion_analysis['themes']) if emotion_analysis['themes'] else 'general'}
- Message type: {'greeting' if emotion_analysis['is_greeting'] else 'substantive'}

PERSONALIZATION REQUIREMENTS:
1. Quote or reference their EXACT words: "{user_text[:50]}{'...' if len(user_text) > 50 else ''}"
2. Match their emotional energy ({emotion_analysis['energy_level']})
3. Address their primary emotion ({emotion_analysis['primary_emotion']})
4. Focus on themes: {emotion_analysis['themes']}
5. Personalization level: {personalization_strength}/5

RESPONSE STYLE ADAPTATION:
- Tone: {tone if tone != 'adaptive' else f"match their {emotion_analysis['primary_emotion']} energy"}
- Length: {length}
- Creativity boost: {creativity}

CRITICAL: This response must be COMPLETELY DIFFERENT from any previous response. Use their specific situation, words, and emotional state to create something unique.
"""

    return (
        SYSTEM_PROMPT.strip()
        + "\n\n"
        + personalization_context
        + f"\nMODE: {requested_mode}\n"
        + f"NUMBER OF QUOTES: {num_quotes}\n"
        + "\n"
        + "Create a response that feels like you're their close friend who truly understands their specific situation. NO GENERIC RESPONSES ALLOWED."
    )

def parse_loose_json(s: str):
    """Enhanced JSON parsing with better error handling."""
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        pass
    
    # Try to extract JSON from markdown code blocks
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', s, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except Exception:
            pass
    
    # Try to find the largest JSON object
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(s[start:end+1])
        except Exception:
            pass
    return None

def call_gemini(user_text: str):
    requested_mode = "message" if mode in ("message", "both") else "quote"
    
    # Enhanced temperature calculation for more variety
    base_temp = max(0.8, creativity)
    
    # Add randomization based on content
    content_hash = hash(user_text) % 100
    temp_variance = (content_hash / 100) * 0.2  # 0.0 to 0.2 variance
    
    emotion_analysis = analyze_user_emotion(user_text)
    
    # Adjust temperature based on emotional context
    if emotion_analysis['primary_emotion'] in ['excited', 'happy']:
        temp = min(1.0, base_temp + 0.1 + temp_variance)
    elif emotion_analysis['primary_emotion'] in ['sad', 'anxious']:
        temp = max(0.7, base_temp - 0.1 + temp_variance)
    else:
        temp = base_temp + temp_variance
    
    prompt = build_instruction(user_text)
    
    # Enhanced generation config
    cfg = types.GenerateContentConfig(
        temperature=temp,
        max_output_tokens=2500,
        candidate_count=1,
        top_p=0.95,
        top_k=40,  # Add top_k for more variety
    )

    try:
        resp = client.models.generate_content(
            model=model,
            contents=prompt,
            config=cfg,
        )

        raw = (getattr(resp, "text", None) or "").strip()
        data = parse_loose_json(raw)

        # Store response to avoid repetition
        context_hash = create_context_hash(user_text)
        if context_hash not in st.session_state.response_history:
            st.session_state.response_history[context_hash] = []
        st.session_state.response_history[context_hash].append(data)

        if not data:
            # Create truly personalized fallback based on user's actual input
            emotion_analysis = analyze_user_emotion(user_text)
            
            if requested_mode == "message":
                # Personalized fallback based on their input
                motivation_text = f"I hear you when you say '{user_text[:100]}{'...' if len(user_text) > 100 else ''}'. "
                
                if emotion_analysis['primary_emotion'] == 'excited':
                    motivation_text += "Your excitement is contagious! This energy you're feeling is powerful - it's the fuel of achievement."
                elif emotion_analysis['primary_emotion'] == 'sad':
                    motivation_text += "I can feel the heaviness in your words, and I want you to know that it's okay to feel this way."
                elif emotion_analysis['primary_emotion'] == 'anxious':
                    motivation_text += "I understand that anxiety can feel overwhelming, but you're stronger than you realize."
                elif emotion_analysis['is_greeting']:
                    motivation_text = "Hello there! I'm so glad you reached out today. How are you really feeling right now?"
                else:
                    motivation_text += "Your situation is unique, and you deserve support that truly understands what you're going through."
                
                data = {
                    "type": "message",
                    "motivation": motivation_text,
                    "steps": [
                        f"Reflect on what you just shared: '{user_text[:50]}{'...' if len(user_text) > 50 else ''}'",
                        f"Focus on your {emotion_analysis['primary_emotion']} feelings and what they're telling you",
                        "Take one small action that aligns with your current emotional state",
                        "Practice self-compassion as you navigate this moment"
                    ],
                    "mantra": f"I honor my {emotion_analysis['primary_emotion']} feelings and trust my journey",
                    "quotes": [
                        {"quote": "The only way to do great work is to love what you do.", "author": "Steve Jobs", "context": f"This resonates with your {emotion_analysis['primary_emotion']} energy"},
                        {"quote": "Success is not final, failure is not fatal: it is the courage to continue that counts.", "author": "Winston Churchill", "context": "Speaks to the resilience I see in your message"}
                    ],
                    "reflection_questions": [
                        f"What does your {emotion_analysis['primary_emotion']} feeling tell you about what you need right now?",
                        f"How can you honor the situation you described: '{user_text[:30]}{'...' if len(user_text) > 30 else ''}'?",
                        "What would self-compassion look like in this moment?"
                    ],
                    "daily_affirmation": f"I trust my {emotion_analysis['primary_emotion']} feelings and my ability to navigate this situation"
                }
            else:
                data = {
                    "type": "quote",
                    "quotes": [
                        {"quote": "The future belongs to those who believe in the beauty of their dreams.", "author": "Eleanor Roosevelt", "context": f"This speaks to the {emotion_analysis['primary_emotion']} energy in your message", "category": "motivation"},
                        {"quote": "It does not matter how slowly you go as long as you do not stop.", "author": "Confucius", "context": "Perfectly fits your current situation", "category": "wisdom"}
                    ],
                    "reflection": f"Your words '{user_text[:100]}{'...' if len(user_text) > 100 else ''}' reveal someone who is {emotion_analysis['primary_emotion']} and seeking guidance. These quotes speak directly to your emotional state.",
                    "theme": f"Navigating {emotion_analysis['primary_emotion']} feelings with wisdom",
                    "application": f"Use these quotes to guide you through your current {emotion_analysis['primary_emotion']} experience"
                }
        
        return data
        
    except Exception as e:
        st.error(f"Error calling AI: {str(e)}")
        return None

# -------------------- Enhanced Rendering --------------------
def render_message(data: dict):
    st.markdown('<div class="motivation-box">', unsafe_allow_html=True)
    st.markdown("### 💫 Your Personalized Motivation")
    st.write(data.get("motivation", ""))
    st.markdown('</div>', unsafe_allow_html=True)

    if include_steps and data.get("steps"):
        st.markdown("### 🎯 Action Steps")
        for i, step in enumerate(data["steps"], 1):
            st.markdown(f'<div class="step-box"><strong>{i}.</strong> {step}</div>', unsafe_allow_html=True)

    if data.get("mantra"):
        st.markdown(f'<div class="mantra-box">🎭 Your Mantra: "{data["mantra"]}"</div>', unsafe_allow_html=True)

    if data.get("daily_affirmation"):
        st.markdown(f'<div class="mantra-box">✨ Daily Affirmation: "{data["daily_affirmation"]}"</div>', unsafe_allow_html=True)

    if data.get("reflection_questions"):
        st.markdown("### 🤔 Reflection Questions")
        for i, question in enumerate(data["reflection_questions"], 1):
            st.markdown(f"**{i}.** {question}")

    if data.get("quotes"):
        st.markdown("### 📚 Inspiring Quotes")
        for q in data["quotes"]:
            quote_text = f'"{q.get("quote", "")}" — *{q.get("author", "")}*'
            if q.get("context"):
                quote_text += f"\n💡 {q.get('context')}"
            st.markdown(f'<div class="quote-box">{quote_text}</div>', unsafe_allow_html=True)

def render_quotes(data: dict):
    quotes = data.get("quotes", [])
    if quotes:
        st.markdown("### 📚 Curated Quotes for You")
        for i, q in enumerate(quotes, 1):
            quote_text = f'**{i}.** "{q.get("quote", "")}" — *{q.get("author", "")}*'
            if q.get("context"):
                quote_text += f"\n💡 {q.get('context')}"
            if q.get("category"):
                quote_text += f"\n🏷️ Category: {q.get('category')}"
            st.markdown(f'<div class="quote-box">{quote_text}</div>', unsafe_allow_html=True)
    
    if data.get("theme"):
        st.markdown(f"### 🎯 Theme: {data['theme']}")
    
    if data.get("reflection"):
        st.markdown("### 💭 Deep Reflection")
        st.markdown(f'<div class="reflection-box">{data["reflection"]}</div>', unsafe_allow_html=True)
    
    if data.get("application"):
        st.markdown("### 🚀 How to Apply This Wisdom")
        st.write(data["application"])

def speak_and_copy_widget(text: str, title: str = "Response"):
    if not text:
        return
    
    escaped = json.dumps(text)
    html = Template("""
      <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 10px; margin: 1rem 0;">
        <h4 style="color: white; margin-bottom: 0.5rem;">🔊 $title</h4>
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
          <button id="speakBtn" style="background: #4CAF50; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer;">🔊 Speak</button>
          <button id="copyBtn" style="background: #2196F3; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer;">📋 Copy</button>
          <button id="pauseBtn" style="background: #FF9800; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer;">⏸️ Pause</button>
        </div>
      </div>
      <script>
        const TEXT = $text;
        const auto = $autospeak;
        let speaking = false;
        
        function speak(t){
          if (speaking) {
            window.speechSynthesis.cancel();
            speaking = false;
            return;
          }
          window.speechSynthesis.cancel();
          const u = new SpeechSynthesisUtterance(t);
          u.rate = 0.9; u.pitch = 1; u.volume = 1;
          u.onstart = () => { speaking = true; };
          u.onend = () => { speaking = false; };
          window.speechSynthesis.speak(u);
        }
        
        function pause() {
          window.speechSynthesis.pause();
        }
        
        document.getElementById('speakBtn').onclick = () => speak(TEXT);
        document.getElementById('copyBtn').onclick = () => {
          navigator.clipboard.writeText(TEXT).then(()=>{
            const b = document.getElementById('copyBtn');
            b.textContent='✅ Copied!'; 
            setTimeout(()=>b.textContent='📋 Copy', 2000);
          });
        };
        document.getElementById('pauseBtn').onclick = () => pause();
        
        if (auto && TEXT.length>0){ 
          setTimeout(() => speak(TEXT), 1000); 
        }
      </script>
    """).substitute(text=escaped, autospeak=str(auto_speak).lower(), title=title)
    components.html(html, height=120)

# -------------------- Main Execution --------------------
if go:
    if not mood.strip():
        st.error("⚠ Please share your thoughts or feelings first.")
    else:
        with st.spinner("🤔 Crafting your personalized inspiration..."):
            try:
                data = call_gemini(mood)
                if data:
                    st.session_state.result = data
                    st.success("✨ Your inspiration is ready!")
                else:
                    st.error("⚠ Unable to generate response. Please try again.")
            except Exception as e:
                st.error(f"⚠ Error: {e}")

res = st.session_state.get("result", {})

if res:
    t = res.get("type")
    
    if mode == "message":
        render_message(res)
        full_text = res.get("motivation", "") + " " + res.get("mantra", "") + " " + res.get("daily_affirmation", "")
        speak_and_copy_widget(full_text, "Motivational Message")
        
    elif mode == "quote":
        render_quotes(res)
        # Speak first quote + reflection
        first_q = ""
        if res.get("quotes"):
            q0 = res["quotes"][0]
            first_q = f"{q0.get('quote','')} — {q0.get('author','')}"
        speak_and_copy_widget(first_q + " " + res.get("reflection",""), "Quote Collection")
        
    else:  # both
        render_message(res)
        if res.get("quotes"):
            st.markdown("---")
            render_quotes(res)
        full_text = res.get("motivation","") + " " + res.get("mantra","") + " " + res.get("daily_affirmation","")
        speak_and_copy_widget(full_text, "Complete Experience")
else:
    st.info("💡 **Welcome!** Share your thoughts, choose your experience, and let AI create personalized inspiration for you.")
    
    # Show example
    with st.expander("💡 Try these different inputs to see unique responses"):
        st.markdown("""
        **Simple greetings:**
        - "Hi"
        - "Hello there"
        - "Good morning"
        
        **Different emotions:**
        - "I'm feeling really sad today"
        - "I'm so excited about my new job!"
        - "I'm anxious about my presentation tomorrow"
        - "I'm angry at my boss"
        - "I'm confused about what to do next"
        
        **Different situations:**
        - "I just broke up with my partner"
        - "I got promoted at work!"
        - "I'm tired of everything"
        - "I don't know what I want in life"
        
        **Each response will be completely different and personalized!**
        """)

# Display debug info in sidebar during development
if st.sidebar.checkbox("Show Debug Info", value=False):
    if mood:
        emotion_analysis = analyze_user_emotion(mood)
        st.sidebar.json(emotion_analysis)