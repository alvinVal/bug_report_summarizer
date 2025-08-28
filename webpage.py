import re


def strip_html_tags(text):
    return re.sub(r'<[^>]*>', '', text or '').strip()


def build_html_report(project_overall_summaries, project_component_summaries, output_dir):
    """
    Build an HTML report with these changes:
      • Overall project summary displays only Summary and Potential Customer Impact.
      • In the table of component summaries, the Component name is vertically centered.
      • The Impact Level remains trimmed and color-coded.
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
        .project-section {
          margin-bottom: 60px;
        }
        .project-code {
          font-size: 26px;
          font-weight: bold;
          color: #fff;
          background: linear-gradient(135deg, #0072ff, #00c6ff);
          padding: 12px 20px;
          border-radius: 8px;
          box-shadow: 0px 4px 6px rgba(0,0,0,0.2);
          display: inline-block;
          margin-bottom: 20px;
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
        /* Center the component name vertically */
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
    # Define sorting order for impact.
    impact_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}

    def comp_sort_key(item):
        field_val = item[1].get("impact_level", "")
        text = strip_html_tags(field_val)
        line = text.splitlines()[0].strip().upper() if text else "N/A"
        return impact_order.get(line, 0)

    for project, overall_fields in project_overall_summaries.items():
        html += '<div class="project-section">\n'
        # Emphasized project code.
        html += f'<div class="project-code">Project {project}</div>\n'
        html += '<div class="summary-box">\n'
        html += f"<strong>Overall Summary:</strong> {overall_fields.get('summary', 'N/A')}<br>\n"
        html += f"<strong>Potential Customer Impact:</strong> {overall_fields.get('customer_impact', 'N/A')}<br>\n"
        html += '</div>\n'
        html += '<table>\n<thead>\n<tr>\n'
        html += '<th>Component</th>\n'
        html += '<th>Summary of Issues</th>\n'
        html += '<th>Recommendations for Developers</th>\n'
        html += '<th>Recommendations for Testers</th>\n'
        html += '<th>Potential Customer Impact</th>\n'
        html += '<th>Impact Level</th>\n'
        html += '</tr>\n</thead>\n<tbody>\n'

        comp_summaries = project_component_summaries.get(project, {})
        sorted_components = sorted(comp_summaries.items(), key=comp_sort_key, reverse=True)

        for comp, fields in sorted_components:

            csv_path = f'{output_dir}/{project}_{strip_html_tags(comp).replace(" ", "_").replace("/", "_")}.csv'

            html += '<tr>\n'
            html += f'<td class="component-name"><a href="{csv_path}">{strip_html_tags(comp)}</a></td>\n'
            html += f'<td>{fields.get("summary", "N/A")}</td>\n'
            html += f'<td>{fields.get("rec_devs", "N/A")}</td>\n'
            html += f'<td>{fields.get("rec_testers", "N/A")}</td>\n'
            html += f'<td>{fields.get("customer_impact", "N/A")}</td>\n'

            # Process Impact Level.
            field_val = fields.get("impact_level", "N/A")
            text = strip_html_tags(field_val)
            impact_plain = text.splitlines()[0].strip().upper() if text else "N/A"
            if not impact_plain:
                impact_plain = "N/A"

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
        html += '</div>\n'
    html += '</body>\n</html>'
    return html

