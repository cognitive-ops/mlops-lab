"""
Simple AI Agent using LangChain and LangGraph.

This agent has basic tools for:
- Calculator operations
- Web search simulation
- File operations
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent as create_langchain_agent


# Tool 1: Calculator
@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression. Input should be a valid Python expression like '2+2' or '10*5'."""
    try:
        # Safe evaluation of simple math expressions
        result = eval(expression, {"__builtins__": {}}, {})
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {str(e)}"


# Tool 2: Simple search simulator
@tool
def search(query: str) -> str:
    """Simulate a web search (returns mock data). Input should be a search query about weather, python, or ai."""
    mock_results = {
        "weather": "Today's weather is sunny with a high of 75°F.",
        "python": "Python is a high-level programming language known for its simplicity.",
        "ai": "Artificial Intelligence is the simulation of human intelligence by machines.",
    }

    for keyword, result in mock_results.items():
        if keyword.lower() in query.lower():
            return result

    return f"No specific results found for '{query}'. Try: weather, python, or ai."


# Tool 3: Note taking
notes_storage = []


@tool
def take_note(note: str) -> str:
    """Store a note in memory. Input should be the note text you want to save."""
    notes_storage.append(note)
    return f"Note saved: '{note}' (Total notes: {len(notes_storage)})"


@tool
def read_notes() -> str:
    """Read all stored notes. No input required."""
    if not notes_storage:
        return "No notes stored yet."
    return "Stored notes:\n" + "\n".join(f"{i+1}. {note}" for i, note in enumerate(notes_storage))


# Tool 4: PostgreSQL Database Query
def get_db_connection():
    """Get PostgreSQL database connection."""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        database=os.getenv("POSTGRES_DB", "postgres"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "")
    )


@tool
def query_database(sql_query: str) -> str:
    """Execute a SQL query on the PostgreSQL database and return results. 
    Input should be a valid SQL query string (SELECT, INSERT, UPDATE, DELETE).
    Examples: 'SELECT * FROM users LIMIT 5', 'SELECT COUNT(*) FROM orders WHERE status=\'completed\''
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(sql_query)

        # Check if it's a SELECT query
        if sql_query.strip().upper().startswith('SELECT'):
            results = cursor.fetchall()
            if not results:
                return "Query executed successfully. No rows returned."

            # Format results as a table
            if len(results) > 10:
                results = results[:10]
                truncated = True
            else:
                truncated = False

            output = f"Found {len(results)} rows:\n\n"
            for i, row in enumerate(results, 1):
                output += f"Row {i}:\n"
                for key, value in row.items():
                    output += f"  {key}: {value}\n"
                output += "\n"

            if truncated:
                output += "(Results truncated to 10 rows)\n"

            cursor.close()
            conn.close()
            return output
        else:
            # For INSERT, UPDATE, DELETE
            conn.commit()
            rows_affected = cursor.rowcount
            cursor.close()
            conn.close()
            return f"Query executed successfully. {rows_affected} row(s) affected."

    except psycopg2.Error as e:
        return f"Database error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def list_database_tables() -> str:
    """List all tables in the PostgreSQL database. No input required."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)

        tables = cursor.fetchall()
        cursor.close()
        conn.close()

        if not tables:
            return "No tables found in the database."

        table_list = "\n".join([f"- {table[0]}" for table in tables])
        return f"Available tables:\n{table_list}"

    except psycopg2.Error as e:
        return f"Database error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def describe_table(table_name: str) -> str:
    """Get the schema/structure of a specific database table. 
    Input should be the table name.
    Example: 'users', 'orders', 'products'
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT column_name, data_type, character_maximum_length, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position;
        """, (table_name,))

        columns = cursor.fetchall()
        cursor.close()
        conn.close()

        if not columns:
            return f"Table '{table_name}' not found or has no columns."

        output = f"Table: {table_name}\n\n"
        output += "Columns:\n"
        for col in columns:
            col_name, data_type, max_length, nullable, default = col
            output += f"  - {col_name}: {data_type}"
            if max_length:
                output += f"({max_length})"
            output += f" | Nullable: {nullable}"
            if default:
                output += f" | Default: {default}"
            output += "\n"

        return output

    except psycopg2.Error as e:
        return f"Database error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"


# Define tools list
tools = [calculator, search, take_note, read_notes,
         query_database, list_database_tables, describe_table]


def create_agent(api_key: str = None, model: str = "gpt-4o-mini"):
    """Create and return a ReAct agent using LangGraph."""

    # Initialize LLM
    llm = ChatOpenAI(
        model=model,
        temperature=0,
        api_key=api_key or os.getenv("OPENAI_API_KEY")
    )

    # Create agent using LangChain's create_agent
    agent_executor = create_langchain_agent(llm, tools)

    return agent_executor


def main():
    """Run the agent with example queries."""

    print("=" * 80)
    print("Simple AI Agent Demo")
    print("=" * 80)

    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n⚠️  Warning: OPENAI_API_KEY not set in environment variables.")
        print("Please set it with: export OPENAI_API_KEY='your-key-here'\n")
        return

    # Create agent
    agent = create_agent()

    # Example queries
    queries = [
        "What is 15 multiplied by 23?",
        "Search for information about Python",
        "Take a note: Meeting scheduled for Monday at 2pm",
        "Take a note: Buy groceries - milk, eggs, bread",
        "What is the weather like today?",
        "Calculate 100 divided by 4, then multiply the result by 3",
        "List all tables in the database",
        "Describe the structure of the users table",
    ]

    for i, query in enumerate(queries, 1):
        print(f"\n{'=' * 80}")
        print(f"Query {i}: {query}")
        print('=' * 80)

        try:
            response = agent.invoke({"messages": [("user", query)]})
            # Extract final answer from messages
            final_message = response["messages"][-1]
            if hasattr(final_message, "content"):
                answer = final_message.content
            else:
                answer = str(final_message)
            print(f"\n✅ Final Answer: {answer}\n")
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")

    print("=" * 80)
    print("Demo completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
