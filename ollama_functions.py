import ollama
import markdown


def parse_llm_markdown(md):  # This function will parse the summaries from the LLM into data frames for later use
    # Extract sections based on headings
    sections = {'summary': '', 'dev': '', 'test': '', 'impact_desc': '', 'impact': ''}
    current = None
    buff = []
    for line in md.splitlines():
        lin = line.strip().lower()
        if lin.startswith('## summary'):
            if current:
                sections[current] = '\n'.join(buff).strip()
                buff = []
            current = 'summary'
        elif lin.startswith('## recommendations for developers'):
            if current:
                sections[current] = '\n'.join(buff).strip()
                buff = []
            current = 'dev'
        elif lin.startswith('## recommendations for testers'):
            if current:
                sections[current] = '\n'.join(buff).strip()
                buff = []
            current = 'test'
        elif lin.startswith('## potential customer impact'):
            if current:
                sections[current] = '\n'.join(buff).strip()
                buff = []
            current = 'impact_desc'
        elif lin.startswith('## impact level'):
            if current:
                sections[current] = '\n'.join(buff).strip()
                buff = []
            current = 'impact'
        else:
            buff.append(line)
    if current:
        sections[current] = '\n'.join(buff).strip()
    # Extract impact level
    impact_rating = 'MEDIUM'
    for word in ['HIGH', 'MEDIUM', 'LOW']:
        if word in sections['impact']:
            impact_rating = word
            break
    return sections['summary'], sections['dev'], sections['test'], sections['impact_desc'], impact_rating


def generate_summary_table(all_bugs, component_dfs, ollama_model):  # This is the main function for generating summaries
    summaries = []

    # Overall summary using all data for the top-of-page block (markdown to HTML)
    all_bugs_text = all_bugs.to_string(index=False)
    overall_prompt = ("""
        Given these bug reports found below, write a concise overall summary of key recurring issues and their impact across all components.
        List main issue areas as bullet points, provide a one-paragraph customer impact summary, and note notable trends. Use markdown formatting.
        Please follow this format exactly. Example:
        ## Summary
        - Example bullet 1 (grouped issue)
        - Example bullet 2

        ## Recommendations for Developers
        - Example dev rec 1
        - Example dev rec 2

        ## Recommendations for Testers
        - Example tester rec 1

        ## Potential Customer Impact
        Short sentence.

        ## Impact Level
        Impact: HIGH


        """ + all_bugs_text
                      )
    messages = [
        {'role': 'system', 'content': "You are a helpful assistant software QA lead."},
        {'role': 'user', 'content': overall_prompt}
    ]
    response = ollama.chat(model=ollama_model, messages=messages)
    overall_text = markdown.markdown(response.message.content)

    # For debugging the overall summary
    print("------- Overall -------\n" + overall_text)

    # Per-component summaries
    for component, df in component_dfs.items():
        if df.empty:
            continue
        component_issues = df.to_string(index=False)
        prompt = (
                f"Given the following bug reports for the '{component}' component:\n"
                "1. Summarize the key findings and recurring issues as a bullet list, grouping similar reports together. Try to do it in less bullets, with a maximum of 5 concise bullet points.\n"
                "2. Provide separate bulleted recommendations for developers.\n"
                "3. Provide separate bulleted recommendations for testers.\n"
                "4. Add a one or two sentence potential customer impact description.\n"
                "5. Rate the customer impact as HIGH, MEDIUM, or LOW, depending on how much a customer can be affected. HIGH means that the customers can no longer use the software, MEDIUM means that their usage will be heavily impeded but still doable, while LOW means that it will be a minor annoyance.\n"
                "Respond in Markdown format, use clear section markers, do not ever respond in any other way:\n"
                "## Summary\n(bulleted list)\n\n"
                "## Recommendations for Developers\n(bulleted list)\n\n"
                "## Recommendations for Testers\n(bulleted list)\n\n"
                "## Potential Customer Impact\n(one or two sentences)\n\n"
                "## Impact Level\n(Write: Impact: HIGH/MEDIUM/LOW)\n\n"
                + component_issues
        )
        messages = [
            {'role': 'system', 'content': "You are a helpful software QA expert."},
            {'role': 'user', 'content': prompt}
        ]
        summary_resp = ollama.chat(model=ollama_model, messages=messages).message.content

        # For debugging per component responses
        print("----Summary for " + component + "-----\n" + summary_resp)

        summary_md, dev_md, test_md, impact_desc_md, impact_rating = parse_llm_markdown(summary_resp)
        summary_html = markdown.markdown(summary_md)
        dev_html = markdown.markdown(dev_md)
        test_html = markdown.markdown(test_md)
        impact_desc_html = markdown.markdown(impact_desc_md)

        summaries.append({
            'component': component,
            'summary': summary_html,
            'dev_recs': dev_html,
            'test_recs': test_html,
            'impact_desc': impact_desc_html,
            'impact': impact_rating
        })
    return overall_text, summaries
