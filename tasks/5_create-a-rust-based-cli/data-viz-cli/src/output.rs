use crate::charts::Chart;
use anyhow::Result;
use std::fs::File;
use std::io::Write;
use std::path::Path;

pub struct HtmlWriter {
    output_path: String,
}

impl HtmlWriter {
    pub fn new<P: AsRef<Path>>(path: P) -> Self {
        HtmlWriter {
            output_path: path.as_ref().to_string_lossy().to_string(),
        }
    }

    pub fn write(&self, chart: &Chart) -> Result<()> {
        let html = self.generate_html(chart)?;
        let mut file = File::create(&self.output_path)?;
        file.write_all(html.as_bytes())?;
        Ok(())
    }

    fn generate_html(&self, chart: &Chart) -> Result<String> {
        let chart_data = chart.get_chart_data();
        let chart_data_json = serde_json::to_string_pretty(&chart_data)?;
        let chart_type = chart.chart_type.as_str();
        let title = &chart.title;
        let width = chart.style.width;
        let height = chart.style.height;
        let show_legend = chart.style.show_legend;
        let enable_zoom = chart.style.enable_zoom;

        let x_label = chart.x_label.as_deref().unwrap_or("X Axis");
        let y_label = chart.y_label.as_deref().unwrap_or("Y Axis");

        Ok(format!(
            r#"<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/hammerjs@2.0.8/hammer.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}

        .container {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            padding: 30px;
            max-width: {width}px;
            width: 100%;
        }}

        h1 {{
            text-align: center;
            color: #333;
            margin-bottom: 20px;
            font-size: 28px;
            font-weight: 600;
        }}

        .chart-container {{
            position: relative;
            width: 100%;
            height: {height}px;
            margin: 20px 0;
        }}

        .controls {{
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-top: 20px;
            flex-wrap: wrap;
        }}

        button {{
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            background: #667eea;
            color: white;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
        }}

        button:hover {{
            background: #764ba2;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }}

        button:active {{
            transform: translateY(0);
        }}

        .info {{
            text-align: center;
            color: #666;
            margin-top: 20px;
            font-size: 14px;
        }}

        @media (max-width: 768px) {{
            .container {{
                padding: 20px;
            }}

            h1 {{
                font-size: 22px;
            }}

            .chart-container {{
                height: 400px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <div class="chart-container">
            <canvas id="myChart"></canvas>
        </div>
        <div class="controls">
            <button onclick="resetZoom()">Reset Zoom</button>
            <button onclick="downloadChart()">Download PNG</button>
            <button onclick="toggleLegend()">Toggle Legend</button>
        </div>
        <div class="info">
            <p>Scroll to zoom • Drag to pan • Click buttons to export</p>
        </div>
    </div>

    <script>
        const chartData = {chart_data_json};
        const ctx = document.getElementById('myChart').getContext('2d');

        let config;

        if ('{chart_type}' === 'scatter') {{
            config = {{
                type: 'scatter',
                data: {{
                    datasets: [{{
                        label: chartData.dataset_name,
                        data: chartData.x_data.map((x, i) => ({{
                            x: x,
                            y: chartData.y_data[i]
                        }})),
                        backgroundColor: chartData.colors[0],
                        borderColor: chartData.colors[0],
                        pointRadius: 8,
                        pointHoverRadius: 12
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            display: {show_legend},
                            position: 'top'
                        }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    return '(' + context.parsed.x.toFixed(2) + ', ' + context.parsed.y.toFixed(2) + ')';
                                }}
                            }}
                        }},
                        zoom: {{
                            zoom: {{
                                wheel: {{ enabled: {enable_zoom} }},
                                pinch: {{ enabled: {enable_zoom} }},
                                mode: 'xy'
                            }},
                            pan: {{
                                enabled: {enable_zoom},
                                mode: 'xy'
                            }}
                        }}
                    }},
                    scales: {{
                        x: {{
                            display: true,
                            title: {{
                                display: true,
                                text: '{x_label}'
                            }}
                        }},
                        y: {{
                            display: true,
                            title: {{
                                display: true,
                                text: '{y_label}'
                            }}
                        }}
                    }}
                }}
            }};
        }} else {{
            config = {{
                type: '{chart_type}',
                data: {{
                    labels: chartData.labels,
                    datasets: [{{
                        label: chartData.dataset_name,
                        data: chartData.data,
                        backgroundColor: chartData.colors[0],
                        borderColor: chartData.colors[0],
                        borderWidth: 2,
                        fill: '{chart_type}' === 'line' ? false : true,
                        tension: 0.4,
                        pointRadius: '{chart_type}' === 'line' ? 6 : 0,
                        pointHoverRadius: 8
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            display: {show_legend},
                            position: 'top'
                        }},
                        tooltip: {{
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            padding: 12,
                            titleFont: {{ size: 14 }},
                            bodyFont: {{ size: 13 }},
                            callbacks: {{
                                label: function(context) {{
                                    return context.dataset.label + ': ' + context.parsed.y.toFixed(2);
                                }}
                            }}
                        }},
                        zoom: {{
                            zoom: {{
                                wheel: {{ enabled: {enable_zoom} }},
                                pinch: {{ enabled: {enable_zoom} }},
                                mode: 'x'
                            }},
                            pan: {{
                                enabled: {enable_zoom},
                                mode: 'x'
                            }}
                        }}
                    }},
                    scales: {{
                        x: {{
                            display: true,
                            title: {{
                                display: true,
                                text: '{x_label}'
                            }}
                        }},
                        y: {{
                            display: true,
                            title: {{
                                display: true,
                                text: '{y_label}'
                            }},
                            beginAtZero: true
                        }}
                    }}
                }}
            }};
        }}

        const myChart = new Chart(ctx, config);

        function resetZoom() {{
            if (myChart.resetZoom) {{
                myChart.resetZoom();
            }}
        }}

        function downloadChart() {{
            const link = document.createElement('a');
            link.download = '{title}.png';
            link.href = document.getElementById('myChart').toDataURL('image/png');
            link.click();
        }}

        function toggleLegend() {{
            const legendDisplay = myChart.options.plugins.legend.display;
            myChart.options.plugins.legend.display = !legendDisplay;
            myChart.update();
        }}
    </script>
</body>
</html>"#
        ))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::charts::{ChartStyle, ChartType};
    use crate::data::{DataPoint, DataSet};

    #[test]
    fn test_html_writer_new() {
        let writer = HtmlWriter::new("test.html");
        assert_eq!(writer.output_path, "test.html");
    }
}
