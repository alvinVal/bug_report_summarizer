import os
import webbrowser
from preprocess import load_and_preprocess, split_by_project_and_component
from ollama_functions import generate_summary_table
from webpage import build_html_report
from graphs import (
    generate_reports_per_component_bar,
    generate_resolution_pie,
    generate_grouped_bar_chart,
    generate_reports_over_time_line,
)


OLLAMA_MODEL = 'llama3.1:8b'
CHUNK_SIZE = 5

if __name__ == '__main__':
    csv_filepath = 'project_data.csv'
    component_cols = ['Component/s']
    project_col = 'Project List'
    output_dir = './project_component_csvs'

    # Preprocess data once for both graphing and AI summaries.
    all_df = load_and_preprocess(csv_filepath, component_cols, project_col)

    # --- Generate all graphs for each project ---
    project_graphs = {}
    for project_code in all_df[project_col].unique():
        project_df = all_df[all_df[project_col] == project_code]
        project_graphs[project_code] = {
            'reports_per_component': generate_reports_per_component_bar(project_df, project_code),
            'resolution_pie': generate_resolution_pie(project_df, project_code),
            'priority_chart': generate_grouped_bar_chart(project_df, project_code, 'Priority'),
            'severity_chart': generate_grouped_bar_chart(project_df, project_code, 'Severity'),
            'reports_over_time': generate_reports_over_time_line(project_df, project_code),
        }

    # Split data and save component-level CSVs.
    project_component_dfs = split_by_project_and_component(all_df, project_col, output_dir)

    # Generate AI summaries.
    project_overall_summaries, project_component_summaries = generate_summary_table(
        all_df, project_component_dfs, project_col, OLLAMA_MODEL, CHUNK_SIZE
    )

    # Build the HTML report with summaries and graphs.
    html_report = build_html_report(
        project_overall_summaries,
        project_component_summaries,
        project_graphs, # Pass graphs to the report builder
        output_dir
    )

    # Save and open the report.
    output_file = 'bug_report_summary.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_report)

    path = os.path.abspath(output_file)
    webbrowser.open(f'file://{path}')