import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.conditions import ExternalTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient

# Create an OpenAI model client.
model_client = OpenAIChatCompletionClient(
    model="gpt-4o-2024-08-06",
    api_key="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", # Optional if you have an OPENAI_API_KEY env variable set.
)

# Create the primary agent.
primary_agent = AssistantAgent(
    "primary",
    model_client=model_client,
    system_message="You are a helpful AI assistant.",
)

# Create the critic agent.
critic_agent = AssistantAgent(
    "critic",
    model_client=model_client,
    system_message="Provide constructive feedback. Respond with 'APPROVE' to when your feedbacks are addressed.",
)

# Define a termination condition that stops the task if the critic approves.
text_termination = TextMentionTermination("APPROVE")

# Create a team with the primary and critic agents.
team = RoundRobinGroupChat([primary_agent, critic_agent], termination_condition=text_termination)



# When running inside a script, use a async main function and call it from `asyncio.run(...)`.
async def main():
    await team.reset()  # Reset the team for a new task.
    await Console(team.run_stream(task="Write a short poem about the fall season."))  # Stream the messages to the console.


if __name__ == "__main__":
    asyncio.run(main())
