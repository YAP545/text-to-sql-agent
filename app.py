import streamlit as st
import pandas as pd
import ast
from database import setup_mock_database, get_database_schema
from workflow import create_workflow

st.set_page_config(page_title="AI SQL Agent", page_icon="🤖", layout="centered")
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

user_query = st.text_input("What would you like to know?", placeholder="e.g., Which sales employee brought in the most revenue?")

if st.button("Run Analytics Engine"):
    if not st.secrets.get("GROQ_API_KEY"):
        st.error("GROQ_API_KEY missing in Secrets manager!")
        st.stop()

    if user_query:
        with st.spinner("Llama-3 is analyzing and writing SQL..."):
            initial_state = {
                "user_query": user_query, "db_schema": schema, "generated_sql": "",
                "query_results": "", "sql_error": "", "explanation": ""
            }
            
            final_state = workflow_app.invoke(initial_state)
            
            if final_state["sql_error"]:
                st.error(f"Error: {final_state['sql_error']}")
            else:
                tab1, tab2, tab3 = st.tabs(["Explanation", "Data Table", "Raw SQL"])
                with tab1:
                    st.write(final_state["explanation"])
                with tab2:
                    try:
                        results_list = ast.literal_eval(final_state["query_results"])
                        st.dataframe(pd.DataFrame(results_list), use_container_width=True)
                    except:
                        st.write(final_state["query_results"])
                with tab3:
                    st.code(final_state["generated_sql"], language="sql")
