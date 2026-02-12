"""Prompt templates for LLM-driven tree navigation during retrieval (plan section 9.9)."""

TREE_NAVIGATION_PROMPT = """You are a document navigation expert. Given the following sections from a document's table of contents, select which section(s) most likely contain the answer to the user's question.

<document_info>
Document: {document_name}
Description: {document_description}
</document_info>

<sections>
{sections}
</sections>

<question>
{query}
</question>

You must select between 1 and 3 sections that are most likely to contain the answer. Consider the section titles, summaries, and page ranges.

Respond ONLY with a JSON object in this format:
{{
    "selectedNodeIds": ["nodeId1", "nodeId2"],
    "reasoning": "Brief explanation of why these sections were selected"
}}

Directly return the JSON. Do not include any other text."""

TREE_NAVIGATION_WITH_CONTEXT_PROMPT = """You are a document navigation expert. You have previously visited some sections and need to decide where to look next.

<document_info>
Document: {document_name}
Description: {document_description}
</document_info>

<previously_visited>
{visited_context}
</previously_visited>

<available_sections>
{sections}
</available_sections>

<question>
{query}
</question>

Select 1-3 sections to explore next. Avoid sections that overlap heavily with previously visited content unless you believe a deeper look is needed.

Respond ONLY with a JSON object:
{{
    "selectedNodeIds": ["nodeId1", "nodeId2"],
    "reasoning": "Brief explanation of why these sections were selected"
}}

Directly return the JSON. Do not include any other text."""
