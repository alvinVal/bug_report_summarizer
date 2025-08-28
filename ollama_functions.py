import ollama
import markdown
import re


def parse_llm_output(raw_text):
    """
    Parses the raw markdown output from the LLM into a dictionary.
    This function is designed to be robust against variations in whitespace and heading markers.
    """
    section_map = {
        'summary': 'summary',
        'recommendations for developers': 'rec_devs',
        'recommendations for testers': 'rec_testers',
        'potential customer impact': 'customer_impact',
        'impact level': 'impact_level'
    }
    sections = {key: '' for key in section_map.values()}

    current_key = None
    buffer = []

    for line in raw_text.splitlines():
        match = re.match(r'^\s*##\s*(.*)', line, re.IGNORECASE)
        if match:
            if current_key and buffer:
                sections[current_key] = '\n'.join(buffer).strip()
            buffer = []
            heading_text = match.group(1).strip().lower()
            current_key = section_map.get(heading_text)
        elif current_key:
            buffer.append(line)

    if current_key and buffer:
        sections[current_key] = '\n'.join(buffer).strip()

    if sections.get('impact_level'):
        impact_match = re.search(r'\b(HIGH|MEDIUM|LOW)\b', sections['impact_level'], re.IGNORECASE)
        sections['impact_level'] = impact_match.group(1).upper() if impact_match else 'N/A'

    return sections


def _generate_iterative_summary(df, initial_prompt, refinement_prompt, ollama_model, chunk_size, progress_label,
                                cancel_event):
    """
    Generates a summary by processing a DataFrame in chunks, now with cancellation support.
    """
    previous_summary_md = ""
    total_reports = len(df)

    for i in range(0, total_reports, chunk_size):
        if cancel_event.is_set():
            print(f"  -> Cancellation detected in {progress_label}. Stopping summary generation.")
            return ""

        chunk_df = df.iloc[i:i + chunk_size]
        chunk_csv = chunk_df.to_csv(index=False)

        processed_count = min(i + chunk_size, total_reports)
        print(f"  -> Processing chunk for {progress_label}: ({processed_count} of {total_reports} reports)")

        prompt = initial_prompt.format(reports_csv=chunk_csv) if not previous_summary_md else refinement_prompt.format(
            previous_summary=previous_summary_md,
            new_reports=chunk_csv
        )
        messages = [{"role": "system",
                     "content": "You are a software QA expert. Always respond using the exact markdown format requested."},
                    {"role": "user", "content": prompt}]

        response = ollama.chat(
            model=ollama_model,
            messages=messages,
            options={'temperature': 0.2}
        )

        previous_summary_md = response['message']['content']

        print("\n" + "--- LLM Response ---".center(60, "-"))
        print(previous_summary_md)
        print("--- End of Response ---".center(60, "-") + "\n")

    return previous_summary_md


