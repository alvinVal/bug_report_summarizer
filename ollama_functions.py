import os

# Set the OLLAMA_HOST environment variable
os.environ['OLLAMA_HOST'] = 'http://10.65.168.147:11434'

import ollama
import markdown
import re


def parse_llm_output(raw_text):
    """
    Parses the raw markdown output from the LLM into a dictionary.
    This function is designed to be robust against variations in whitespace and heading markers.
    """
    # Define the section headers we expect and the keys they map to.
    section_map = {
        'summary': 'summary',
        'recommendations for developers': 'rec_devs',
        'recommendations for testers': 'rec_testers',
        'potential customer impact': 'customer_impact',
        'impact level': 'impact_level'
    }

    # Initialize a dictionary to hold the content of each section.
    sections = {
        'summary': '', 'rec_devs': '', 'rec_testers': '',
        'customer_impact': '', 'impact_level': ''
    }

    current_key = None
    buffer = []

    for line in raw_text.splitlines():
        # Check if the line is a heading (e.g., "## Summary")
        match = re.match(r'^\s*##\s*(.*)', line, re.IGNORECASE)
        if match:
            # If we were already building a section, save its content.
            if current_key and buffer:
                sections[current_key] = '\n'.join(buffer).strip()
            buffer = []  # Reset the buffer for the new section.

            # Normalize the heading text to find its corresponding key.
            heading_text = match.group(1).strip().lower()
            current_key = section_map.get(heading_text)
        elif current_key:
            # If we are inside a known section, add the line to its buffer.
            buffer.append(line)

    # Save any content remaining in the buffer after the last heading.
    if current_key and buffer:
        sections[current_key] = '\n'.join(buffer).strip()

    # Clean the 'impact_level' field to ensure it only contains HIGH, MEDIUM, or LOW.
    if sections.get('impact_level'):
        impact_match = re.search(r'\b(HIGH|MEDIUM|LOW)\b', sections['impact_level'], re.IGNORECASE)
        if impact_match:
            sections['impact_level'] = impact_match.group(1).upper()
        else:
            sections['impact_level'] = 'N/A'  # Default if no keyword is found

    return sections


def _generate_iterative_summary(df, initial_prompt, refinement_prompt, ollama_model, chunk_size, progress_label):
    """
    Generates a summary by processing a DataFrame in chunks, showing progress and LLM output.
    """
    previous_summary_md = ""
    total_reports = len(df)

    for i in range(0, total_reports, chunk_size):
        chunk_df = df.iloc[i:i + chunk_size]
        chunk_csv = chunk_df.to_csv(index=False)

        processed_count = min(i + chunk_size, total_reports)
        print(f"  -> Processing chunk for {progress_label}: ({processed_count} of {total_reports} reports)")

        if not previous_summary_md:
            current_prompt = initial_prompt.format(reports_csv=chunk_csv)
        else:
            current_prompt = refinement_prompt.format(
                previous_summary=previous_summary_md,
                new_reports=chunk_csv
            )

        messages = [
            {"role": "system",
             "content": "You are a software QA expert. Always respond using the exact markdown format requested."},
            {"role": "user", "content": current_prompt}
        ]
        response = ollama.chat(model=ollama_model, messages=messages)
        previous_summary_md = response['message']['content']

        # --- NEW: Display the LLM response in the terminal ---
        print("\n" + "--- LLM Response ---".center(60, "-"))
        print(previous_summary_md)
        print("--- End of Response ---".center(60, "-") + "\n")

    return previous_summary_md


