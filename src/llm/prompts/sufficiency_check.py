"""Prompt templates for answer sufficiency checking during retrieval (plan section 9.10)."""

SUFFICIENCY_CHECK_PROMPT = """Analyze the following document content to answer the question.

<question>
{query}
</question>

<content>
{content}
</content>

<context>
{ancestor_context}
</context>

<cross_references>
{cross_refs}
</cross_references>

Based on the content and context provided, determine if you can fully answer the question.

Respond ONLY with a JSON object in this format:
{{
    "answer": "Your answer here, or null if insufficient",
    "confidence": 0.85,
    "sufficient": true,
    "nextAction": null
}}

If the content is NOT sufficient to answer the question, set "sufficient" to false and provide a nextAction:
{{
    "answer": null,
    "confidence": 0.3,
    "sufficient": false,
    "nextAction": {{
        "type": "navigate_deeper",
        "targetNodeId": "0003",
        "reasoning": "The section mentions details in subsection 3 that may contain the answer"
    }}
}}

Valid nextAction types: "navigate_deeper", "follow_reference", "search_different_section"

Directly return the JSON. Do not include any other text."""

MULTI_TURN_SUFFICIENCY_PROMPT = """Analyze the following document content to answer the question, considering the conversation history.

<conversation_history>
{conversation_history}
</conversation_history>

<question>
{query}
</question>

<content>
{content}
</content>

<context>
{ancestor_context}
</context>

Based on the content, context, and conversation history, determine if you can fully answer the follow-up question.

Respond ONLY with a JSON object:
{{
    "answer": "Your answer here, or null if insufficient",
    "confidence": 0.85,
    "sufficient": true,
    "nextAction": null
}}

If insufficient, set "sufficient" to false and provide a nextAction with type "navigate_deeper", "follow_reference", or "search_different_section".

Directly return the JSON. Do not include any other text."""
