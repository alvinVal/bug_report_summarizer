import pandas as pd


def load_and_preprocess(csv_path, component_cols):
    df = pd.read_csv(csv_path)
    df['All_Components'] = df[component_cols].apply(
        lambda row: ', '.join(str(x).strip() for x in row if pd.notnull(x) and str(x).strip()), axis=1
    )
    df.drop(columns=component_cols, inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def split_by_component(df, output_dir='./component_csvs'):
    import os
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    unique_components = set()
    df['All_Components'].apply(
        lambda cell: [unique_components.add(component.strip()) for component in cell.split(',')] if cell else None
    )
    unique_components.discard('')  # Remove empty string if any

    component_dfs = {}

    for comp in unique_components:
        mask = df['All_Components'].str.split(r',\s*').apply(lambda lst: comp in lst)
        sub_df = df[mask].copy()
        sub_df.drop(columns=['All_Components'], inplace=True)
        safe_comp_name = comp.replace(" ", "_").replace("/", "_")
        csv_filename = f'{safe_comp_name}.csv'
        csv_path = os.path.join(output_dir, csv_filename)
        sub_df.to_csv(csv_path, index=False)
        component_dfs[comp] = sub_df

    return component_dfs
