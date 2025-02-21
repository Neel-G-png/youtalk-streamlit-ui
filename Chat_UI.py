import streamlit as st
from urllib.parse import urlparse, parse_qs
from streamlit_local_storage import LocalStorage
import requests
import json
from api_utils import API
from datetime import datetime
import logging
import streamlit.components.v1 as components

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

footer = """
<style>
.footer {
    position: fixed;
    left: 0;
    bottom: 0;
    width: 100%;
    background-color: black;
    color: white;
    text-align: center;
    padding: 12px 20px;
    font-size: 16px;
    z-index: 1000;
    box-shadow: 0 -4px 10px rgba(0, 0, 0, 0.05);
    transition: all 0.3s ease;
}

.footer:hover {
    box-shadow: 0 -4px 15px rgba(0, 0, 0, 0.1);
}

.footer a {
    color: #2D7FF9;
    text-decoration: none;
    padding: 4px 8px;
    border-radius: 4px;
    transition: all 0.3s ease;
    font-weight: 500;
}

.footer a:hover {
    color: #1756B8;
    background-color: #F0F7FF;
    text-decoration: none;
    transform: translateY(-1px);
}

.footer .heart {
    color: #FF4B4B;
    display: inline-block;
    transition: transform 0.3s ease;
}

.footer:hover .heart {
    transform: scale(1.2);
}

.stApp {
    padding-bottom: 60px;
}
</style>

<div class="footer">
    Made with <span class="heart">❤️</span> by 
    <a href="https://neelgandhi.netlify.app/" 
       target="_blank">Neel Gandhi</a>
</div>
"""

st.set_page_config(
    page_title="YouTalk",
    page_icon="🎙️",
    layout="wide"
)

# Include Google Analytics tracking code
with open("analytics.html", "r") as f:
    html_code = f.read()
    components.html(html_code, height=0)

st.header("YouTalk - Coz why not!", divider="rainbow")

def write_stream(stream):
    result = ""
    container = st.empty()
    for chunk in stream:
        result += chunk
        container.markdown(result, unsafe_allow_html=True)
    return result

def ai_response(msg):
    params = {
        "user_id": st.session_state.user,
        "session_id": st.session_state.selected_session,
        "message": msg
    }
    followup = True
    if len(st.session_state.messages) < 2:
        followup = False

    return st.session_state.api.stream_response(params, followup)

def initialize_sessions_state_variables():
    st.session_state.localS = LocalStorage()
    st.session_state.api = API(baseurl=st.secrets["API_BASE_URL"])
    st.session_state.user_logo = "custom_chat_logos/user.jpg"
    st.session_state.ai_logo = "custom_chat_logos/cat_bot.jpg"
    storage_values = st.session_state.localS.getAll()
    st.session_state.user = storage_values['ajs_anonymous_id']
    if not storage_values.get("youtalk_user_sessions", None):
        params = {"user_id":st.session_state.user }

        response = st.session_state.api.get_all_user_sessions(params)
        
        if response['status'] != "success":
            st.error(response['message'])
            st.session_state.user_sessions = []
        else:
            st.session_state.user_sessions = response['data']['user_sessions']
            st.session_state.localS.setItem("youtalk_user_sessions", st.session_state.user_sessions)
    else:
        st.session_state.user_sessions = storage_values['youtalk_user_sessions']
    st.session_state.variables_exist = True
    st.session_state.messages = []
    st.session_state.selected_session = None

def erase_local_storage():
    localS = LocalStorage()
    localS.eraseItem('youtalk_user_sessions')
    if "session_id" in st.query_params:
        del st.query_params['session_id']

def fetch_chat_history(session_id):
    current_selected_session = st.session_state.selected_session
    if session_id is None:
        return

    if session_id != current_selected_session:
        with st.spinner("Fetching chat history..."):
            params = {
                "user_id": st.session_state.user,
                "session_id": session_id
            }

            response = st.session_state.api.get_chat_history(params)

            if response['status'] != "success":
                st.error(response['message'])
                st.session_state.messages = []
                st.session_state.sellected_session = None
                st.query_params['session_id'] = None
            else:
                st.query_params['session_id'] = session_id
                st.session_state.messages = json.loads(response['data']['chat_history'])
                st.session_state.selected_session = session_id

def validate_session_id(session_id):
    for i, session in enumerate(st.session_state.user_sessions):
        if session[0] == session_id:
            return i
    st.error("Dont try to be sneakyyyyy!")
    if "session_id" in st.query_params:
        del st.query_params['session_id']
    return None

