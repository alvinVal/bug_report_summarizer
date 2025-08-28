import os
import webbrowser
from preprocess import load_and_preprocess, split_by_project_and_component
from ollama_functions import generate_summary_table
from webpage import build_html_report

# For faster outputs
OLLAMA_MODEL = 'llama3.1:8b'


if __name__ == '__main__':
    csv_filepath = 'project_data.csv'
    component_cols = ['Component/s', 'Component/s.1', 'Component/s.2']
    project_col = 'Project Codes'  # New field indicating which product or project each report belongs to
    output_dir = './project_component_csvs' # Indicates where the output CSVs will be saved at

    # Load CSV data including the project field.
    all_df = load_and_preprocess(csv_filepath, component_cols, project_col)

    # Split the DataFrame into nested dictionaries by project and component.
    project_component_dfs = split_by_project_and_component(all_df, project_col,  output_dir)

    # Generate summaries.
    # The generate_summary_table function should be updated to process both overall project
    # summaries and per-component summaries within each project.
    project_overall_summaries, project_component_summaries = generate_summary_table(
        all_df, project_component_dfs, project_col, OLLAMA_MODEL
    )

    # Build the HTML report.
    html_report = build_html_report(project_overall_summaries, project_component_summaries,  output_dir)

    # Save the report as an HTML file and open in a browser.
    output_file = 'bug_report_summary.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_report)

    path = os.path.abspath(output_file)
    webbrowser.open(f'file://{path}')
