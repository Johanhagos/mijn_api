"""Prompt templates for the agent's planner and tool selector.
Keep prompts small and deterministic where possible.
"""
SIMPLE_TOOL_SELECTOR = """
You are an assistant that maps tasks to tools.
Available tools: check_api_health, deploy_vercel, run_script, git_commit_and_push, read_logs
Task: {task}
Respond with a single JSON object: {"tool":"tool_name","args":{...}}
"""
