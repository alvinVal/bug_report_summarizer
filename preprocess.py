import pandas as pd
import os


def load_and_preprocess(csv_path, component_cols, project_col):
    """
    Reads the CSV, combines component columns into an 'All_Components' field,
    and checks that the project column exists.
    """
    df = pd.read_csv(csv_path)
    # Combine the component columns into one comma-separated string.
    df['All_Components'] = df[component_cols].apply(
        lambda row: ', '.join(str(x).strip() for x in row
                              if pd.notnull(x) and str(x).strip()), axis=1
    )
    df.drop(columns=component_cols, inplace=True)
    df.reset_index(drop=True, inplace=True)

    # Ensure the project column exists.
    if project_col not in df.columns:
        raise ValueError(f"Project column '{project_col}' not found in CSV.")

    return df


def split_by_project_and_component(df, project_col, output_dir):
    """
    Groups the data first by project and then by each component within a project.
    For each (project, component) group, creates a CSV file and saves the subset.
    Returns a nested dictionary: { project: { component: DataFrame, ... }, ... }
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    project_component_dfs = {}
    # Group the data by project.
    for project in df[project_col].unique():
        project_df = df[df[project_col] == project].copy()
        components = set()
        project_df['All_Components'].apply(
            lambda cell: [components.add(c.strip()) for c in cell.split(',')] if cell else None
        )
        components.discard('')  # Remove empty strings

        # Initialize dictionary for the current project.
        project_component_dfs[project] = {}
        for comp in components:
            mask = project_df['All_Components'].str.split(r',\s*').apply(lambda lst: comp in lst)
            sub_df = project_df[mask].copy()
            sub_df.drop(columns=['All_Components'], inplace=True)

            # Create a safe filename for CSV output.
            safe_project = str(project)
            safe_comp = comp.replace(" ", "_").replace("/", "_")
            csv_filename = f'{safe_project}_{safe_comp}.csv'
            csv_path = os.path.join(output_dir, csv_filename)
            sub_df.to_csv(csv_path, index=False)

            project_component_dfs[project][comp] = sub_df

    return project_component_dfs
