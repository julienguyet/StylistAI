from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.genai import types
import os

# ----- DEFINE SYSTEM PROMPT ----- #
file_path = os.path.join(os.path.dirname(__file__), 'system_prompt.txt')

with open(file_path, 'r') as file:
    SYSTEM_PROMPT = file.read()

# ----- DEFINE AGENT ----- #
root_agent = LlmAgent(
    model=LiteLlm(model="anthropic/claude-haiku-4-5"),
    name="Erling",
    instruction=SYSTEM_PROMPT,
    tools=[
        McpToolset(
            connection_params=StreamableHTTPConnectionParams(
                url='http://mcp-server:8001/mcp',
                timeout=120
            ),
        )
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2,
        max_output_tokens=1024,
        safety_settings=[
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            )
        ]
    )
)
