import sqlite3
import streamlit as st
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

class AgentState(TypedDict):
    user_query: str
    db_schema: str
    generated_sql: str
    query_results: str
    sql_error: str
    explanation: str


def generate_sql_node(state: AgentState):
    llm = ChatGroq(
        model="llama3-8b-8192",
        groq_api_key=st.secrets["GROQ_API_KEY"],
        temperature=0
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", "Write only SQL query."),
        ("user", "Schema:\n{schema}\n\nQuestion: {query}")
    ])

    chain = prompt | llm
    response = chain.invoke({
        "schema": state["db_schema"],
        "query": state["user_query"]
    })

    sql = response.content.strip().replace("```", "")
    return {"generated_sql": sql}


def execute_sql_node(state: AgentState):
    conn = sqlite3.connect("company.db")
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
    llm = ChatGroq(
        model="llama3-8b-8192",
        groq_api_key=st.secrets["GROQ_API_KEY"]
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", "Explain simply."),
        ("user", "SQL: {sql}, Result: {result}")
    ])

    chain = prompt | llm
    response = chain.invoke({
        "sql": state["generated_sql"],
        "result": state["query_results"]
    })

    return {"explanation": response.content}


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
