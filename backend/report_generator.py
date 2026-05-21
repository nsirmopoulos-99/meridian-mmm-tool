import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for servers
import matplotlib.pyplot as plt
import base64
from io import BytesIO
from jinja2 import Template
import os


def fig_to_base64(fig):
    """Convert matplotlib figure to base64 string for HTML embedding."""
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return encoded


def generate_full_report(results: dict, job_id: str) -> str:
    """Generate a full HTML report from Meridian analysis results."""

    analyzer = results['analyzer']
    plots = {}
    tables = {}

    # --- Plot 1: Model Fit ---
    try:
        fig = analyzer.plot_model_fit()
        plots['model_fit'] = fig_to_base64(fig)
    except Exception as e:
        plots['model_fit'] = None
        print(f"Model fit plot error: {e}")

    # --- Plot 2: ROI by Channel ---
    try:
        fig = analyzer.plot_roi_bar_chart()
        plots['roi'] = fig_to_base64(fig)
    except Exception as e:
        plots['roi'] = None
        print(f"ROI plot error: {e}")

    # --- Plot 3: Media Contribution Decomposition ---
    try:
        fig = analyzer.plot_contribution_waterfall_chart()
        plots['decomposition'] = fig_to_base64(fig)
    except Exception as e:
        plots['decomposition'] = None
        print(f"Decomposition plot error: {e}")

    # --- Plot 4: Response Curves ---
    try:
        fig = analyzer.plot_response_curves()
        plots['response_curves'] = fig_to_base64(fig)
    except Exception as e:
        plots['response_curves'] = None
        print(f"Response curves error: {e}")

    # --- Plot 5: Budget Optimization ---
    try:
        fig = analyzer.plot_budget_allocation_vs_optimized()
        plots['budget'] = fig_to_base64(fig)
    except Exception as e:
        plots['budget'] = None
        print(f"Budget plot error: {e}")

    # --- Table: ROI Summary ---
    try:
        roi_df = analyzer.roi_summary()
        tables['roi'] = roi_df.to_html(classes='data-table', border=0)
    except Exception as e:
        tables['roi'] = "<p>ROI table unavailable</p>"
        print(f"ROI table error: {e}")

    # --- Load and render template ---
    template_path = os.path.join(os.path.dirname(__file__), 'report_template.html')
    with open(template_path, 'r') as f:
        template = Template(f.read())

    return template.render(
        plots=plots,
        tables=tables,
        job_id=job_id,
        date_start=results['date_start'],
        date_end=results['date_end'],
        channels=results['channels'],
    )
