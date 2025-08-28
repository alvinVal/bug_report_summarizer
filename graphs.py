import plotly.express as px
import pandas as pd

# --- TROUBLESHOOTING ---
# Set this to True to display each chart in a pop-up window as it's created.
# Set it to False for normal operation.
SHOW_CHARTS_FOR_DEBUG = False

# Define a consistent and pleasing color scheme for the charts.
PLOTLY_TEMPLATE = "seaborn"
PROJECT_COLORS = px.colors.qualitative.Vivid


def generate_reports_per_component_bar(project_df, project_code):
    """Generates a horizontal bar chart of report counts per component."""
    if 'All_Components_List' not in project_df.columns:
        return ""

    component_counts = project_df.explode('All_Components_List')['All_Components_List'].value_counts().reset_index()
    component_counts.columns = ['Component', 'Count']
    component_counts = component_counts.sort_values('Count', ascending=True)

    fig = px.bar(
        component_counts,
        x='Count',
        y='Component',
        orientation='h',
        title=f'Bug Reports per Component for Project {project_code}',
        labels={'Count': 'Number of Reports', 'Component': 'Component'},
        template=PLOTLY_TEMPLATE,
        color_discrete_sequence=['#0072ff']
    )
    # Ensure title and axis labels are centered
    fig.update_layout(
        title_x=0.5,
        xaxis_title_standoff=15,
        yaxis_title_standoff=15,
        margin=dict(t=50, b=20, l=20, r=20),
        yaxis={'categoryorder': 'total ascending'}
    )

    if SHOW_CHARTS_FOR_DEBUG:
        fig.show()

    return fig.to_html(full_html=False, include_plotlyjs=False)


def generate_resolution_pie(project_df, project_code):
    """Generates a pie chart of report resolutions with correct hover data."""
    resolution_counts = project_df['Resolution'].value_counts().reset_index()
    resolution_counts.columns = ['Resolution', 'Count']

    fig = px.pie(
        names=resolution_counts['Resolution'],
        values=resolution_counts['Count'],
        title=f'Report Resolutions for Project {project_code}',
        template=PLOTLY_TEMPLATE,
        color_discrete_sequence=px.colors.qualitative.Set2,
        hole=0.3
    )
    fig.update_traces(
        textinfo='percent+label',
        pull=[0.05, 0, 0, 0],
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
    )
    fig.update_layout(
        title_x=0.5,
        margin=dict(t=50, b=20, l=20, r=20),
        legend_title_text='Resolution Status'
    )

    if SHOW_CHARTS_FOR_DEBUG:
        fig.show()

    return fig.to_html(full_html=False, include_plotlyjs=False)


def generate_grouped_bar_chart(project_df, project_code, group_col):
    """Generates a grouped bar chart for Priority or Severity per component."""
    if 'All_Components_List' not in project_df.columns:
        return ""

    data = project_df.explode('All_Components_List').groupby(['All_Components_List', group_col]).size().reset_index(
        name='Count')
    data.rename(columns={'All_Components_List': 'Component'}, inplace=True)

    category_orders = {
        "Priority": ["Minor", "Major", "High", "Critical", "Blocker"],
        "Severity": ["Low", "Medium", "High", "Critical"]
    }

    fig = px.bar(
        data,
        x='Component',
        y='Count',
        color=group_col,
        barmode='group',
        title=f'{group_col} Distribution per Component',
        template=PLOTLY_TEMPLATE,
        color_discrete_sequence=px.colors.qualitative.Bold,
        category_orders={group_col: category_orders.get(group_col, [])}
    )
    fig.update_layout(title_x=0.5, margin=dict(t=50, b=20, l=20, r=20))

    if SHOW_CHARTS_FOR_DEBUG:
        fig.show()

    return fig.to_html(full_html=False, include_plotlyjs=False)


def generate_reports_over_time_line(project_df, project_code):
    """Generates a line chart of new reports per month for each component."""
    if 'All_Components_List' not in project_df.columns or 'Created' not in project_df.columns:
        return ""

    df_time = project_df.explode('All_Components_List').copy()

    monthly_counts = df_time.groupby(
        ['All_Components_List', pd.Grouper(key='Created', freq='ME')]
    ).size().reset_index(name='Count')

    monthly_counts.rename(columns={'All_Components_List': 'Component'}, inplace=True)

    fig = px.line(
        monthly_counts,
        x='Created',
        y='Count',
        color='Component',
        markers=True,
        title=f'New Reports per Month for Project {project_code}',
        labels={'Created': 'Month', 'Count': 'Number of New Reports'},
        template=PLOTLY_TEMPLATE,
        color_discrete_sequence=PROJECT_COLORS
    )
    fig.update_layout(title_x=0.5, margin=dict(t=50, b=20, l=20, r=20))

    if SHOW_CHARTS_FOR_DEBUG:
        fig.show()

    return fig.to_html(full_html=False, include_plotlyjs=False)