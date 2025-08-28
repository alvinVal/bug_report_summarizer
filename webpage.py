import re


def strip_html_tags(text):
    return re.sub(r'<[^>]*>', '', text or '').strip()


def generate_singular_overall_summary(project_overall_summaries):
    combined_md = "## Combined Summary\n"
    for project, fields in project_overall_summaries.items():
        combined_md += f"### Project {project}\n"
        summary = fields.get('summary', '')
        impact = fields.get('customer_impact', '')
        if summary:
            combined_md += summary.strip() + "\n"
        if impact:
            combined_md += f"**Customer Impact:** {impact.strip()}\n"
        combined_md += "\n"
    try:
        import markdown
        return markdown.markdown(combined_md)
    except ImportError:
        return combined_md


def build_html_report(project_overall_summaries, project_component_summaries, output_dir):
    """
    Assembles all per-project and per-component summaries in a single table,
    with merged (rowspan) project cells, sorted by descending impact, and with component hyperlinks.
    """
    html = '''
    <html>
    <head>
      <meta charset="UTF-8">
      <title>Bug Report Summary</title>
      <style>
        body {
          font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
          margin: 40px;
          background: #f1f3f6;
        }
        .summary-box {
          background: #004080;
          color: #fff;
          padding: 24px;
          border-radius: 12px;
          margin-bottom: 36px;
          font-size: 18px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        table {
          width: 100%;
          border-collapse: collapse;
          background: #fff;
          margin-bottom: 20px;
          border: 1px solid #ddd;
          box-shadow: 0px 2px 4px rgba(0,0,0,0.1);
        }
        th, td {
          padding: 14px 12px;
          border: 1px solid #e3e3e3;
          vertical-align: top;
          white-space: pre-wrap;
        }
        td.component-name {
          vertical-align: middle;
        }
        th {
          background: #29384a;
          color: #fff;
          font-weight: bold;
        }
        tr:hover td {
          background: #eef2f6;
        }
        .impact {
          font-weight: bold;
          color: #fff;
          border-radius: 8px;
          padding: 4px 12px;
          display: inline-block;
        }
        .impact-high {
          background: #d9534f;
        }
        .impact-medium {
          background: #f0ad4e;
        }
        .impact-low {
          background: #5cb85c;
        }
        .impact-default {
          background: #777;
        }
      </style>
    </head>
    <body>
    '''
    # 1. SINGLE OVERALL SUMMARY BOX
    singular_summary_html = generate_singular_overall_summary(project_overall_summaries)
    html += f'<div class="summary-box">{singular_summary_html}</div>\n'

    # 2. Prepare sorted rows project-by-project, keeping their order for rendering
    impact_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    # For keeping merged rows, collect: {project: [ (component, fields, impact_plain) ]}
    project_rows = {}
    for project, comp_summaries in project_component_summaries.items():
        rows = []
        for comp, fields in comp_summaries.items():
            # Parse/plain the impact
            field_val = fields.get("impact_level", "")
            text = strip_html_tags(field_val)
            impact_plain = text.splitlines()[0].strip().upper() if text else "N/A"
            if not impact_plain:
                impact_plain = "N/A"
            rows.append((comp, fields, impact_plain))
        # Sort within project
        rows = sorted(rows, key=lambda tup: impact_order.get(tup[2], 0), reverse=True)
        project_rows[project] = rows

    # 3. Final rendering: single table, merged project cells, sorted within project
    html += '<table>\n<thead>\n<tr>\n'
    html += '<th>Project</th>\n'
    html += '<th>Component</th>\n'
    html += '<th>Summary of Issues</th>\n'
    html += '<th>Recommendations for Developers</th>\n'
    html += '<th>Recommendations for Testers</th>\n'
    html += '<th>Potential Customer Impact</th>\n'
    html += '<th>Impact Level</th>\n'
    html += '</tr>\n</thead>\n<tbody>\n'

    for project, rows in project_rows.items():
        rowspan = len(rows)
        first = True
        for comp, fields, impact_plain in rows:
            html += '<tr>\n'
            # Only output <td rowspan=...> for this project on the first component row
            if first:
                html += f'<td rowspan="{rowspan}">{project}</td>\n'
                first = False

            csv_path = f'{output_dir}/{project}_{strip_html_tags(comp).replace(" ", "_").replace("/", "_")}.csv'

            html += f'<td class="component-name"><a href="{csv_path}">{strip_html_tags(comp)}</a></td>\n'
            html += f'<td>{fields.get("summary", "N/A")}</td>\n'
            html += f'<td>{fields.get("rec_devs", "N/A")}</td>\n'
            html += f'<td>{fields.get("rec_testers", "N/A")}</td>\n'
            html += f'<td>{fields.get("customer_impact", "N/A")}</td>\n'

            # Color for impact
            impact_class = "impact-default"
            if impact_plain == "HIGH":
                impact_class = "impact-high"
            elif impact_plain == "MEDIUM":
                impact_class = "impact-medium"
            elif impact_plain == "LOW":
                impact_class = "impact-low"
            html += f'<td><span class="impact {impact_class}">{impact_plain}</span></td>\n'
            html += '</tr>\n'

    html += '</tbody>\n</table>\n'
    html += '</body>\n</html>'
    return html
