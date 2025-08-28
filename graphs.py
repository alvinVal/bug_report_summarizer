import matplotlib
# This must be done BEFORE importing pyplot to avoid threading issues in the GUI.
matplotlib.use('Agg')

import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
import base64
from io import BytesIO

# --- TROUBLESHOOTING ---
# Set this to True to display each chart in a pop-up window as it's created.
SHOW_CHARTS_FOR_DEBUG = False

# Define a consistent and pleasing color scheme for the charts.
sns.set_theme(style="whitegrid", palette="viridis")


def _save_fig_to_base64():
    """Saves the current matplotlib figure to a base64 encoded string."""
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches='tight')
    plt.close()  # Close the figure to free memory
    return "data:image/png;base64," + base64.b64encode(buf.getbuffer()).decode("ascii")


def generate_reports_per_component_bar(project_df):
    """Generates a horizontal bar chart of report counts per component using Seaborn."""
    if 'All_Components_List' not in project_df.columns:
        return ""

    component_counts = project_df.explode('All_Components_List')['All_Components_List'].value_counts().reset_index()
    component_counts.columns = ['Component', 'Count']

    plt.figure(figsize=(10, 6))
    ax = sns.barplot(
        data=component_counts,
        x='Count',
        y='Component',
        hue='Component',
        legend=False,
        orient='h',
        palette='viridis'
    )
    ax.set_xlabel('Number of Reports', fontsize=12)
    ax.set_ylabel('Component', fontsize=12)

    if SHOW_CHARTS_FOR_DEBUG:
        plt.show()

    return _save_fig_to_base64()


def generate_resolution_pie(project_df):
    """Generates a pie chart of report resolutions with an external legend."""
    resolution_counts = project_df['Resolution'].value_counts()

    colors = sns.color_palette('plasma', len(resolution_counts))

    plt.figure(figsize=(8, 6))

    total = resolution_counts.sum()
    labels_with_pct = [f'{label} ({count / total:.1%})' for label, count in resolution_counts.items()]

    wedges, texts = plt.pie(
        resolution_counts,
        startangle=140,
        colors=colors,
        wedgeprops={'edgecolor': 'white'}
    )

    plt.legend(
        wedges,
        labels_with_pct,
        title="Resolutions",
        loc="center left",
        bbox_to_anchor=(0.9, 0, 0.5, 1)
    )
    plt.ylabel('')

    if SHOW_CHARTS_FOR_DEBUG:
        plt.show()

    return _save_fig_to_base64()


def generate_grouped_bar_chart(project_df, group_col):
    """Generates a grouped bar chart for Priority or Severity per component using Seaborn."""
    if 'All_Components_List' not in project_df.columns:
        return ""

    data = project_df.explode('All_Components_List').groupby(['All_Components_List', group_col]).size().reset_index(
        name='Count')
    data.rename(columns={'All_Components_List': 'Component'}, inplace=True)

    category_orders = {
        "Priority": ["Minor", "Major", "High", "Critical", "Blocker"],
        "Severity": ["Low", "Medium", "High", "Critical"]
    }

    plt.figure(figsize=(12, 7))
    ax = sns.barplot(
        data=data,
        x='Component',
        y='Count',
        hue=group_col,
        palette='magma',
        hue_order=category_orders.get(group_col)
    )
    ax.set_xlabel('Component', fontsize=12)
    ax.set_ylabel('Count', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.legend(title=group_col)

    if SHOW_CHARTS_FOR_DEBUG:
        plt.show()

    return _save_fig_to_base64()


def generate_reports_over_time_line(project_df):
    """Generates a line chart of new reports per month for the entire project."""
    if 'Created' not in project_df.columns:
        return ""

    df_time = project_df.copy()

    monthly_counts = df_time.groupby(
        pd.Grouper(key='Created', freq=pd.offsets.MonthEnd())
    ).size().reset_index(name='Count')

    plt.figure(figsize=(12, 6))
    ax = sns.lineplot(
        data=monthly_counts,
        x='Created',
        y='Count',
        marker='o',
        color='#0072ff'
    )
    ax.set_xlabel('Month', fontsize=12)
    ax.set_ylabel('Number of New Reports', fontsize=12)
    plt.xticks(rotation=45, ha='right')

    if SHOW_CHARTS_FOR_DEBUG:
        plt.show()

    return _save_fig_to_base64()