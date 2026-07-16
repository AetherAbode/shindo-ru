import plotly.graph_objects as go
from typing import Dict


def create_pvt_plot(results: Dict[str, any]) -> go.Figure:
    """Build a PVT plot for processed PVT results."""
    fig = go.Figure()
    for key, df in results.items():
        if 'satoil' in key:
            fig.add_trace(go.Scatter(
                x=df['Pressure'],
                y=df['Bo_adjusted'],
                mode='lines+markers',
                name=f'{key} Bo_adjusted',
            ))
            fig.add_trace(go.Scatter(
                x=df['Pressure'],
                y=df['Rs_adjusted'],
                mode='lines+markers',
                name=f'{key} Rs_adjusted',
                yaxis='y2',
            ))
        elif 'wetgastable' in key:
            fig.add_trace(go.Scatter(
                x=df['Pressure'],
                y=df['Bgwet_adjusted'],
                mode='lines+markers',
                name=f'{key} Bgwet_adjusted',
            ))
    fig.update_layout(
        title='PVT Curves',
        xaxis_title='Pressure',
        yaxis_title='Volume Factor',
        template='plotly_white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        height=600,
    )
    fig.update_layout(
        yaxis2=dict(
            title='Rs Adjusted',
            overlaying='y',
            side='right',
            showgrid=False,
        )
    )
    return fig


def create_relperm_plot(results: Dict[str, any]) -> go.Figure:
    """Build a relative permeability plot for processed RelPerm results."""
    fig = go.Figure()
    for key, df in results.items():
        if 'sgof' in key:
            fig.add_trace(go.Scatter(
                x=df['Sg'],
                y=df['Krg_adjusted'],
                mode='lines+markers',
                name=f'{key} Krg_adjusted',
            ))
            fig.add_trace(go.Scatter(
                x=df['Sg'],
                y=df['Kro_adjusted'],
                mode='lines+markers',
                name=f'{key} Kro_adjusted',
            ))
        elif 'swof' in key:
            fig.add_trace(go.Scatter(
                x=df['Sw'],
                y=df['Krw_adjusted'],
                mode='lines+markers',
                name=f'{key} Krw_adjusted',
            ))
            fig.add_trace(go.Scatter(
                x=df['Sw'],
                y=df['Kro_adjusted'],
                mode='lines+markers',
                name=f'{key} Kro_adjusted',
            ))
    fig.update_layout(
        title='Relative Permeability Curves',
        xaxis_title='Saturation',
        yaxis_title='Relative Permeability',
        template='plotly_white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        height=600,
    )
    return fig
