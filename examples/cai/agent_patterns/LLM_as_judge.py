"""
LLM as a Judge Pattern

Uses one LLM to perform a task and another to evaluate the result and provide feedback.
The loop continues until the evaluator is satisfied. This improves output quality
and allows cost optimization by combining smaller and larger models.
"""

from __future__ import annotations

import asyncio
import os
import json
from dataclasses import dataclass
from typing import Literal
from cai.sdk.agents import Agent, ItemHelpers, Runner, TResponseInputItem, OpenAIChatCompletionsModel
from openai import AsyncOpenAI
from cai.util import get_ollama_api_base

# Enable debug mode
#os.environ['CAI_DEBUG'] = '2'
#os.environ['LITELLM_VERBOSE'] = 'True'

# Force Ollama mode if qwen model is used
if os.getenv('CAI_MODEL', "qwen2.5:14b").startswith("qwen"): 
    os.environ['OLLAMA'] = 'true'

# Modify OpenAIChatCompletionsModel._fetch_response_litellm_ollama to debug output
import cai.sdk.agents.models.openai_chatcompletions
original_fetch_response_litellm_ollama = cai.sdk.agents.models.openai_chatcompletions.OpenAIChatCompletionsModel._fetch_response_litellm_ollama

async def debug_fetch_response_litellm_ollama(self, kwargs, model_settings, tool_choice, stream, parallel_tool_calls):
    print("\n[DEBUG] Ollama request parameters:")
    print(f"Base URL: {get_ollama_api_base().rstrip('/v1')}")
    print(f"Model name: {kwargs.get('model')}")
    print(f"Messages: {json.dumps(kwargs.get('messages'))[:200]}...") # Truncated to avoid huge output
    
    # Check if the model exists in Ollama
    import requests
    try:
        response = requests.get(f"{get_ollama_api_base().rstrip('/v1')}/api/tags")
        models = response.json().get("models", [])
        model_names = [model.get("name") for model in models]
        print(f"Available Ollama models: {model_names}")
        
        model_name = kwargs.get('model')
        if model_name in model_names:
            print(f"✅ Model '{model_name}' is available in Ollama")
        else:
            print(f"❌ Model '{model_name}' is NOT available in Ollama")
            similar_models = [name for name in model_names if model_name.split(":")[0] in name]
            if similar_models:
                print(f"Similar models available: {similar_models}")
                
                # Try with first similar model
                if similar_models:
                    print(f"⚠️ Trying with similar model: {similar_models[0]}")
                    kwargs["model"] = similar_models[0]
    except Exception as e:
        print(f"Error checking Ollama models: {e}")
    
    # Call the original function
    return await original_fetch_response_litellm_ollama(self, kwargs, model_settings, tool_choice, stream, parallel_tool_calls)

# Patch the function
cai.sdk.agents.models.openai_chatcompletions.OpenAIChatCompletionsModel._fetch_response_litellm_ollama = debug_fetch_response_litellm_ollama

# CTF task planner agent (performs planning)
ctf_task_planner = Agent(
    name="CTF Task Planner",
    description="Agent focused on creating a task plan to approach a CTF challenge.",
    instructions=(
        "You are a cybersecurity strategist. Given a CTF challenge description, "
        "generate a clear and effective plan of tasks to solve it. "
        "Use any feedback to improve your planning."
    ),
    model=OpenAIChatCompletionsModel(
        model=os.getenv('CAI_MODEL', "qwen2.5:14b"),
        openai_client=AsyncOpenAI(),
    ),
    tools=[] 
)


# Feedback structure for the judge
@dataclass
class EvaluationFeedback:
    feedback: str
    score: Literal["pass", "needs_improvement", "fail"]


# CTF task plan evaluator (judges planning quality)
ctf_plan_evaluator = Agent[None](
    name="CTF Plan Evaluator",
    description="Agent that evaluates CTF task plans for effectiveness and completeness.",
    instructions=(
        "You evaluate a task plan created for solving a CTF challenge. "
        "Ensure it covers all essential steps (recon, exploitation, post-exploitation, etc.). "
        "Provide actionable feedback. Never approve on the first try."
    ),
    model=OpenAIChatCompletionsModel(
        model=os.getenv('CAI_MODEL', "qwen2.5:14b"),
        openai_client=AsyncOpenAI(),
    ),
    tools=[],  
    output_type=EvaluationFeedback,
)


async def main() -> None:
    challenge_desc = input("Describe the CTF challenge: ")
    input_items: list[TResponseInputItem] = [{"content": challenge_desc, "role": "user"}]

    latest_plan: str | None = None
    
    while True:
        try:
            print("\n[INFO] Running CTF Task Planner...")
            planner_result = await Runner.run(ctf_task_planner, input_items)
            input_items = planner_result.to_input_list()
            latest_plan = ItemHelpers.text_message_outputs(planner_result.new_items)
            print("CTF task plan generated.")

            print("\n[INFO] Running CTF Plan Evaluator...")
            eval_result = await Runner.run(ctf_plan_evaluator, input_items)
            feedback: EvaluationFeedback = eval_result.final_output
            print(f"Evaluator score: {feedback.score}")

            if feedback.score == "pass":
                print("CTF task plan approved.")
                break

            print("Refining plan based on evaluator feedback...")
            input_items.append({"content": f"Feedback: {feedback.feedback}", "role": "user"})
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            break

    if latest_plan:
        print(f"Final CTF task plan:\n{latest_plan}")
    else:
        print("No plan was generated due to errors.")


if __name__ == "__main__":
    asyncio.run(main())