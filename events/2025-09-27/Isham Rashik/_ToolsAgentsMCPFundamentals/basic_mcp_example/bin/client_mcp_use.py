import asyncio
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from mcp_use import MCPAgent, MCPClient

async def main():
    load_dotenv()
    client = MCPClient.from_config_file("mcpServers.json")
    llm = ChatOpenAI(model="gpt-4.1")
    agent = MCPAgent(llm=llm, client=client, max_steps=30)

    collected = []

    async for chunk in agent.stream("What is the present price of Tesla stock?"):
        # Extract printable text robustly from different chunk shapes
        def emit_text(text):
            if text:
                collected.append(text)
                print(text, end="", flush=True)

        try:
            # Direct strings
            if isinstance(chunk, str):
                emit_text(chunk)
                continue

            # Dict-shaped chunks
            if isinstance(chunk, dict):
                # Common fields
                for key in ("content", "messages", "text", "token", "delta"):
                    val = chunk.get(key)
                    if isinstance(val, str):
                        emit_text(val)
                        break
                else:
                    # Sometimes the content is nested (e.g., {'message_log': [AIMessageChunk(...)]})
                    msg_log = chunk.get("message_log") or chunk.get("messages")
                    if isinstance(msg_log, (list, tuple)):
                        for msg in msg_log:
                            if hasattr(msg, "content") and isinstance(msg.content, str):
                                emit_text(msg.content)
                    log_field = chunk.get("log")
                    if isinstance(log_field, str):
                        emit_text(log_field)
                continue

            # Tuple-shaped chunks (e.g., (token, meta))
            if isinstance(chunk, tuple):
                for el in chunk:
                    if isinstance(el, str):
                        emit_text(el)
                    elif hasattr(el, "content") and isinstance(getattr(el, "content"), str):
                        emit_text(el.content)
                continue

            # Objects with a 'content' attr (e.g., LangChain Message/Chunk)
            if hasattr(chunk, "content") and isinstance(getattr(chunk, "content"), str):
                emit_text(chunk.content)
                continue
        except Exception as e:
            # Don't crash on unexpected shapes; emit a minimal notice once
            if not collected:
                print(f"[stream parsing error: {e}]\n", flush=True)

    # If nothing was streamed, fall back to a single-shot invoke
    if not collected:
        try:
            result = await agent.ainvoke("What is the present price of Tesla stock?")
            # Handle common result shapes
            if isinstance(result, str):
                print(result)
            elif isinstance(result, dict):
                out = result.get("output") or result.get("content") or result.get("text")
                if isinstance(out, str):
                    print(out)
                else:
                    print(str(result))
            elif hasattr(result, "content") and isinstance(getattr(result, "content"), str):
                print(result.content)
            else:
                print(str(result))
        except Exception as e:
            print(f"[fallback invoke failed: {e}]")
    else:
        print()  # final newline after stream completes when we did stream something

if __name__ == "__main__":
    asyncio.run(main())