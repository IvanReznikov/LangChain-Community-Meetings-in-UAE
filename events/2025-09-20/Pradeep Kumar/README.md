
# Langchain in 60 minutes

Opinionated introduction to Langchain.
Features AI tour guides using OpenAI, LangChain, and related tools with features like conversation memory, tool integration, and LangSmith tracing.

## Project Structure

- **Version1/hello-world.py**: Minimal OpenAI chat example.
- **Version2/talking_guide.py**: LangChain prompt pipeline for a friendly Dubai tour guide.
- **Version3/memory-v1.py / memory-v2.py**: Adds conversation memory to the guide.
- **Version4/tool.py**: LangChain agent with OpenWeatherMap tool.
- **Version5/langsmith-demo.py**: Agent with LangSmith tracing enabled.
- **Version6/server.py**: FastAPI server exposing a /guide endpoint.

## Features

- Uses OpenAI GPT models (e.g., `gpt-4o-mini`) for chat.
- Loads API keys from `.env` files.
- Disables SSL verification for local/demo use (not for production).
- Supports conversation memory and tool integration.
- Web server demo with FastAPI and LangServe.

## Setup

1. Clone this repository.
2. Create a `.env` file in the project root with your API keys:
    ```
    OPENAI_API_KEY=your_openai_api_key_here
    OPENWEATHER_API_KEY=your_openweather_api_key_here
    LANGSMITH_API_KEY=your_langsmith_api_key_here
    ```
3. Install dependencies:
    ```
    pip install -r requirements.txt
    ```

## Usage

### Command-Line Demos

- **Basic Chat:**
   ```
   python Version1/hello-world.py
   ```
- **LangChain Prompt:**
   ```
   python Version2/talking_guide.py
   ```
- **With Memory:**
   ```
   python Version3/memory-v1.py
   python Version3/memory-v2.py
   ```
- **Agent with Tool:**
   ```
   python Version4/tool.py
   ```
- **LangSmith Tracing:**
   ```
   python Version5/langsmith-demo.py
   ```

### FastAPI Server

Start the server:
```
python -m uvicorn Version6.server:app --reload --port 8080
```
Access the guide endpoint at: `http://localhost:8080/guide`

## Security Note

SSL verification is disabled in these demos for local development and testing with self-signed certificates. **Do not use this configuration in production.**

---

**Author:** Pradeep KUmar
