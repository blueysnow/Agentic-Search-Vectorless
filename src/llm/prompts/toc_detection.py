"""Prompt templates for ToC detection (ref: page_index.py:104-235)."""

TOC_DETECTION_PROMPT = """
Your job is to detect if there is a table of content provided in the given text.

<document_text>
{content}
</document_text>

return the following JSON format:
{{
    "thinking": <why do you think there is a table of content in the given text>
    "toc_detected": "<yes or no>",
}}

Directly return the final JSON structure. Do not output anything else.
Please note: abstract, summary, notation list, figure list, table list, etc. are not table of contents."""

TOC_EXTRACTION_PROMPT = """
Your job is to extract the full table of contents from the given text, replace ... with :

<document_text>
{content}
</document_text>

Directly return the full table of contents content. Do not output anything else."""

TOC_CONTINUATION_PROMPT = """please continue the generation of table of contents, directly output the remaining part of the structure"""

TOC_EXTRACTION_COMPLETENESS_PROMPT = """
You are given a partial document and a table of contents.
Your job is to check if the table of contents is complete, which it contains all the main sections in the partial document.

Reply format:
{{
    "thinking": <why do you think the table of contents is complete or not>
    "completed": "yes" or "no"
}}
Directly return the final JSON structure. Do not output anything else.

<document_text>
{content}
</document_text>

<table_of_contents>
{toc}
</table_of_contents>"""

PAGE_NUMBER_DETECTION_PROMPT = """
You will be given a table of contents.

Your job is to detect if there are page numbers/indices given within the table of contents.

<table_of_contents>
{toc_content}
</table_of_contents>

Reply format:
{{
    "thinking": <why do you think there are page numbers/indices given within the table of contents>
    "page_index_given_in_toc": "<yes or no>"
}}
Directly return the final JSON structure. Do not output anything else."""
