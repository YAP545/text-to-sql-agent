import sqlite3
import streamlit as st
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

# Define the State passing between agents
class AgentState(TypedDict):
    user_query: str
    db_schema: str
    generated_sql: str
    query_results: str
    sql_error: str
    explanation: str

def generate_sql_node(state: AgentState):
    try:
        llm = ChatGroq(
            model="llama-3.1-8b-instant",
            groq_api_key=st.secrets["GROQ_API_KEY"],
            temperature=0
        )

        # The strict, anti-hallucination prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert SQLite Database Administrator. You MUST adhere strictly to these rules:
            1. ONLY use the exact tables and columns provided in the Schema below. Pay attention to plural vs singular names.
            2. NEVER invent, guess, or hallucinate table names or columns.
            3. If a question requires data from multiple tables, use INNER JOINs based on the foreign keys in the schema.
            4. Return ONLY the raw SQL query. No markdown, no explanation, no backticks."""),
            ("user", "Schema:\n{schema}\n\nQuestion: {query}")
        ])

        chain = prompt | llm
        response = chain.invoke({
            "schema": state["db_schema"],
            "query": state["user_query"]
        })

        # Clean the SQL output to prevent execution errors
        sql = response.content.strip().replace("```sql", "").replace("```", "").replace(";", "")
        return {"generated_sql": sql, "sql_error": ""}

    except Exception as e:
        return {"generated_sql": "", "sql_error": str(e)}

def execute_sql_node(state: AgentState):
    # Connects to the uploaded database file
    conn = sqlite3.connect("temp_db.db")
    cursor = conn.cursor()
    try:
        cursor.execute(state["generated_sql"])
        result = cursor.fetchall()
        conn.close()
        return {"query_results": str(result), "sql_error": ""}
    except Exception as e:
        conn.close()
        return {"query_results": "", "sql_error": str(e)}

def explain_sql_node(state: AgentState):
    try:
        llm = ChatGroq(
            model="llama-3.1-8b-instant",
            groq_api_key=st.secrets["GROQ_API_KEY"],
            temperature=0.7
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a friendly data analyst. Explain the SQL results simply for a non-technical user. Do not mention the SQL code itself, just summarize the data."),
            ("user", "Question: {query}\nSQL used: {sql}\nResult from DB: {result}")
        ])

        chain = prompt | llm
        response = chain.invoke({
            "query": state["user_query"],
            "sql": state["generated_sql"],
            "result": state["query_results"]
        })

        return {"explanation": response.content}

    except Exception as e:
        return {"explanation": str(e)}

def create_workflow():
    workflow = StateGraph(AgentState)

    workflow.add_node("generate", generate_sql_node)
    workflow.add_node("execute", execute_sql_node)
    workflow.add_node("explain", explain_sql_node)

    workflow.set_entry_point("generate")
    workflow.add_edge("generate", "execute")
    workflow.add_edge("execute", "explain")
    workflow.add_edge("explain", END)

    return workflow.compile()
