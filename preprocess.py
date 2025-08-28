import pandas as pd
import os


def load_and_preprocess(csv_path, component_cols, project_col):
    """
    Reads CSV, handles multi-project reports, converts dates, cleans component names,
    and prepares the data for all downstream processing.
    """
    df = pd.read_csv(csv_path)

    # --- Step 1: Ensure required columns exist ---
    if project_col not in df.columns:
        raise ValueError(f"Project column '{project_col}' not found in CSV.")
    if 'Created' not in df.columns:
        raise ValueError("'Created' column not found, which is required for time-series graphs.")

    # --- Step 2: Convert date column, coercing errors to NaT (Not a Time) ---
    df['Created'] = pd.to_datetime(df['Created'], errors='coerce')
    df.dropna(subset=['Created'], inplace=True)  # Drop rows where date conversion failed

    # --- Step 3: Handle multi-project reports by duplicating rows ---
    df[project_col] = df[project_col].apply(
        lambda x: [p.strip() for p in str(x).split(',')] if pd.notna(x) else []
    )
    df = df.explode(project_col)

    # --- Step 4: Handle and clean component column ---
    comp_col_name = component_cols[0] if component_cols and component_cols[0] in df.columns else 'All_Components'
    if comp_col_name not in df.columns:
        df[comp_col_name] = 'General'

    df[comp_col_name] = df[comp_col_name].fillna('General')
    df[comp_col_name] = df[comp_col_name].apply(lambda x: 'General' if str(x).strip() == '' else x)

    # Function to clean component names based on the project code in its row
    def clean_row_components(row):
        project_prefix = f"{row[project_col]}_"
        component_string = str(row[comp_col_name])

        cleaned_list = [
            comp.strip().replace(project_prefix, '')
            for comp in component_string.split(',')
        ]
        return [c if c else 'General' for c in cleaned_list]

    # Create a new column with the cleaned list of components
    df['All_Components_List'] = df.apply(clean_row_components, axis=1)

    # Create the original comma-separated string version for splitting logic
    df['All_Components'] = df['All_Components_List'].apply(lambda x: ', '.join(x))

    df.reset_index(drop=True, inplace=True)
    return df


def split_by_project_and_component(df, project_col, output_dir):
    """
    Groups data by project and component using the pre-cleaned 'All_Components'
    field, saves a CSV for each group, and returns a nested dictionary of DataFrames.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    project_component_dfs = {}

    # Group by the exploded project column.
    for project in df[project_col].unique():
        project_df = df[df[project_col] == project].copy()

        # Get unique components from the pre-cleaned list column
        components = project_df.explode('All_Components_List')['All_Components_List'].unique()

        project_component_dfs[project] = {}
        for comp in components:
            if not comp: continue

            # Filter rows where the component is in our list of components for that row
            mask = project_df['All_Components_List'].apply(lambda lst: comp in lst)
            sub_df = project_df[mask].copy()

            # Prepare a version for CSV export without the list-based column
            sub_df_for_csv = sub_df.drop(columns=['All_Components_List', 'All_Components'])

            safe_project = str(project)
            safe_comp = comp.replace(" ", "_").replace("/", "_")
            csv_filename = f'{safe_project}_{safe_comp}.csv'
            csv_path = os.path.join(output_dir, csv_filename)
            sub_df_for_csv.to_csv(csv_path, index=False)

            project_component_dfs[project][comp] = sub_df

    return project_component_dfs