
import asyncio
import json
from pathlib import Path
from typing import Any
from observability.tracing import observe_agent
import yaml
import time
from observability.metrics import record_tool_call
from observability.tracing import trace_span
from config.settings import get_settings
from services.llm_service import get_llm_service
from agents.tools import RESEARCH_TOOLS


settings = get_settings()

PROMPT_PATH = Path("config/prompts.yaml")

TOOL_MAP = {
    item.name: item for item in RESEARCH_TOOLS
}


def load_research_prompts() -> dict[str, str]:
    """Load the Research Agent prompts from prompts.yaml."""

    if not PROMPT_PATH.exists():
        raise FileNotFoundError(
            f"Research prompt file not found: {PROMPT_PATH}"
        )

    with PROMPT_PATH.open("r", encoding="utf-8") as file:
        prompts = yaml.safe_load(file)

    research = prompts.get("research_agent", {})

    if not research.get("system") or not research.get("task"):
        raise ValueError("Research Agent prompts are incomplete")

    return research


def get_groq_tool_schemas() -> list[dict[str, Any]]:
    """Convert LangChain tools into Groq/OpenAI function schemas."""

    schemas = []

    for research_tool in RESEARCH_TOOLS:
        schemas.append({
            "type": "function",
            "function": {
                "name": research_tool.name,
                "description": research_tool.description,
                "parameters": research_tool.args_schema.model_json_schema(),
            },
        })

    return schemas


