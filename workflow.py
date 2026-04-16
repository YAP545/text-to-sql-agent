import sqlite3
import streamlit as st
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

# 1. Define the State (Data structure passed between nodes)
class AgentState(TypedDict):
    user_query: str
    db_schema: str
    generated_sql: str
    query_results: str
    sql_error: str
    explanation: str

# 2. Node: Generate SQL using Llama-3
def generate_sql_node(state: AgentState):
    # Initialize Groq LLM
    llm = ChatGroq(
        model="llama3-8b-8192", 
        groq_api_key=st.secrets["GROQ_API_KEY"],
        temperature=0
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert SQL Developer. Given the database schema, write a valid SQLite query to answer the user's question. Return ONLY the raw SQL code. No markdown, no backticks, no 'sql' prefix."),
        ("user", "Schema:\n{schema}\n\nQuestion: {query}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({"schema": state["db_schema"], "query": state["user_query"]})
    
    # Clean up the output just in case
    clean_sql = response.content.strip().replace("```sql", "").replace("```", "").replace(";", "")
    return {"generated_sql": clean_sql}

# 3. Node: Execute the SQL against the local DB
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

# 4. Node: Explain the results
def explain_sql_node(state: AgentState):
    llm = ChatGroq(
        model="llama3-8b-8192", 
        groq_api_key=st.secrets["GROQ_API_KEY"],
        temperature=0.7
    )
    
    if state["sql_error"]:
        return {"explanation": f"I encountered an error: {state['sql_error']}"}
        
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a data analyst. Explain the SQL logic used and summarize the results found in simple terms."),
        ("user", "Question: {query}\nSQL used: {sql}\nData found: {results}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({
        "query": state["user_query"],
        "sql": state["generated_sql"],
        "results": state["query_results"]
    })
    return {"explanation": response.content}

# 5. Connect the Graph
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
