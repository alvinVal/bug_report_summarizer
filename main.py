import os
import webbrowser
from preprocess import load_and_preprocess, split_by_component
from ollama_functions import generate_summary_table
from webpage import build_html_report

# For faster outputs
OLLAMA_MODEL = 'llama3.1:8b'

if __name__ == '__main__':
    csv_filepath = 'dummy_data.csv'
    component_cols = ['Component/s', 'Component/s.1', 'Component/s.2']

    # Load CSV and create separate data frames for each of the components
    all_df = load_and_preprocess(csv_filepath, component_cols)
    component_dfs = split_by_component(all_df)

    # Begin prompting for per component summaries and overall summary
    overall, per_component = generate_summary_table(all_df, component_dfs, OLLAMA_MODEL)
    # Generate the HTML report
    html_report = build_html_report(overall, per_component)

    # Save and open in browser
    output_file = 'bug_report_summary.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_report)
    path = os.path.abspath(output_file)
    webbrowser.open(f'file://{path}')
