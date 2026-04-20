import sqlite3
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
    try:
        llm = ChatGroq(
            model="llama-3.1-8b-instant",   # ✅ FINAL WORKING MODEL
            groq_api_key="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",
            temperature=0
        )

        # ✅ FIX: Stricter prompt to prevent table name hallucinations
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert SQL Developer. You MUST strictly use the exact table and column names provided in the Schema below. 
            Pay close attention to plural vs singular names (e.g., 'students' vs 'Student'). 
            Return ONLY the raw SQLite query. No markdown, no backticks, no 'sql' prefix."""),
            ("user", "Schema:\n{schema}\n\nQuestion: {query}")
        ])

        chain = prompt | llm
        response = chain.invoke({
            "schema": state["db_schema"],
            "query": state["user_query"]
        })

        # ✅ FIX: Clean up markdown blocks so SQLite doesn't crash
        sql = response.content.strip().replace("```sql", "").replace("```", "").replace(";", "")
        return {"generated_sql": sql, "sql_error": ""}

    except Exception as e:
        return {"generated_sql": "", "sql_error": str(e)}


def execute_sql_node(state: AgentState):
    # ✅ FIX: Changed to temp_db.db to support the file uploader we built
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
            model="llama-3.1-8b-instant",   # ✅ SAME FIX HERE
            groq_api_key="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"
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", "Explain the SQL results simply for a non-technical user."),
            ("user", "Question: {query}\nSQL: {sql}\nResult: {result}")
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
