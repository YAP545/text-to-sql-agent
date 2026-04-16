import sqlite3
import streamlit as st
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

# 1. Define the State
class AgentState(TypedDict):
    user_query: str
    db_schema: str
    generated_sql: str
    query_results: str
    sql_error: str
    explanation: str

# 2. Define the Nodes
def generate_sql_node(state: AgentState):
    # Using Groq Llama 3
    llm = ChatGroq(model="llama3-8b-8192", groq_api_key=st.secrets["GROQ_API_KEY"])
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert Database Administrator. Given the schema, write a highly optimized SQLite query. Return ONLY the raw SQL query, no markdown.\n\nSchema:\n{schema}"),
        ("user", "{query}")
    ])
    chain = prompt | llm
    response = chain.invoke({"schema": state["db_schema"], "query": state["user_query"]})
    return {"generated_sql": response.content.strip().replace("```sql", "").replace("```", "")}

def execute_sql_node(state: AgentState):
    conn = sqlite3.connect("company.db")
    cursor = conn.cursor()
    try:
        cursor.execute(state["generated_sql"])
        results = cursor.fetchall()
        conn.close()
        return {"query_results": str(results), "sql_error": ""}
    except Exception as e:
        conn.close()
        return {"query_results": "", "sql_error": str(e)}

def explain_sql_node(state: AgentState):
    llm = ChatGroq(model="llama3-8b-8192", groq_api_key=st.secrets["GROQ_API_KEY"])
    
    if state["sql_error"]:
        return {"explanation": f"Failed to execute query: {state['sql_error']}"}
        
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a data educator. Explain WHY this specific SQL query was written and what the results mean for a non-technical user."),
        ("user", "Question: {query}\nSQL: {sql}\nResults: {results}")
    ])
    chain = prompt | llm
    response = chain.invoke({
        "query": state["user_query"],
        "sql": state["generated_sql"],
        "results": state["query_results"]
    })
    return {"explanation": response.content}

# 3. Build and Compile the Graph
def create_workflow():
    workflow = StateGraph(AgentState)
    workflow.add_node("generate_sql", generate_sql_node)
    workflow.add_node("execute_sql", execute_sql_node)
    workflow.add_node("explain_sql", explain_sql_node)

    workflow.set_entry_point("generate_sql")
    workflow.add_edge("generate_sql", "execute_sql")
    workflow.add_edge("execute_sql", "explain_sql")
    workflow.add_edge("explain_sql", END)
    
    return workflow.compile()
