"""Prompt templates for query analysis and classification (plan section 7.1 step 1)."""

QUERY_ANALYSIS_PROMPT = """Analyze the following user question about a document. Classify the query type and extract useful search terms.

<question>
{query}
</question>

<document_info>
Document: {document_name}
Description: {document_description}
</document_info>

Classify the query into one of these types:
- "factual_lookup": Simple factual questions (who, what, when, where)
- "analytical": Questions requiring analysis or interpretation
- "comparison": Questions comparing two or more things
- "multi_hop": Questions requiring information from multiple sections
- "definitional": Questions asking for definitions or explanations

Extract the most important keywords that would help find the answer via text search.

Respond ONLY with a JSON object:
{{
    "query_type": "factual_lookup",
    "keywords": ["keyword1", "keyword2", "keyword3"],
    "expected_content_type": "section",
    "reasoning": "Brief explanation of the classification"
}}

Valid expected_content_type values: "section", "table", "figure", "appendix", "any"

Directly return the JSON. Do not include any other text."""
