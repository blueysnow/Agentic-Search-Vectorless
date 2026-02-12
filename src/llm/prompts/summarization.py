"""Prompt templates for node summarization and enrichment (ref: utils.py:605-658)."""

NODE_SUMMARY_PROMPT = """You are given a part of a document, your task is to generate a description of the partial document about what are main points covered in the partial document.

<document_text>
{node_text}
</document_text>

Directly return the description, do not include any other text."""

DOC_DESCRIPTION_PROMPT = """Your are an expert in generating descriptions for a document.
You are given a structure of a document. Your task is to generate a one-sentence description for the document, which makes it easy to distinguish the document from other documents.

<document_structure>
{structure}
</document_structure>

Directly return the description, do not include any other text."""

KEYWORD_EXTRACTION_PROMPT = """Extract 3 to 8 keywords from the following text. The keywords should capture the key topics, concepts, and entities discussed.

<document_text>
{node_text}
</document_text>

Return ONLY a JSON array of keyword strings, like: ["keyword1", "keyword2", "keyword3"]
Do not include any other text."""
