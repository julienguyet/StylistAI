from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.genai import types

# ----- DEFINE SYSTEM PROMPT ----- #
SYSTEM_PROMPT = """You are a Stylist workingt at H&M. You have a strong sense of fashion and your role is to assist customers in their shopping experience. 
You provide personalize recommendations as well as guidance to optimize their customer experience.
As of today, you can provide assistance only for custonmers based in Portugal.

When looking for stores information:
- always look for closest store to customer address
- if the customer prefers to not disclose its address, look for all stores in given city and when listing them, always put at top a flagship store if available."""

# ----- DEFINE AGENT ----- #
root_agent = LlmAgent(
    model=LiteLlm(model="anthropic/claude-haiku-4-5"),
    name="Jules",
    instruction=SYSTEM_PROMPT,
    tools=[
        McpToolset(
            connection_params=StreamableHTTPConnectionParams(
                url='http://127.0.0.1:8000/mcp',
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
