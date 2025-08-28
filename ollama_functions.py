import ollama
import markdown
import re


def parse_summary_text(text):
    """
    Parses the AI-generated raw markdown to extract the fields:
      - Summary
      - Recommendations for Developers
      - Recommendations for Testers
      - Potential Customer Impact
      - Impact Level
    Expects the response to include sections exactly as:
      ## Summary
      ## Recommendations for Developers
      ## Recommendations for Testers
      ## Potential Customer Impact
      ## Impact Level
    """
    fields = {
        'summary': '',
        'rec_devs': '',
        'rec_testers': '',
        'customer_impact': '',
        'impact_level': ''
    }

    # Use a regex to capture sections (non-greedy until next header or end)
    pattern = r'##\s*(.+?)\s*\n(.*?)(?=\n##|$)'
    matches = re.findall(pattern, text, flags=re.DOTALL)
    for section, content in matches:
        sec_lower = section.strip().lower()
        if "summary" in sec_lower and "recommendations" not in sec_lower:
            fields['summary'] = content.strip()
        elif "recommendations for developers" in sec_lower:
            fields['rec_devs'] = content.strip()
        elif "recommendations for testers" in sec_lower:
            fields['rec_testers'] = content.strip()
        elif "potential customer impact" in sec_lower:
            fields['customer_impact'] = content.strip()
        elif "impact level" in sec_lower:
            fields['impact_level'] = content.strip()
    return fields


def generate_summary_table(df, project_component_dfs, project_col, ollama_model):
    """
    For each project in project_component_dfs:
      - Generate an overall project summary using the full CSV data for that project.
      - For each component within the project, generate a component summary using its CSV data.

    The AI is prompted to return an answer with the following sections exactly:
      ## Summary
      ## Potential Customer Impact
    The returned raw markdown is then parsed and each field is converted individually to HTML.

    Returns:
      project_overall_summaries: Dictionary mapping project -> {field: HTML text, ... }
      project_component_summaries: Nested dictionary mapping project -> { component -> {field: HTML text, ... } }
    """
    project_overall_summaries = {}
    project_component_summaries = {}

    for project, components in project_component_dfs.items():
        # Prompt for overall summary for the project
        project_data = df[df[project_col] == project]
        overall_prompt = (
                f"Generate an overall summary for project '{project}' based on the bug report data. Limit each section to 3 sentences.\n"
                "Please provide the output with the following sections exactly:\n\n"
                "## Summary\n- Talk about the most important issues in three sentences.\n"
                "## Potential Customer Impact\nDescribe the potential impact in three sentences.\n\n"
                "Here is the CSV data for the project:\n" +
                project_data.to_csv(index=False)
        )
        messages = [
            {"role": "system", "content": "You are a helpful software QA expert."},
            {"role": "user", "content": overall_prompt}
        ]
        overall_response = ollama.chat(model=ollama_model, messages=messages)
        # Get raw markdown and parse fields
        overall_markdown = overall_response.message.content
        overall_fields = parse_summary_text(overall_markdown)
        # Convert each field from markdown to HTML (so that bullet/numbered lists render properly)
        for key in overall_fields:
            overall_fields[key] = markdown.markdown(overall_fields[key] or '')
        project_overall_summaries[project] = overall_fields

        print(overall_fields)

        project_component_summaries[project] = {}
        # Process each component
        for comp, sub_df in components.items():
            comp_prompt = (
                    f"Generate a summary for the component '{comp}' in project '{project}' based on the bug report data.\n"
                    "Provide the output with the following sections exactly, don't leave any sections out, and limit each section to 3 lines.\n\n"
                    "## Summary\n- List the key recurring issues as bullet points.\n\n"
                    "## Recommendations for Developers\n- List detailed recommendations as bullet points.\n\n"
                    "## Recommendations for Testers\n- List detailed recommendations as bullet points.\n\n"
                    "## Potential Customer Impact\nProvide a three sentence description.\n\n"
                    "## Impact Level\nState the impact level, either HIGH, MEDIUM or LOW. Choose only one of the three levels, make sure to have this section, don't explain.\n\n"
                    "Make sure not to forget any part.\n"
                    "Here is the CSV data for this component:\n" +
                    sub_df.to_csv(index=False)
            )
            messages = [
                {"role": "system", "content": "You are a helpful software QA expert."},
                {"role": "user", "content": comp_prompt}
            ]
            comp_response = ollama.chat(model=ollama_model, messages=messages)
            comp_markdown = comp_response.message.content
            comp_fields = parse_summary_text(comp_markdown)
            for key in comp_fields:
                comp_fields[key] = markdown.markdown(comp_fields[key] or '')
            project_component_summaries[project][comp] = comp_fields

            print(comp_fields)

    return project_overall_summaries, project_component_summaries