def chat_with_history(video_display_container):
    # Check session ID
    qp_session_id = st.query_params.get("session_id", None)
    index = validate_session_id(qp_session_id) if qp_session_id and qp_session_id != "None" else None
    selected_session = st.selectbox(
        "Older Chats",
        placeholder = "Select an old chat",
        index = index,
        options = st.session_state.user_sessions,
        format_func = lambda x: x[1],
        # key = "selected_session"
    )
    # if selected_session:
    #     st.session_state.selected_session = selected_session[0]
    fetch_chat_history(selected_session[0] if selected_session else None)

    if selected_session:
        video_display_container.video(selected_session[2])
        
def validate_youtube_link(youtube_link):
    parsed_url = urlparse(youtube_link)
    
    if parsed_url.netloc in ["www.youtube.com", "youtube.com", "m.youtube.com"]:
        query_params = parse_qs(parsed_url.query)
        return "v" in query_params  # Check if 'v' parameter exists
    
    if parsed_url.netloc in ["youtu.be"]:
        return len(parsed_url.path.strip("/")) == 11  # Shortened URL should have 11-character video ID

    return False

def process_youtube_link(video_display_container):
    st.write("## New Chat")
    with st.form(key="Insert Youtube Link"):
        yt_URL = st.text_input("Paste a Youtube Link")
        submitted = st.form_submit_button("Start Chat")
        if submitted:
            if not validate_youtube_link(yt_URL):
                st.error("Invalid Youtube Link. Please enter a valid Youtube Link.")
            else:
                with st.spinner("Learing about video...", show_time=False):
                    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    params = {
                        "user_id": st.session_state.user,
                        "video_link": yt_URL,
                        "created_at":  created_at
                    }
                    response = st.session_state.api.process_video(params)
                    try:
                        if response['status'] != "success":
                            st.error(response['data'])
                        else:
                            if response['data']['sub_status'] == 202 or response['data']['sub_status'] == 200:
                                st.session_state.user_sessions = [(response['data']['session_id'], response['data']['video_name'], yt_URL, created_at)] + st.session_state.user_sessions

                                # Also add it to local storage for persistence
                                st.session_state.localS.setItem("youtalk_user_sessions", st.session_state.user_sessions)


                            st.query_params['session_id'] = response['data']['session_id']
                    except Exception as e:
                        st.error(response)
                            
def save_msg(role, msg):
    if not st.session_state.selected_session:
        return
    params = {
        "session_id": st.session_state.selected_session,
        "role": role,
        "message": msg,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    response = st.session_state.api.insert_message(params)
    if response['status'] != "success":
        st.error(response['message'])

def disclaimer():
    st.markdown("""
    <style>
        .highlight-box {
            display: inline-block;
            padding: 2px 8px;
            margin: 0 2px;
            border-radius: 4px;
            font-weight: bold;
            background-color: rgba(147, 51, 234, 0.1);
            color: #9333EA;
            border: 1px solid rgba(147, 51, 234, 0.2);
        }
    </style>
    
    ## Disclaimer‼️

    - Everything is <span class="highlight-box">FREE</span>.
    - Since it runs on free-tier services, usage limits might be imposed frequently  
    - If you can't access it right now, try again later or report a bug using the <span class="highlight-box">form below</span>.  
    - If something else seems off, feel free to <span class="highlight-box">reach out to me</span>.  
    - Enjoying the project? Got an open position? I'd love to hear from you — <span class="highlight-box">I'm looking for a job!</span>
    """, unsafe_allow_html=True)
    st.divider()
    st.markdown("[Report a 🐛](https://docs.google.com/forms/d/e/1FAIpQLScK0dQdnzfeNfAw_v_AK-vVTUvHUyMaQiNzl81taubNT73MLg/viewform?usp=dialog)")

# erase_local_storage()

if 'variables_exist' not in st.session_state:
    initialize_sessions_state_variables()


# fetch_chat_history(st.query_params.get("session_id", None))

st.markdown(footer,unsafe_allow_html=True)

with st.sidebar:
    video_display_container = st.empty()
    process_youtube_link(video_display_container)
    st.write("## Or")
    chat_with_history(video_display_container)
    st.divider()
    disclaimer()

for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar=st.session_state.ai_logo if message["role"] == 'user' else st.session_state.user_logo):
        st.markdown(message["msg"])

if prompt := st.chat_input("What is up?"):
    # Add user message to chat history
    if st.session_state.selected_session:
        st.session_state.messages.append({"role": "user", "msg": prompt})
        save_msg("user", prompt)

    with st.chat_message("user", avatar=st.session_state.user_logo):
        st.markdown(prompt)

    ai_msg = ""
    if st.session_state.selected_session:
        with st.spinner("Responding..."):
            with st.chat_message("assistant", avatar=st.session_state.ai_logo):
                ai_msg += write_stream(stream=ai_response(prompt))

        st.session_state.messages.append({"role": "assistant", "msg": ai_msg})
        save_msg("assistant", ai_msg)
    else:
        with st.chat_message("assistant", avatar=st.session_state.ai_logo):
            st.markdown("Please select a video to continue chatting.")