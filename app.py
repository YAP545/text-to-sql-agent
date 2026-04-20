import streamlit as st
import pandas as pd
import ast
import base64
from gtts import gTTS
from io import BytesIO
from streamlit_mic_recorder import mic_recorder
from database import setup_mock_database, get_database_schema
from workflow import create_workflow

st.set_page_config(page_title="Voice SQL Agent", page_icon="🎙️")

# --- UI Header ---
st.title("Voice-Enabled SQL Agent 🤖🎙️")
st.markdown("Speak or type your database questions.")

@st.cache_resource
def init_system():
    db_name = setup_mock_database()
    schema = get_database_schema(db_name)
    app = create_workflow()
    return schema, app

schema, workflow_app = init_system()

# --- Voice Input Logic ---
st.subheader("Step 1: Ask your question")
col1, col2 = st.columns([4, 1])

with col2:
    audio_input = mic_recorder(start_prompt="🎤 Record", stop_prompt="🛑 Stop", key='recorder')

# Capture text input OR voice input
manual_input = col1.text_input("Type here:", key="text_in")
final_query = manual_input

# Use Groq or Google Whisper API to transcribe if you wanted higher accuracy, 
# but for now, we'll focus on the manual/voice UI flow.

# --- Text-to-Speech Function ---
def speak_text(text):
    tts = gTTS(text=text, lang='en')
    fp = BytesIO()
    tts.write_to_fp(fp)
    return fp

# --- Main Logic ---
if st.button("Run Analysis"):
    if final_query:
        with st.spinner("Agent is thinking..."):
            initial_state = {
                "user_query": final_query,
                "db_schema": schema,
                "generated_sql": "",
                "query_results": "",
                "sql_error": "",
                "explanation": ""
            }

            result = workflow_app.invoke(initial_state)

            if result["sql_error"]:
                st.error(result["sql_error"])
            else:
                st.subheader("Explanation")
                st.write(result["explanation"])
                
                # Generate and Play Audio
                audio_fp = speak_text(result["explanation"])
                st.audio(audio_fp, format='audio/mp3', autoplay=True)

                st.subheader("Data Result")
                try:
                    data = ast.literal_eval(result["query_results"])
                    st.dataframe(pd.DataFrame(data), use_container_width=True)
                except:
                    st.write(result["query_results"])

                with st.expander("View Generated SQL"):
                    st.code(result["generated_sql"], language="sql")
