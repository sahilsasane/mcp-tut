import asyncio
import json
from contextlib import AsyncExitStack

import nest_asyncio
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI

nest_asyncio.apply()

load_dotenv()


class MCP_ChatBot:
    def __init__(self):
        self.exit_stack = AsyncExitStack()
        self.openai = OpenAI()
        # Tools list required for Anthropic API
        self.available_tools = []
        # Prompts list for quick display
        self.available_prompts = []
        # Sessions dict maps tool/prompt names or resource URIs to MCP client sessions
        self.sessions = {}

    async def connect_to_server(self, server_name, server_config):
        try:
            server_params = StdioServerParameters(**server_config)
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()

            try:
                # List available tools
                response = await session.list_tools()
                for tool in response.tools:
                    self.sessions[tool.name] = session
                    self.available_tools.append(
                        {
                            "type": "function",
                            "function": {
                                "name": tool.name,
                                "description": tool.description,
                                "parameters": tool.inputSchema,
                            },
                        }
                    )

                # List available prompts
                prompts_response = await session.list_prompts()
                if prompts_response and prompts_response.prompts:
                    for prompt in prompts_response.prompts:
                        self.sessions[prompt.name] = session
                        self.available_prompts.append(
                            {
                                "name": prompt.name,
                                "description": prompt.description,
                                "arguments": prompt.arguments,
                            }
                        )
                # List available resources
                resources_response = await session.list_resources()
                if resources_response and resources_response.resources:
                    for resource in resources_response.resources:
                        resource_uri = str(resource.uri)
                        self.sessions[resource_uri] = session

            except Exception as e:
                print(f"Error {e}")

        except Exception as e:
            print(f"Error connecting to {server_name}: {e}")

    async def connect_to_servers(self):
        try:
            with open("server_config.json", "r") as file:
                data = json.load(file)
            servers = data.get("mcpServers", {})
            for server_name, server_config in servers.items():
                await self.connect_to_server(server_name, server_config)
        except Exception as e:
            print(f"Error loading server config: {e}")
            raise

    async def process_query_anthropic(self, query):
        messages = [{"role": "user", "content": query}]

        while True:
            response = self.anthropic.messages.create(
                max_tokens=2024,
                model="claude-3-7-sonnet-20250219",
                tools=self.available_tools,
                messages=messages,  # type: ignore
            )

            assistant_content = []
            has_tool_use = False

            for content in response.content:
                if content.type == "text":
                    print(content.text)
                    assistant_content.append(content)
                elif content.type == "tool_use":
                    has_tool_use = True
                    assistant_content.append(content)
                    messages.append({"role": "assistant", "content": assistant_content})

                    # Get session and call tool
                    session = self.sessions.get(content.name)
                    if not session:
                        print(f"Tool '{content.name}' not found.")
                        break

                    result = await session.call_tool(
                        content.name, arguments=content.input
                    )
                    messages.append(
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": content.id,
                                    "content": result.content,
                                }
                            ],
                        }
                    )

            # Exit loop if no tool was used
            if not has_tool_use:
                break

    async def process_query(self, query):
        messages = [{"role": "user", "content": query}]
        process_query = True

        while process_query:
            response = self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,  # type: ignore
                tools=self.available_tools,
                tool_choice="auto",
                max_tokens=2024,
            )

            response_message = response.choices[0].message
            messages.append(response_message.model_dump())

            if response_message.tool_calls:
                for tool_call in response_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    tool_id = tool_call.id

                    print(f"Calling tool {tool_name} with args {tool_args}")
                    session = self.sessions.get(tool_name)
                    result = await session.call_tool(tool_name, arguments=tool_args)  # type: ignore

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "content": result.content,
                        }
                    )
            else:
                print(response_message.content)
                process_query = False

    async def get_resource(self, resource_uri):
        session = self.sessions.get(resource_uri)

        # Fallback for Gmail URIs - try any Gmail resource session
        if not session and resource_uri.startswith("gmail://"):
            for uri, sess in self.sessions.items():
                if uri.startswith("gmail://"):
                    session = sess
                    break

        if not session:
            print(f"Resource '{resource_uri}' not found.")
            return

        try:
            result = await session.read_resource(uri=resource_uri)
            if result and result.contents:
                print(f"\nResource: {resource_uri}")
                print("Content:")
                # Handle different content types
                for content in result.contents:
                    if hasattr(content, "text"):
                        print(content.text)
                    else:
                        print(str(content))
            else:
                print("No content available.")
        except Exception as e:
            print(f"Error: {e}")

    async def list_resources(self):
        """List all available resources."""
        gmail_resources = [
            uri for uri in self.sessions.keys() if uri.startswith("gmail://")
        ]

        if not gmail_resources:
            print("No Gmail resources available.")
            return

        print("\nAvailable Gmail resources:")
        print("- meeting-emails: Get recent meeting-related emails")
        print("- processed-meetings: Get processed meeting data")
        print("- meeting-emails/{email_id}: Get specific meeting email by ID")

    async def list_prompts(self):
        """List all available prompts."""
        if not self.available_prompts:
            print("No prompts available.")
            return

        print("\nAvailable prompts:")
        for prompt in self.available_prompts:
            print(f"- {prompt['name']}: {prompt['description']}")
            if prompt["arguments"]:
                print("  Arguments:")
                for arg in prompt["arguments"]:
                    arg_name = arg.name if hasattr(arg, "name") else arg.get("name", "")
                    print(f"    - {arg_name}")

    async def execute_prompt(self, prompt_name, args):
        """Execute a prompt with the given arguments."""
        session = self.sessions.get(prompt_name)
        if not session:
            print(f"Prompt '{prompt_name}' not found.")
            return

        try:
            result = await session.get_prompt(prompt_name, arguments=args)
            if result and result.messages:
                prompt_content = result.messages[0].content

                # Extract text from content (handles different formats)
                if isinstance(prompt_content, str):
                    text = prompt_content
                elif hasattr(prompt_content, "text"):
                    text = prompt_content.text
                else:
                    # Handle list of content items
                    text = " ".join(
                        item.text if hasattr(item, "text") else str(item)
                        for item in prompt_content
                    )

                print(f"\nExecuting prompt '{prompt_name}'...")
                await self.process_query(text)
        except Exception as e:
            print(f"Error: {e}")

    async def chat_loop(self):
        print("\nMCP Chatbot Started!")
        print("Type your queries or 'quit' to exit.")
        print("Available commands:")
        print("- @meeting-emails: Get recent meeting-related emails")
        print("- @processed-meetings: Get processed meeting data")
        print("- @meeting-emails/<email_id>: Get specific meeting email by ID")
        print("- /resources: List available resources")
        print("- /prompts: List available prompts")
        print("- /prompt <name> <arg1=value1>: Execute a prompt")

        while True:
            try:
                query = input("\nQuery: ").strip()
                if not query:
                    continue

                if query.lower() == "quit":
                    break

                # Check for @resource syntax first
                if query.startswith("@"):
                    # Remove @ sign
                    resource_identifier = query[1:]

                    if resource_identifier == "meeting-emails":
                        resource_uri = "gmail://meeting-emails"
                    elif resource_identifier == "processed-meetings":
                        resource_uri = "gmail://processed-meetings"
                    elif resource_identifier.startswith("meeting-emails/"):
                        # Extract email ID from meeting-emails/email_id
                        email_id = resource_identifier.split("/", 1)[1]
                        resource_uri = f"gmail://meeting-emails/{email_id}"
                    else:
                        print(f"Unknown resource: {resource_identifier}")
                        print(
                            "Available resources: meeting-emails, processed-meetings, meeting-emails/<email_id>"
                        )
                        continue

                    await self.get_resource(resource_uri)
                    continue

                # Check for /command syntax
                if query.startswith("/"):
                    parts = query.split()
                    command = parts[0].lower()

                    if command == "/resources":
                        await self.list_resources()
                    elif command == "/prompts":
                        await self.list_prompts()
                    elif command == "/prompt":
                        if len(parts) < 2:
                            print("Usage: /prompt <name> <arg1=value1> <arg2=value2>")
                            continue

                        prompt_name = parts[1]
                        args = {}

                        # Parse arguments
                        for arg in parts[2:]:
                            if "=" in arg:
                                key, value = arg.split("=", 1)
                                args[key] = value

                        await self.execute_prompt(prompt_name, args)
                    else:
                        print(f"Unknown command: {command}")
                        print("Available commands: /resources, /prompts, /prompt")
                    continue

                await self.process_query(query)

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        await self.exit_stack.aclose()


async def main():
    chatbot = MCP_ChatBot()
    try:
        await chatbot.connect_to_servers()
        await chatbot.chat_loop()
    finally:
        await chatbot.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
