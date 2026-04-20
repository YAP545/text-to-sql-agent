import streamlit as st
import pandas as pd
import sqlite3
import ast
from workflow import create_workflow

st.set_page_config(page_title="AI SQL Agent", page_icon="🤖", layout="wide")

# --- Initialize Workflow ---
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
    st.write("Upload an SQLite database to analyze.")
    uploaded_file = st.file_uploader("Upload a .db or .sqlite file", type=["db", "sqlite"])
    
    if uploaded_file:
        # Save uploaded file locally for the workflow to access
        with open("temp_db.db", "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success("Database Loaded Successfully!")
        schema = get_schema_from_uploaded_file("temp_db.db")
        
        st.subheader("Detected Schema")
        st.code(schema, language="sql")
    else:
        st.warning("Please upload a database file to begin.")
        st.stop()

# --- Main UI ---
st.title("Autonomous Text-to-SQL Agent 🤖📊")
st.markdown("Ask natural language questions about your uploaded database, and the agent will write, execute, and explain the SQL.")

user_query = st.text_input("Ask a question about your data:")

if st.button("Run Analytics Engine"):
    # Security check
    if not st.secrets.get("GROQ_API_KEY"):
        st.error("Please add your GROQ_API_KEY to the Streamlit Secrets manager!")
        st.stop()

    if user_query:
        with st.spinner("Agent is analyzing the schema and processing your query..."):
            initial_state = {
                "user_query": user_query,
                "db_schema": schema,
                "generated_sql": "",
                "query_results": "",
                "sql_error": "",
                "explanation": ""
            }

            try:
                result = workflow_app.invoke(initial_state)
            except Exception as e:
                st.error(f"Agent crashed: {e}")
                st.stop()

            # Display Error if SQL failed
            if result["sql_error"]:
                st.error(f"SQL Execution Error: {result['sql_error']}")
                with st.expander("View Failed SQL"):
                    st.code(result["generated_sql"], language="sql")
            else:
                # Layout for successful results
                st.subheader("Agent Explanation")
                st.info(result["explanation"])

                st.subheader("Data Results")
                try:
                    data = ast.literal_eval(result["query_results"])
                    if data:
                        st.dataframe(pd.DataFrame(data), use_container_width=True)
                    else:
                        st.write("Query executed successfully, but returned no data.")
                except:
                    st.write(result["query_results"])

                with st.expander("View Generated SQL"):
                    st.code(result["generated_sql"], language="sql")
    else:
        st.warning("Please enter a question first.")
