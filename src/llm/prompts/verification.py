"""Prompt templates for tree verification (ref: page_index.py:731-786)."""

TITLE_VERIFICATION_PROMPT = """
Your job is to check if the given section appears or starts in the given page_text.

Note: do fuzzy matching, ignore any space inconsistency in the page_text.

<section_title>
{title}
</section_title>

<page_text>
{page_text}
</page_text>

Reply format:
{{
    "thinking": <why do you think the section appears or starts in the page_text>
    "answer": "yes or no" (yes if the section appears or starts in the page_text, no otherwise)
}}
Directly return the final JSON structure. Do not output anything else."""

TITLE_AT_START_PROMPT = """
You will be given the current section title and the current page_text.
Your job is to check if the current section starts in the beginning of the given page_text.
If there are other contents before the current section title, then the current section does not start in the beginning of the given page_text.
If the current section title is the first content in the given page_text, then the current section starts in the beginning of the given page_text.

Note: do fuzzy matching, ignore any space inconsistency in the page_text.

<section_title>
{title}
</section_title>

<page_text>
{page_text}
</page_text>

reply format:
{{
    "thinking": <why do you think the section appears or starts in the page_text>
    "start_begin": "yes or no" (yes if the section starts in the beginning of the page_text, no otherwise)
}}
Directly return the final JSON structure. Do not output anything else."""

SINGLE_TOC_ITEM_FIXER_PROMPT = """
You are given a section title and several pages of a document, your job is to find the physical index of the start page of the section in the partial document.

The provided pages contains tags like <physical_index_X> and <physical_index_X> to indicate the physical location of the page X.

Reply in a JSON format:
{{
    "thinking": <explain which page, started and closed by <physical_index_X>, contains the start of this section>,
    "physical_index": "<physical_index_X>" (keep the format)
}}
Directly return the final JSON structure. Do not output anything else.

<section_title>
{title}
</section_title>

<document_pages>
{content}
</document_pages>"""
