# Simple AI Agent Demo

A basic ReAct-style AI agent implementation using LangChain.

## Features

The agent has 7 built-in tools:
- **Calculator**: Performs mathematical calculations
- **Search**: Simulates web search (returns mock data for demo)
- **TakeNote**: Stores notes in memory
- **ReadNotes**: Retrieves all stored notes
- **QueryDatabase**: Execute SQL queries on PostgreSQL database
- **ListDatabaseTables**: List all tables in the database
- **DescribeTable**: Get schema/structure of a specific table

## Installation

```bash
pip install -r requirements-agent.txt
```

## Usage

Set your OpenAI API key:
```bash
export OPENAI_API_KEY='your-api-key-here'
```

**Optional:** Configure PostgreSQL connection (defaults to localhost):
```bash
export POSTGRES_HOST='localhost'
export POSTGRES_PORT='5432'
export POSTGRES_DB='postgres'
export POSTGRES_USER='postgres'
export POSTGRES_PASSWORD='your-password'
```

Run the agent:
```bash
python simple_agent.py
```

## How It Works

The agent uses the **ReAct pattern** (Reasoning + Acting):
1. **Thought**: Agent reasons about what to do
2. **Action**: Agent selects a tool to use
3. **Action Input**: Agent provides input to the tool
4. **Observation**: Agent sees the result
5. Repeat until answer is found

## Example Queries

The demo runs these example queries:
- "What is 15 multiplied by 23?"
- "Search for information about Python"
- "Take a note: Meeting scheduled for Monday at 2pm"
- "What notes have I saved?"
- "Calculate 100 divided by 4, then multiply the result by 3"
- "List all tables in the database"
- "Describe the structure of the users table"

## Database Queries

You can ask the agent to interact with your PostgreSQL database:
- **List tables**: "Show me all tables in the database"
- **Describe schema**: "What columns does the users table have?"
- **Query data**: "Get the first 5 users from the users table"
- **Count records**: "How many orders are in the orders table?"
- **Complex queries**: "Find all active users who registered in the last month"

## Customization

To add your own tools, create a function with the `@tool` decorator:

```python
@tool
def my_tool(input: str) -> str:
    """Your tool description. This tells the agent when and how to use the tool."""
    # Your logic here
    return "result"

# Add to tools list
tools.append(my_tool)
```

### PostgreSQL Tool Examples

The database tools demonstrate how to:
1. **Manage connections**: Using environment variables for configuration
2. **Handle different query types**: SELECT vs INSERT/UPDATE/DELETE
3. **Format results**: Return structured data in readable format
4. **Error handling**: Catch and return database-specific errors

## Architecture

```
┌─────────────┐
│    User     │
│   Query     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   ReAct     │
│   Agent     │◄──── LLM (GPT-4o-mini)
└──────┬──────┘
       │
       ▼
┌─────────────────────────┐
│        Tools            │
├─────────────────────────┤
│ • Calculator            │
│ • Search                │
│ • TakeNote             │
│ • ReadNotes            │
└─────────────────────────┘
```
