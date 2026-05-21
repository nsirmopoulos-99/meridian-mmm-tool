import pandas as pd
import os
from meridian.data import load
from meridian.model import model as mmm_model
from meridian.analysis import analyzer as mmm_analyzer
from meridian.analysis import optimizer as mmm_optimizer


def run_meridian_analysis(csv_path: str, column_config: dict, date_start: str, date_end: str):
    """
    Runs the full Meridian MMM pipeline.
    """

    # 1. Load and filter data by date range
    df = pd.read_csv(csv_path, parse_dates=['date'])
    df = df[(df['date'] >= date_start) & (df['date'] <= date_end)]
    filtered_path = csv_path.replace('.csv', '_filtered.csv')
    df.to_csv(filtered_path, index=False)

    # 2. Map columns
    coord_to_columns = load.CoordToColumns(
        time='date',
        kpi=column_config['kpi'],
        revenue_per_kpi=column_config.get('revenue_per_kpi', None),
        controls=column_config.get('controls', []),
        media=list(column_config['media_channels'].keys()),
        media_spend=list(column_config['media_spend'].keys()),
    )

    # 3. Load data into Meridian
    loader = load.CsvDataLoader(
        csv_path=filtered_path,
        kpi_type='non_revenue',
        coord_to_columns=coord_to_columns,
        media_to_channel=column_config['media_channels'],
        media_spend_to_channel=column_config['media_spend'],
    )
    input_data = loader.load()

    # 4. Build and fit model
    model = mmm_model.Meridian(input_data=input_data)
    model.sample_prior(500)
    model.fit_model(
        n_chains=4,
        n_adapt=500,
        n_burnin=500,
        n_keep=1000
    )

    # 5. Analyze results
    analysis = mmm_analyzer.Analyzer(model)

    # 6. Optimize budget
    total_budget = float(df[list(column_config['media_spend'].keys())].sum().sum())
    budget_opt = mmm_optimizer.BudgetOptimizer(model)
    optimization_result = budget_opt.optimize(
        scenario=mmm_optimizer.FixedBudgetScenario(
            total_budget=total_budget
        )
    )

    return {
        'model': model,
        'analyzer': analysis,
        'optimizer': optimization_result,
        'input_data': input_data,
        'date_start': date_start,
        'date_end': date_end,
        'channels': list(column_config['media_channels'].values()),
    }
