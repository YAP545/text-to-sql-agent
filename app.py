import streamlit as st
import pandas as pd
import ast
import os
import sqlite3
from streamlit_mic_recorder import mic_recorder
from workflow import create_workflow
from audio_handler import transcribe_audio, get_audio_file

st.set_page_config(page_title="Neural Data Analyst", page_icon="🎙️", layout="wide")

@st.cache_resource
def get_workflow():
    return create_workflow()

workflow_app = get_workflow()

def get_schema_from_uploaded_file(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';")
    schema = "\n".join([row[0] for row in cursor.fetchall() if row[0]])
    conn.close()
    return schema

# --- Sidebar: Database Upload ---
with st.sidebar:
    st.header("📂 Upload Database")
    uploaded_file = st.file_uploader("Upload an SQLite file (.db)", type=["db", "sqlite"])
    
    if uploaded_file:
        with open("temp_db.db", "wb") as f:
            f.write(uploaded_file.getbuffer())
        schema = get_schema_from_uploaded_file("temp_db.db")
        st.success("Database Loaded!")
        st.subheader("Detected Schema")
        st.code(schema, language="sql")
    else:
        st.warning("Please upload a .db file to begin.")
        st.stop()

# --- Main UI ---
st.title("Neural Voice SQL Agent 🎙️🧠")
st.markdown("Speak to your database. Powered by Llama-3, Whisper-v3, and Neural TTS.")

if not st.secrets.get("GROQ_API_KEY"):
    st.error("GROQ_API_KEY missing in Secrets manager!")
    st.stop()

col1, col2 = st.columns([1, 3])

with col1:
    st.subheader("Voice Input")
    audio_info = mic_recorder(start_prompt="🎤 Record", stop_prompt="🛑 Stop", key='mic')

with col2:
    st.subheader("Data Terminal")
    
    user_query = None
    if audio_info:
        with st.spinner("Transcribing with Whisper-v3..."):
            user_query = transcribe_audio(audio_info['bytes'])
            st.success(f"**Heard:** {user_query}")
    
    manual_query = st.text_input("Or type your question manually:", value=user_query if user_query else "")
    final_query = manual_query or user_query

    if st.button("Run Neural Analysis") and final_query:
        with st.spinner("Processing Data Pipeline..."):
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
                st.error(f"SQL Error: {result['sql_error']}")
            else:
                # Play Audio
                audio_path = get_audio_file(result["explanation"])
                st.audio(audio_path, format="audio/mp3", autoplay=True)
                try:
                    os.remove(audio_path)
                except Exception:
                    pass

                # Display Results
                st.info(f"🤖 **Agent:** {result['explanation']}")
                
                st.subheader("Database Results")
                try:
                    data = ast.literal_eval(result["query_results"])
                    if data:
                        st.dataframe(pd.DataFrame(data), use_container_width=True)
                except:
                    st.write(result["query_results"])

                with st.expander("View Backend SQL"):
                    st.code(result["generated_sql"], language="sql")
