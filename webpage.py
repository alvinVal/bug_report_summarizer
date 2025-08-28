import os

def build_html_report(project_overall_summaries, project_component_summaries, project_graphs, output_dir):
    """
    Builds an HTML report with a clean, multi-row dashboard layout for graphs,
    followed by the AI summary and the detailed component table.
    """
    html = '''
    <html>
    <head>
      <meta charset="UTF-8">
      <title>Bug Report Summary</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
      <style>
        body {
          font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
          margin: 0;
          background: #f1f3f6;
          color: #333;
        }
        .project-section {
          background: #fff;
          border-radius: 16px;
          box-shadow: 0 8px 16px rgba(0,0,0,0.05);
          margin-bottom: 60px;
          overflow: hidden;
        }
        .project-header {
          font-size: 28px;
          font-weight: bold;
          color: #fff;
          background: linear-gradient(135deg, #0072ff, #00c6ff);
          padding: 20px 30px;
        }
        .dashboard, .summary-section, .table-section {
          padding: 30px;
        }
        .section-title {
          font-size: 22px;
          font-weight: 600;
          color: #29384a;
          margin-bottom: 24px;
          border-bottom: 2px solid #ddd;
          padding-bottom: 8px;
        }
        .graph-title {
          font-size: 18px;
          font-weight: 600;
          color: #29384a;
          text-align: center;
          margin-bottom: 15px;
        }
        .graph-box {
          border: 1px solid #e3e3e3;
          border-radius: 12px;
          padding: 20px;
          box-shadow: 0 4px 8px rgba(0,0,0,0.05);
          height: 100%;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: flex-start;
        }
        .graph-box img {
          max-width: 100%;
          max-height: 100%;
          height: auto;
          border-radius: 8px;
        }
        .summary-box {
          background: #004080;
          color: #fff;
          padding: 24px;
          border-radius: 12px;
          font-size: 16px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        .summary-box h3 { margin-top: 0; }
        table {
          width: 100%;
          border-collapse: collapse;
          background: #fff;
          margin-top: 20px;
        }
        th, td {
          padding: 14px 12px;
          border: 1px solid #e3e3e3;
          vertical-align: top;
          white-space: pre-wrap;
          text-align: left;
        }
        td.component-name { vertical-align: middle; font-weight: bold; }
        th { background: #29384a; color: #fff; font-weight: bold; }
        tr:hover td { background: #eef2f6; }
        .impact {
          font-weight: bold; color: #fff; border-radius: 8px;
          padding: 4px 12px; display: inline-block; text-align: center;
        }
        .impact-high { background: #d9534f; }
        .impact-medium { background: #f0ad4e; }
        .impact-low { background: #5cb85c; }
        .impact-default { background: #777; }
      </style>
    </head>
    <body><div class="container-fluid p-5">
    '''
    impact_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}

    def comp_sort_key(item):
        line = item[1].get("impact_level", "").strip().upper()
        return impact_order.get(line, 0)

    for project, overall_fields in project_overall_summaries.items():
        graphs = project_graphs.get(project, {})
        html += '<div class="project-section">\n'
        html += f'<div class="project-header">Project {project}</div>\n'

        # --- Graphs Dashboard Section ---
        html += '<div class="dashboard">\n'
        html += '<div class="section-title">Project Health Dashboard</div>\n'

        # --- Bootstrap Grid for Graphs ---
        html += '<div class="row g-4">\n'

        # --- Row 1: Bar and Pie Charts Side-by-Side ---
        html += '<div class="col-md-7">\n'
        html += f'''<div class="graph-box">
                       <div class="graph-title">Bug Reports per Component</div>
                       <img src="{graphs.get("reports_per_component", "")}" alt="Reports per Component Graph">
                     </div>'''
        html += '</div>\n'
        html += '<div class="col-md-5">\n'
        html += f'''<div class="graph-box">
                       <div class="graph-title">Report Resolutions</div>
                       <img src="{graphs.get("resolution_pie", "")}" alt="Resolutions Pie Chart">
                     </div>'''
        html += '</div>\n'

        # --- Row 2: Priority Chart (Full Width) ---
        html += '<div class="col-12">\n'
        html += f'''<div class="graph-box">
                       <div class="graph-title">Priority Distribution per Component</div>
                       <img src="{graphs.get("priority_chart", "")}" alt="Priority Chart">
                     </div>'''
        html += '</div>\n'

        # --- Row 3: Severity Chart (Full Width) ---
        html += '<div class="col-12">\n'
        html += f'''<div class="graph-box">
                       <div class="graph-title">Severity Distribution per Component</div>
                       <img src="{graphs.get("severity_chart", "")}" alt="Severity Chart">
                     </div>'''
        html += '</div>\n'

        # --- Row 4: Time Series Chart (Full Width) ---
        html += '<div class="col-12">\n'
        html += f'''<div class="graph-box">
                       <div class="graph-title">New Reports Over Time (All Components)</div>
                       <img src="{graphs.get("reports_over_time", "")}" alt="Reports Over Time Graph">
                     </div>'''
        html += '</div>\n'

        html += '</div>\n</div>\n'

        # --- AI Summary Section ---
        html += '<div class="summary-section">\n'
        html += '<div class="section-title">AI Generated Summary</div>\n'
        html += '<div class="summary-box">\n'
        html += f"<h3>Overall Summary</h3>{overall_fields.get('summary', 'N/A')}\n"
        html += f"<h3>Potential Customer Impact</h3>{overall_fields.get('customer_impact', 'N/A')}\n"
        html += '</div>\n</div>\n'

        # --- Detailed Table Section ---
        html += '<div class="table-section">\n'
        html += '<div class="table-responsive">\n'
        html += '<table class="table table-bordered table-hover">\n<thead>\n<tr>\n'
        html += '<th>Component</th><th>Summary of Issues</th><th>Recommendations for Developers</th>'
        html += '<th>Recommendations for Testers</th><th>Potential Customer Impact</th><th>Impact Level</th>\n'
        html += '</tr>\n</thead>\n<tbody>\n'

        comp_summaries = project_component_summaries.get(project, {})
        sorted_components = sorted(comp_summaries.items(), key=comp_sort_key, reverse=True)

        for comp, fields in sorted_components:
            csv_path = f'{output_dir}/{project}_{comp.replace(" ", "_").replace("/", "_")}.csv'
            html += '<tr>\n'
            html += f'<td class="component-name"><a href="file://{os.path.abspath(csv_path)}">{comp}</a></td>\n'
            html += f'<td>{fields.get("summary", "N/A")}</td>\n'
            html += f'<td>{fields.get("rec_devs", "N/A")}</td>\n'
            html += f'<td>{fields.get("rec_testers", "N/A")}</td>\n'
            html += f'<td>{fields.get("customer_impact", "N/A")}</td>\n'

            impact_plain = fields.get("impact_level", "N/A").strip().upper()
            impact_class = "impact-default"
            if impact_plain == "HIGH":
                impact_class = "impact-high"
            elif impact_plain == "MEDIUM":
                impact_class = "impact-medium"
            elif impact_plain == "LOW":
                impact_class = "impact-low"

            html += f'<td><span class="impact {impact_class}">{impact_plain or "N/A"}</span></td>\n'
            html += '</tr>\n'

        html += '</tbody>\n</table>\n</div>\n</div>\n'
        html += '</div>\n'

    html += '</div><script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script></body>\n</html>'

    return html