async def execute_research_tool(
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Execute one selected research tool with timeout and observability."""

    start_time = time.perf_counter()
    status = "failed"

    # Restrict metric labels to registered tools.
    metric_tool_name = (
        tool_name if tool_name in TOOL_MAP else "unknown"
    )

    with trace_span(
        f"tool.{metric_tool_name}",
        {
            "tool.name": metric_tool_name,
            "agent.name": "research_agent",
        },
    ) as span:

        try:
            selected_tool = TOOL_MAP.get(tool_name)

            if selected_tool is None:
                return {
                    "error": f"Unknown research tool: {tool_name}",
                    "evidence_found": False,
                }

            result = await asyncio.wait_for(
                asyncio.to_thread(
                    selected_tool.invoke,
                    arguments,
                ),
                timeout=settings.tool_timeout_seconds,
            )

            if not isinstance(result, dict):
                return {
                    "error": "Research tool returned an invalid result",
                    "evidence_found": False,
                }

            status = "success"
            return result

        except asyncio.TimeoutError:
            return {
                "error": f"Tool execution timed out: {tool_name}",
                "evidence_found": False,
            }

        except Exception as exc:
            return {
                "error": f"Tool execution failed: {str(exc)}",
                "evidence_found": False,
            }

        finally:
            duration = time.perf_counter() - start_time

            record_tool_call(
                agent_name="research_agent",
                tool_name=metric_tool_name,
                status=status,
            )

            span.set_attribute("tool.status", status)
            span.set_attribute("tool.duration_seconds", duration)


def extract_findings(content: str | None) -> dict[str, Any]:
    """Extract structured findings when the LLM returns JSON."""

    if not content:
        return {}

    try:
        parsed = json.loads(content)

        if isinstance(parsed, dict):
            return parsed

    except (json.JSONDecodeError, TypeError):
        pass

    return {}


@observe_agent("research_agent")
async def research_petition(
    state: dict[str, Any],
) -> dict[str, Any]:
    """
    Research a student petition using bounded Groq tool calling.

    Returns research findings and retrieved evidence for
    the Verification Agent.
    """

    petition = state.get("petition", {})

    if not petition:
        raise ValueError("Petition data is missing from agent state")

    prompts = load_research_prompts()
    llm = get_llm_service()

    initial_evidence = state.get("retrieved_provisions", [])

    task_prompt = prompts["task"].format(
        petition=json.dumps(petition, ensure_ascii=False),
        initial_evidence=json.dumps(
            initial_evidence,
            ensure_ascii=False,
        ),
    )

    task_prompt += """

    IMPORTANT: Your final response MUST be a valid JSON object.
    Do not wrap it in Markdown code fences.

    Use exactly this structure:

    {
        "petition_category": "attendance",
        "classification_confidence": 0.95,
        "research_query": "attendance condonation medical grounds",
        "findings": "Summary of the retrieved regulatory evidence.",
        "citations": [
            {
                "clause_reference": "Exact clause reference",
                "document_id": "Exact document identifier",
                "text": "Exact supporting passage"
            }
        ],
        "proposed_recommendation": "refer-to-committee",
        "missing_evidence": []
    }

    Rules:
    1. Use only provisions actually returned by retrieval tools.
    2. Never invent clause references, document IDs or quotations.
    3. If no relevant evidence is found, citations MUST be [].
    4. If evidence is insufficient, recommend refer-to-committee.
    5. Use only these recommendation values:
    grant-under-provision
    refer-to-committee
    reject
    6. Do not treat a medical ground as automatic eligibility.
    7. Identify potentially relevant condonation provisions.
    8. The examination officer retains final decision authority.
    """

    messages = [
        {
            "role": "system",
            "content": prompts["system"],
        },
        {
            "role": "user",
            "content": task_prompt,
        },
    ]

    tool_schemas = get_groq_tool_schemas()

    retrieved_evidence: list[dict[str, Any]] = []
    errors = list(state.get("errors", []))

    tool_calls_used = 0
    agent_steps = 0
    limit_reached = False
    final_content = ""

    evidence_found = False
    requires_escalation = False

    while agent_steps < settings.max_agent_steps:

        agent_steps += 1

        # Once the tool-call budget is exhausted, request a
        # final answer without allowing further tool execution.
        available_tools = (
            tool_schemas
            if tool_calls_used < settings.max_tool_calls
            else None
        )

        try:
            if available_tools:
                response = await llm.generate_with_tools(
                    messages=messages,
                    tools=available_tools,
                    tool_choice="auto",
                )
            else:
                response_text = await llm.generate(
                    messages=messages,
                )

                final_content = response_text
                limit_reached = True
                break

        except Exception as exc:
            errors.append(f"LLM request failed: {str(exc)}")
            requires_escalation = True
            break

        messages.append(response)

        content = response.get("content")
        if isinstance(content, str) and content.strip():
            final_content = content

        requested_calls = response.get("tool_calls") or []

        if not requested_calls:
            break

        for tool_call in requested_calls:

            if tool_calls_used >= settings.max_tool_calls:
                limit_reached = True
                requires_escalation = True
                break

            function = tool_call.get("function", {})
            tool_name = function.get("name")
            raw_arguments = function.get("arguments", "{}")
            call_id = tool_call.get("id")

            if not tool_name or not call_id:
                errors.append("Malformed tool call received from LLM")
                requires_escalation = True
                continue

            try:
                arguments = json.loads(raw_arguments)

                if not isinstance(arguments, dict):
                    raise ValueError("Tool arguments must be a JSON object")

            except (json.JSONDecodeError, ValueError) as exc:
                result = {
                    "error": f"Invalid tool arguments: {str(exc)}",
                    "evidence_found": False,
                }

            else:
                tool_calls_used += 1

                result = await execute_research_tool(
                    tool_name,
                    arguments,
                )

            if result.get("evidence_found"):
                evidence_found = True

            if result.get("requires_escalation"):
                requires_escalation = True

            if result.get("error"):
                errors.append(result["error"])
                requires_escalation = True

            tool_evidence = result.get("results", [])

            if tool_evidence:
                retrieved_evidence.extend(tool_evidence)

            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": json.dumps(
                    result,
                    ensure_ascii=False,
                    default=str,
                ),
            })

        if limit_reached:
            break

    else:
        limit_reached = True
        requires_escalation = True

    # Deduplicate evidence by document ID and text.
    unique_evidence = []
    seen_evidence = set()

    for item in retrieved_evidence:
        identity = (
            item.get("document_id"),
            item.get("text"),
        )

        if identity not in seen_evidence:
            seen_evidence.add(identity)
            unique_evidence.append(item)

    if not unique_evidence:
        evidence_found = False
        requires_escalation = True

    if limit_reached:
        requires_escalation = True

    if errors:
        requires_escalation = True

    structured_findings = extract_findings(final_content)

    return {
        "current_agent": "research_agent",

        "petition_category": structured_findings.get(
            "petition_category",
            "unclassified",
        ),

        "classification_confidence": structured_findings.get(
            "classification_confidence",
            0.0,
        ),

        "research_query": structured_findings.get(
            "research_query",
            "",
        ),

        "proposed_recommendation": structured_findings.get(
            "proposed_recommendation",
            "refer-to-committee",
        ),

        "retrieved_provisions": unique_evidence,

        "research_findings": final_content,

        "research_complete": True,

        "evidence_found": evidence_found,

        "requires_escalation": (
            requires_escalation
            or not bool(structured_findings)
        ),

        "agent_steps": (
            state.get("agent_steps", 0) + agent_steps
        ),

        "tool_calls": (
            state.get("tool_calls", 0) + tool_calls_used
        ),

        "errors": errors,
    }
