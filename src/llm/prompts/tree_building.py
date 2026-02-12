"""Prompt templates for tree building (ref: page_index.py:240-566)."""

TOC_TO_JSON_PROMPT = """
You are given a table of contents, Your job is to transform the whole table of content into a JSON format included table_of_contents.

structure is the numeric system which represents the index of the hierarchy section in the table of contents. For example, the first section has structure index 1, the first subsection has structure index 1.1, the second subsection has structure index 1.2, etc.

The response should be in the following JSON format:
{{
    "table_of_contents": [
        {{
            "structure": <structure index, "x.x.x" or None> (string),
            "title": <title of the section>,
            "page": <page number or None>,
        }},
        ...
    ],
}}
You should transform the full table of contents in one go.
Directly return the final JSON structure, do not output anything else.

<table_of_contents>
{toc_content}
</table_of_contents>"""

TOC_TO_JSON_CONTINUE_PROMPT = """
Your task is to continue the table of contents json structure, directly output the remaining part of the json structure.

<raw_table_of_contents>
{toc_content}
</raw_table_of_contents>

<incomplete_json>
{incomplete_json}
</incomplete_json>

Please continue the json structure, directly output the remaining part of the json structure."""

TOC_TRANSFORMATION_COMPLETENESS_PROMPT = """
You are given a raw table of contents and a table of contents.
Your job is to check if the table of contents is complete.

Reply format:
{{
    "thinking": <why do you think the cleaned table of contents is complete or not>
    "completed": "yes" or "no"
}}
Directly return the final JSON structure. Do not output anything else.

<raw_table_of_contents>
{raw_toc}
</raw_table_of_contents>

<cleaned_table_of_contents>
{cleaned_toc}
</cleaned_table_of_contents>"""

TREE_GENERATION_INIT_PROMPT = """
You are an expert in extracting hierarchical tree structure, your task is to generate the tree structure of the document.

The structure variable is the numeric system which represents the index of the hierarchy section in the table of contents. For example, the first section has structure index 1, the first subsection has structure index 1.1, the second subsection has structure index 1.2, etc.

For the title, you need to extract the original title from the text, only fix the space inconsistency.

The provided text contains tags like <physical_index_X> and <physical_index_X> to indicate the start and end of page X.

For the physical_index, you need to extract the physical index of the start of the section from the text. Keep the <physical_index_X> format.

The response should be in the following format.
    [
        {{
            "structure": <structure index, "x.x.x"> (string),
            "title": <title of the section, keep the original title>,
            "physical_index": "<physical_index_X> (keep the format)"
        }},
    ],

Directly return the final JSON structure. Do not output anything else.

<document_text>
{text}
</document_text>"""

TREE_GENERATION_CONTINUE_PROMPT = """
You are an expert in extracting hierarchical tree structure.
You are given a tree structure of the previous part and the text of the current part.
Your task is to continue the tree structure from the previous part to include the current part.

The structure variable is the numeric system which represents the index of the hierarchy section in the table of contents. For example, the first section has structure index 1, the first subsection has structure index 1.1, the second subsection has structure index 1.2, etc.

For the title, you need to extract the original title from the text, only fix the space inconsistency.

The provided text contains tags like <physical_index_X> and <physical_index_X> to indicate the start and end of page X.

For the physical_index, you need to extract the physical index of the start of the section from the text. Keep the <physical_index_X> format.

The response should be in the following format.
    [
        {{
            "structure": <structure index, "x.x.x"> (string),
            "title": <title of the section, keep the original title>,
            "physical_index": "<physical_index_X> (keep the format)"
        }},
        ...
    ]

Directly return the additional part of the final JSON structure. Do not output anything else.

<document_text>
{text}
</document_text>

<previous_structure>
{previous_structure}
</previous_structure>"""

PAGE_NUMBER_MAPPING_PROMPT = """
You are given an JSON structure of a document and a partial part of the document. Your task is to check if the title that is described in the structure is started in the partial given document.

The provided text contains tags like <physical_index_X> and <physical_index_X> to indicate the physical location of the page X.

If the full target section starts in the partial given document, insert the given JSON structure with the "start": "yes", and "start_index": "<physical_index_X>".

If the full target section does not start in the partial given document, insert "start": "no", "start_index": None.

The response should be in the following format.
    [
        {{
            "structure": <structure index, "x.x.x" or None> (string),
            "title": <title of the section>,
            "start": "<yes or no>",
            "physical_index": "<physical_index_X> (keep the format)" or None
        }},
        ...
    ]
The given structure contains the result of the previous part, you need to fill the result of the current part, do not change the previous result.
Directly return the final JSON structure. Do not output anything else.

<document_text>
{part}
</document_text>

<current_structure>
{structure}
</current_structure>"""

TOC_INDEX_EXTRACTOR_PROMPT = """
You are given a table of contents in a json format and several pages of a document, your job is to add the physical_index to the table of contents in the json format.

The provided pages contains tags like <physical_index_X> and <physical_index_X> to indicate the physical location of the page X.

The structure variable is the numeric system which represents the index of the hierarchy section in the table of contents. For example, the first section has structure index 1, the first subsection has structure index 1.1, the second subsection has structure index 1.2, etc.

The response should be in the following JSON format:
[
    {{
        "structure": <structure index, "x.x.x" or None> (string),
        "title": <title of the section>,
        "physical_index": "<physical_index_X>" (keep the format)
    }},
    ...
]

Only add the physical_index to the sections that are in the provided pages.
If the section is not in the provided pages, do not add the physical_index to it.
Directly return the final JSON structure. Do not output anything else.

<table_of_contents>
{toc}
</table_of_contents>

<document_pages>
{content}
</document_pages>"""
