import streamlit as st
import pandas as pd
import ast
from database import setup_mock_database, get_database_schema
from workflow import create_workflow

st.set_page_config(page_title="AI SQL Agent", page_icon="🤖")

st.title("Autonomous Text-to-SQL Agent 🤖📊")

@st.cache_resource
def init_system():
    db_name = setup_mock_database()
    schema = get_database_schema(db_name)
    app = create_workflow()
    return schema, app

schema, workflow_app = init_system()

with st.sidebar:
    st.header("Database Schema")
    st.code(schema, language="sql")

user_query = st.text_input("Ask your question:")

if st.button("Run"):
    if not st.secrets.get("GROQ_API_KEY"):
        st.error("Missing API Key")
        st.stop()

    if user_query:
        with st.spinner("Processing..."):
            initial_state = {
                "user_query": user_query,
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
                st.write(result["explanation"])
                st.dataframe(pd.DataFrame(ast.literal_eval(result["query_results"])))
                st.code(result["generated_sql"], language="sql")