def generate_summary_table(df, project_component_dfs, project_col, ollama_model, chunk_size, cancel_event, gui_app,
                           total_summary_tasks):
    """
    Generates summaries for each project and component, updating a detailed progress bar.
    """
    project_overall_summaries = {}
    project_component_summaries = {}
    completed_tasks = 0

    for project, components in project_component_dfs.items():
        if cancel_event.is_set(): break

        project_data = df[df[project_col] == project]

        # --- FIX: Made prompts stricter and more direct to avoid model confusion ---
        overall_initial_prompt = (
            f"You are a helpful assistant that ALWAYS follows the requested response format. "
            f"Analyze the following bug reports for project '{project}'.\n"
            "Your response MUST be in Markdown format and MUST use the following headers EXACTLY as written. Do not add any other headers or introductory text.\n\n"
            "## Summary\n"
            "* (Provide a bulleted list of key findings and recurring issues. Maximum 5 points.)\n\n"
            "## Potential Customer Impact\n"
            "(Provide a one or two sentence description of the potential customer impact.)\n\n"
            "--- Bug Reports to Analyze ---\n"
            "{{reports_csv}}"
        )
        overall_refinement_prompt = (
            f"You are a helpful assistant that ALWAYS follows the requested response format. "
            f"An existing summary for project '{project}' is provided below, along with a new batch of bug reports. "
            "Combine all information into a single, updated, comprehensive analysis.\n"
            "Your response MUST be in Markdown format and MUST use the following headers EXACTLY as written. Do not add any other headers or introductory text.\n\n"
            "## Summary\n"
            "* (Provide a new, updated bulleted list of key findings and recurring issues. Maximum 5 points.)\n\n"
            "## Potential Customer Impact\n"
            "(Provide a new, updated one or two sentence description of the potential customer impact.)\n\n"
            "--- Existing Summary ---\n"
            "{{previous_summary}}\n\n"
            "--- New Bug Reports to Analyze ---\n"
            "{{new_reports}}"
        )
        # --- END OF FIX ---

        print(f"\nProject {project} (Overall Summary): \n" + "=" * 40)
        overall_label = f"Project {project} Overall"

        status_text = f"Summarizing: {project[:35]}..."
        progress_val = 10 + (completed_tasks / total_summary_tasks) * 90
        percent_text = f"{int(progress_val)}%"
        gui_app.after(0, gui_app.update_progress, progress_val, percent_text, status_text)

        overall_summary_md = _generate_iterative_summary(
            project_data, overall_initial_prompt, overall_refinement_prompt, ollama_model, chunk_size, overall_label,
            cancel_event
        )
        if cancel_event.is_set(): break

        completed_tasks += 1
        overall_fields_raw = parse_llm_output(overall_summary_md)
        project_overall_summaries[project] = {key: markdown.markdown(value) for key, value in
                                              overall_fields_raw.items()}

        project_component_summaries[project] = {}
        for comp, sub_df in components.items():
            if cancel_event.is_set(): break

            comp_initial_prompt = (
                f"You are a helpful assistant that ALWAYS follows the requested response format. Analyze bug reports for the '{comp}' component in project '{project}'.\n"
                "Your response MUST be in Markdown and use these headers EXACTLY:\n\n"
                "## Summary\n* (Bulleted list of findings.)\n\n## Recommendations for Developers\n* (Bulleted list.)\n\n## Recommendations for Testers\n* (Bulleted list.)\n\n"
                "## Potential Customer Impact\n(One or two sentences.)\n\n## Impact Level\n(ONLY ONE of: HIGH, MEDIUM, or LOW)\n\n"
                "--- Bug Reports to Analyze ---\n{{reports_csv}}"
            )
            comp_refinement_prompt = (
                f"You are a helpful assistant. An existing summary for '{comp}' is below, along with new reports. Combine all information into an updated analysis.\n"
                "Your response MUST be in Markdown and use these headers EXACTLY:\n\n"
                "## Summary\n* (New bulleted list.)\n\n## Recommendations for Developers\n* (New bulleted list.)\n\n## Recommendations for Testers\n* (New bulleted list.)\n\n"
                "## Potential Customer Impact\n(New one or two sentences.)\n\n## Impact Level\n(ONLY ONE of: HIGH, MEDIUM, or LOW)\n\n"
                "--- Existing Summary ---\n{{previous_summary}}\n\n--- New Bug Reports to Analyze ---\n{{new_reports}}"
            )

            print(f"Project {project} | Component {comp} (Summary):\n" + "-" * 40)
            component_label = f"Component '{comp}'"

            status_text = f"Summarizing: {comp[:35]}..."
            progress_val = 10 + (completed_tasks / total_summary_tasks) * 90
            percent_text = f"{int(progress_val)}%"
            gui_app.after(0, gui_app.update_progress, progress_val, percent_text, status_text)

            comp_summary_md = _generate_iterative_summary(
                sub_df, comp_initial_prompt, comp_refinement_prompt, ollama_model, chunk_size, component_label,
                cancel_event
            )
            if cancel_event.is_set(): break

            completed_tasks += 1
            comp_fields_raw = parse_llm_output(comp_summary_md)
            comp_fields_html = {key: markdown.markdown(value) for key, value in comp_fields_raw.items()}
            comp_fields_html['impact_level'] = comp_fields_raw.get('impact_level', 'N/A')
            project_component_summaries[project][comp] = comp_fields_html

        if cancel_event.is_set(): break

    return project_overall_summaries, project_component_summaries