def generate_summary_table(df, project_component_dfs, project_col, ollama_model, chunk_size):
    """
    Generates summaries for each project and component with detailed progress reporting.
    """
    project_overall_summaries = {}
    project_component_summaries = {}

    for project, components in project_component_dfs.items():
        project_data = df[df[project_col] == project]

        # --- Prompts for Overall Project Summary ---
        overall_initial_prompt = (f"""
            Analyze the following bug reports for project '{project}', and write a concise overall summary of key recurring issues and their impact across all components.
            List main issue areas and recurring trends as bullet points, and provide a short customer impact summary. Use markdown formatting.
            Please follow this format exactly. Example:
            ## Summary
            - Example bullet 1 (grouped issue)
            - Example bullet 2

            ## Potential Customer Impact
            Two sentences.

            Bug Reports:
            {{reports_csv}}
            """
                                  )
        overall_refinement_prompt = (f"""
            Based on the existing summary and the new bug reports provided below, generate a single, updated, and a concise overall summary of key recurring issues and their impact across all components for project '{project}'.
            List main issue areas and recurring trends as bullet points, and provide a short customer impact summary. There should only be 5 bullets at most for the summary. Use markdown formatting.
            Please follow this format exactly. Example:
            ## Summary
            - Example bullet 1 (grouped issue)
            - Example bullet 2

            ## Potential Customer Impact
            Two sentences.

            ## Existing Summary:
            {{previous_summary}}

            ## New Bug Reports:
            {{new_reports}}
            """
                                     )

        print(f"\nProject {project} (Overall Summary): \n" + "=" * 40)
        overall_label = f"Project {project} Overall"

        overall_summary_md = _generate_iterative_summary(
            project_data, overall_initial_prompt, overall_refinement_prompt, ollama_model, chunk_size, overall_label
        )
        overall_fields_raw = parse_llm_output(overall_summary_md)
        project_overall_summaries[project] = {key: markdown.markdown(value) for key, value in
                                              overall_fields_raw.items()}

        project_component_summaries[project] = {}
        for comp, sub_df in components.items():
            # --- Prompts for Component Summary ---
            comp_initial_prompt = (
                f"Given the following bug reports for the '{comp}' component in project '{project}'.\n"
                "1. Summarize the key findings and recurring issues as a bullet list, with a maximum of 5 concise bullet points.\n"
                "2. Provide separate bulleted recommendations for developers.\n"
                "3. Provide separate bulleted recommendations for testers.\n"
                "4. Add a one or two sentence potential customer impact description.\n"
                "5. Rate the customer impact as HIGH, MEDIUM, or LOW, depending on how much a customer can be affected. Only answer either of the three.\n"
                "Respond in Markdown format, use clear section markers, do not ever respond in any other way:\n"
                "## Summary\n(bulleted list)\n\n"
                "## Recommendations for Developers\n(bulleted list)\n\n"
                "## Recommendations for Testers\n(bulleted list)\n\n"
                "## Potential Customer Impact\n(one or two sentences)\n\n"
                "## Impact Level\n(Write: Impact: HIGH/MEDIUM/LOW)\n\n"
                "Bug Reports:\n{{reports_csv}}"
            )
            comp_refinement_prompt = (
                f"Below is an existing summary for the '{comp}' component and a new batch of reports.\n"
                "Combine all information to create a single, new, comprehensive summary.\n"
                "1. Summarize the key findings and recurring issues as a bullet list, with a maximum of 5 concise bullet points.\n"
                "2. Provide separate bulleted recommendations for developers.\n"
                "3. Provide separate bulleted recommendations for testers.\n"
                "4. Add a one or two sentence potential customer impact description.\n"
                "5. Rate the customer impact as HIGH, MEDIUM, or LOW, depending on how much a customer can be affected. Only answer either of the three.\n"
                "Respond in Markdown format, use clear section markers, do not ever respond in any other way:\n"
                "## Summary\n(bulleted list with asterisks)\n\n"
                "## Recommendations for Developers\n(bulleted list with asterisks)\n\n"
                "## Recommendations for Testers\n(bulleted list with asterisks)\n\n"
                "## Potential Customer Impact\n(one or two sentences)\n\n"
                "## Impact Level\n(Write: Impact: HIGH/MEDIUM/LOW)\n\n"
                "## Existing Summary:\n{{previous_summary}}\n\n"
                "## New Bug Reports:\n{{new_reports}}"
            )

            print(f"Project {project} | Component {comp} (Summary):\n" + "-" * 40)
            component_label = f"Component '{comp}'"

            comp_summary_md = _generate_iterative_summary(
                sub_df, comp_initial_prompt, comp_refinement_prompt, ollama_model, chunk_size, component_label
            )
            comp_fields_raw = parse_llm_output(comp_summary_md)

            comp_fields_html = {key: markdown.markdown(value) for key, value in comp_fields_raw.items()}
            comp_fields_html['impact_level'] = comp_fields_raw.get('impact_level', 'N/A')
            project_component_summaries[project][comp] = comp_fields_html

    return project_overall_summaries, project_component_summaries