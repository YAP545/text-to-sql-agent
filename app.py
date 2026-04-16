import streamlit as st
import pandas as pd
import ast
from database import setup_mock_database, get_database_schema
from workflow import create_workflow

st.set_page_config(page_title="AI SQL Agent", page_icon="🤖", layout="centered")
st.title("Autonomous Text-to-SQL Agent 🤖📊")
st.markdown("Ask natural language questions about your database, and let the agent write, execute, and explain the SQL.")

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
    # UPDATED: Now checking for the Groq key instead of Google
    if not st.secrets.get("GROQ_API_KEY"):
        st.error("Please add your GROQ_API_KEY to the Streamlit Secrets manager!")
        st.stop()

    if user_query:
        with st.spinner("Agent is analyzing schema and writing SQL..."):
            initial_state = {
                "user_query": user_query, "db_schema": schema, "generated_sql": "",
                "query_results": "", "sql_error": "", "explanation": ""
            }
            
            final_state = workflow_app.invoke(initial_state)
            
            if final_state["sql_error"]:
                st.error(f"Error executing SQL: {final_state['sql_error']}")
            else:
                tab1, tab2, tab3 = st.tabs(["Explanation", "Data Table", "Raw SQL"])
                
                with tab1:
                    st.subheader("Agent Explanation")
                    st.write(final_state["explanation"])
                
                with tab2:
                    st.subheader("Query Results")
                    try:
                        results_list = ast.literal_eval(final_state["query_results"])
                        if results_list:
                             df = pd.DataFrame(results_list)
                             st.dataframe(df, use_container_width=True)
                        else:
                             st.info("Query executed successfully, but returned no data.")
                    except Exception:
                        st.write(final_state["query_results"])
                
                with tab3:
                    st.subheader("Generated SQL")
                    st.code(final_state["generated_sql"], language="sql")
    else:
        st.warning("Please enter a question first!")
