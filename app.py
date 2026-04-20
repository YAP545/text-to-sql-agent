import streamlit as st
import pandas as pd
import sqlite3
import ast
from gtts import gTTS
from io import BytesIO
from streamlit_mic_recorder import mic_recorder, speech_to_text
from workflow import create_workflow

st.set_page_config(page_title="AI Data Agent", page_icon="🎙️")

# --- Initialize Workflow ---
workflow_app = create_workflow()

def get_schema_from_uploaded_file(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';")
    schema = "\n".join([row[0] for row in cursor.fetchall() if row[0]])
    conn.close()
    return schema

def speak_text(text):
    tts = gTTS(text=text, lang='en')
    fp = BytesIO()
    tts.write_to_fp(fp)
    return fp

# --- Sidebar: Database Upload ---
with st.sidebar:
    st.header("📂 Upload Database")
    uploaded_file = st.file_uploader("Upload an SQLite file", type=["db", "sqlite"])
    
    if uploaded_file:
        # Save uploaded file locally to connect to it
        with open("temp_db.db", "wb") as f:
            f.write(uploaded_file.getbuffer())
        current_db = "temp_db.db"
        st.success("Database Loaded!")
    else:
        st.warning("Please upload a .db file to begin.")
        st.stop()

    schema = get_schema_from_uploaded_file(current_db)
    st.subheader("Detected Schema")
    st.code(schema, language="sql")

# --- Main UI ---
st.title("Autonomous Voice-to-SQL Agent 🤖")

st.subheader("Step 1: Ask your question")
# This component captures voice and converts it to text automatically
text_from_voice = speech_to_text(language='en', use_container_width=True, just_once=True, key='STT')
manual_input = st.text_input("Or type your question here:", value=text_from_voice if text_from_voice else "")

final_query = manual_input if manual_input else text_from_voice

if st.button("Run Analysis"):
    if final_query:
        with st.spinner("Analyzing your database..."):
            initial_state = {
                "user_query": final_query,
                "db_schema": schema,
                "generated_sql": "",
                "query_results": "",
                "sql_error": "",
                "explanation": ""
            }

            # Invoke the graph
            result = workflow_app.invoke(initial_state)

            if result["sql_error"]:
                st.error(f"SQL Error: {result['sql_error']}")
            else:
                # 1. Voice Explanation
                st.subheader("Explanation")
                st.write(result["explanation"])
                audio_fp = speak_text(result["explanation"])
                st.audio(audio_fp, format='audio/mp3', autoplay=True)

                # 2. Data Display
                st.subheader("Results")
                try:
                    data = ast.literal_eval(result["query_results"])
                    st.dataframe(pd.DataFrame(data), use_container_width=True)
                except:
                    st.write(result["query_results"])

                # 3. SQL Transparency
                with st.expander("View Generated SQL"):
                    st.code(result["generated_sql"], language="sql")
