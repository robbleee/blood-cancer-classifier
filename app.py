import streamlit as st
import time

# Page configuration
st.set_page_config(
    page_title="Haematix - Moving to New Platform",
    page_icon="🩸",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for white and teal theme
st.markdown("""
<style>
    .main {
        padding-top: 2rem;
    }
    
    .stApp {
        background-color: white;
    }
    
    .title {
        color: #008B8B;
        text-align: center;
        font-size: 3rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    
    .subtitle {
        color: #20B2AA;
        text-align: center;
        font-size: 1.5rem;
        margin-bottom: 2rem;
    }
    
    .message {
        color: #2F4F4F;
        text-align: center;
        font-size: 1.2rem;
        line-height: 1.6;
        margin-bottom: 2rem;
        padding: 1rem;
        background-color: #F0FFFF;
        border-radius: 10px;
        border-left: 4px solid #008B8B;
    }
    
    .redirect-info {
        color: #696969;
        text-align: center;
        font-size: 1rem;
        margin-top: 2rem;
        font-style: italic;
    }
    
    .countdown {
        color: #008B8B;
        text-align: center;
        font-size: 2rem;
        font-weight: bold;
        margin: 1rem 0;
    }
    
    .button-container {
        display: flex;
        justify-content: center;
        margin: 2rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Main content
st.markdown('<h1 class="title">🩸 Haematix</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">We\'ve moved to a new home!</p>', unsafe_allow_html=True)

st.markdown("""
<div class="message">
    <p>Thank you for visiting Haematix! We're excited to announce that we've moved to our new platform with enhanced features and improved user experience.</p>
</div>
""", unsafe_allow_html=True)

# Countdown and redirect
if 'countdown' not in st.session_state:
    st.session_state.countdown = 10

# Create columns for better layout
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    # Manual redirect button using link_button
    st.link_button("🚀 Take me to the new platform", 
                   "https://www.haem.io/", 
                   use_container_width=True)

# Auto-redirect countdown
st.markdown('<p class="redirect-info">Or wait for automatic redirect...</p>', unsafe_allow_html=True)

# Countdown display
countdown_placeholder = st.empty()

# Auto-redirect logic with improved JavaScript
if st.session_state.countdown > 0:
    countdown_placeholder.markdown(f'<p class="countdown">Redirecting in {st.session_state.countdown} seconds</p>', unsafe_allow_html=True)
    time.sleep(1)
    st.session_state.countdown -= 1
    st.rerun()
else:
    countdown_placeholder.markdown('<p class="countdown">Redirecting now...</p>', unsafe_allow_html=True)
    # Use meta refresh as fallback and improved JavaScript
    st.markdown("""
    <meta http-equiv="refresh" content="0; url=https://haemio.streamlit.app/">
    <script>
    setTimeout(function() {
        window.location.replace('https://haemio.streamlit.app/');
    }, 100);
    </script>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #696969; font-size: 0.9rem; margin-top: 2rem;">
    <p>Thank you for being part of our journey! 💙</p>
    <p>If you have any questions, please contact us through our new platform.</p>
</div>
""", unsafe_allow_html=True) 