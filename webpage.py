def impact_color(impact):
    impact = str(impact).lower()
    if impact == "high":
        return "#FF0000"  # Red for high impact
    elif impact == "medium":
        return "#FFA500"  # Orange for medium impact
    elif impact == "low":
        return "#00FF00"  # Green for low impact
    else:
        return "#CCCCCC"  # Default grey


def build_html_report(overall_summary, summaries, components_dir='/component_csvs'):
    js_function = """
    <script>
    function openCSVPage(csvFile) {
      var newWindow = window.open("", "_blank");
      var newHtml = `
        <!DOCTYPE html>
        <html lang="en">
          <head>
            <meta charset="UTF-8">
            <title>Component Bug Reports</title>
            <style>
              body { font-family: Arial, sans-serif; margin: 40px; background: #f9f9f9; }
              table { width: 100%; border-collapse: collapse; background: #fff; }
              th, td { padding: 10px; border: 1px solid #ccc; }
              tr:hover td { background: #eef2f6; }
            </style>
            <script>
              document.addEventListener("DOMContentLoaded", function(){
                fetch(csvFile)
                  .then(response => response.text())
                  .then(data => {
                    // Notice the correct escaped newline: '\\n'
                    var rowData = data.split('\\n');
                    var table = document.getElementById('tblcsvdata');
                    var tbody = table.querySelector('tbody');
                    rowData.forEach(function(row) {
                      if(row.trim() !== '') {
                        var cols = row.split(',');
                        var tr = document.createElement('tr');
                        cols.forEach(function(col) {
                          var td = document.createElement('td');
                          td.textContent = col;
                          tr.appendChild(td);
                        });
                        tbody.appendChild(tr);
                      }
                    });
                  })
                  .catch(error => console.error('Error loading CSV:', error));
              });
            <\/script>
          </head>
          <body>
            <h2>Bug Reports for the Selected Component</h2>
            <table id="tblcsvdata">
              <thead></thead>
              <tbody></tbody>
            </table>
          </body>
        </html>
      `;
      console.log("Generated HTML:", newHtml);
      newWindow.document.write(newHtml);
      newWindow.document.close();
    }
    </script>
    """

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Bug Report Summary</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 40px;
                background: #f9f9f9;
            }}
            .summary-box {{
                background: #004080;
                color: #fff;
                padding: 24px;
                border-radius: 12px;
                margin-bottom: 36px;
                font-size: 18px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.07);
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                background: #fff;
            }}
            th, td {{
                padding: 14px 10px;
                border-bottom: 1px solid #e3e3e3;
                vertical-align: top;
            }}
            th {{
                background: #29384a;
                color: #fff;
                font-weight: bold;
            }}
            tr:hover td {{
                background: #eef2f6;
            }}
            .impact {{ 
                font-weight: bold; 
                color: #fff; 
                border-radius: 8px; 
                padding: 4px 12px; 
                display: inline-block; 
            }}
            .center-fallback {{ 
                text-align: center; 
                color: #555; 
                font-style: italic; 
                padding: 20px; 
            }}
        </style>
        {js_function}
    </head>
    <body>
        <div class="summary-box">
            <h2>Overall Summary</h2>
            {overall_summary}
        </div>
        <table>
            <thead>
              <tr>
                <th>Component</th>
                <th>Summary of Issues</th>
                <th>Recommendations for Developers</th>
                <th>Recommendations for Testers</th>
                <th>Potential Customer Impact</th>
                <th>Impact Level</th>
              </tr>
            </thead>
            <tbody>
    """

    # Define an order for impact levels: highest first.
    impact_order = {"high": 3, "medium": 2, "low": 1}
    # Sort the summaries in descending order based on the defined impact level.
    sorted_summaries = sorted(
        summaries,
        key=lambda x: impact_order.get(x.get("impact", "").lower(), 0),
        reverse=True
    )

    for s in sorted_summaries:
        component = s['component']
        csv_path = f'{components_dir}/{component.replace(" ", "_").replace("/", "_")}.csv'
        component_link = f'<a href="#" onclick="openCSVPage(\'{csv_path}\')">{component}</a>'

        if not s.get("summary") or not str(s.get("summary")).strip():
            fallback_msg = (
                "Summary unavailable, there are too many or too varied bug reports under this component for a concise overview. "
                "Consider using more specific labels."
            )
            html_row = f'''
                <tr>
                    <td><b>{component_link}</b></td>
                    <td colspan="5" class="center-fallback">{fallback_msg}</td>
                </tr>
            '''
        else:
            color = impact_color(s.get('impact', ''))
            html_row = f'''
                <tr>
                    <td><b>{component_link}</a></b></td>
                    <td>{s.get("summary", "")}</td>
                    <td>{s.get("dev_recs", "")}</td>
                    <td>{s.get("test_recs", "")}</td>
                    <td>{s.get("impact_desc", "")}</td>
                    <td><span class="impact" style="background:{color};">{str(s.get("impact", "")).title()}</span></td>
                </tr>
            '''
        html += html_row

    html += """
                </tbody>
            </table>
        </body>
    </html>
    """
    return html


if __name__ == "__main__":
    overall = "This report summarizes the status of bug reports for various components."
    per_component = [
        {
            "component": "BB",
            "summary": "Endpoints are stable, with minor latency issues resolved.",
            "dev_recs": "Review caching strategies.",
            "test_recs": "Add latency testing.",
            "impact_desc": "Minimal customer impact.",
            "impact": "low"
        },
        {
            "component": "UI",
            "summary": "",  # Simulating a missing/empty summary for "UI"
            "impact": "high"
        },
        {
            "component": "DD",
            "summary": "Authentication and database errors fixed in the latest patch.",
            "dev_recs": "Monitor long-term performance.",
            "test_recs": "Perform stress tests.",
            "impact_desc": "Stable service.",
            "impact": "medium"
        }
    ]

    html_report = build_html_report(overall, per_component)

    with open('test_summary.html', 'w', encoding='utf-8') as f:
        f.write(html_report)

    print("Bug Report Summary HTML generated successfully.")