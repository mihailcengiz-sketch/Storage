import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

_DARK = "plotly_dark"
_CYAN = "#00D4FF"
_GREEN = "#00C851"
_RED = "#FF4444"
_GRAY = "#888888"
_BG = "#0D1117"
_CARD_BG = "#161B22"

_COLORS = px.colors.qualitative.Set3 + px.colors.qualitative.Pastel


def _base_layout(**kwargs) -> dict:
    return dict(
        template=_DARK,
        paper_bgcolor=_CARD_BG,
        plot_bgcolor=_CARD_BG,
        margin=dict(l=10, r=10, t=40, b=10),
        font=dict(family="sans-serif", color="#C9D1D9"),
        **kwargs,
    )


def make_donut_chart(labels: list, values: list, total: float) -> go.Figure:
    """Portfolio allocation donut chart."""
    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.62,
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>$%{value:,.2f}<br>%{percent}<extra></extra>",
        marker=dict(
            colors=_COLORS[:len(labels)],
            line=dict(color=_BG, width=2),
        ),
        sort=True,
        direction="clockwise",
    ))
    fig.update_layout(
        **_base_layout(
            showlegend=True,
            legend=dict(
                orientation="v",
                x=1.02,
                y=0.5,
                font=dict(size=11),
            ),
            annotations=[dict(
                text=f"<b>${total:,.0f}</b>",
                x=0.5, y=0.5,
                font=dict(size=18, color=_CYAN),
                showarrow=False,
            )],
            height=340,
        )
    )
    return fig


def make_pnl_bar_chart(symbols: list, pnl_values: list) -> go.Figure:
    """Horizontal bar chart showing P&L per coin in USD."""
    pairs = sorted(zip(pnl_values, symbols))
    sorted_pnl, sorted_sym = zip(*pairs) if pairs else ([], [])
    colors = [_GREEN if v >= 0 else _RED for v in sorted_pnl]

    fig = go.Figure(go.Bar(
        x=list(sorted_pnl),
        y=list(sorted_sym),
        orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        hovertemplate="<b>%{y}</b><br>$%{x:+,.2f}<extra></extra>",
        text=[f"${v:+,.0f}" for v in sorted_pnl],
        textposition="outside",
        textfont=dict(size=10),
    ))
    fig.add_vline(x=0, line_dash="dash", line_color=_GRAY, line_width=1)
    fig.update_layout(
        **_base_layout(
            title=dict(text="Coin Başına Kar / Zarar (USD)", font=dict(size=13)),
            xaxis=dict(title="USD", zeroline=False, showgrid=True, gridcolor="#30363D"),
            yaxis=dict(showgrid=False),
            height=max(300, len(symbols) * 28 + 60),
            showlegend=False,
        )
    )
    return fig


def make_portfolio_line_chart(snapshots_df: pd.DataFrame) -> go.Figure:
    """Portfolio value vs cost basis over time."""
    fig = go.Figure()
    if snapshots_df.empty:
        fig.update_layout(**_base_layout(
            title="Portföy Değeri Tarihçesi",
            height=300,
            annotations=[dict(text="Henüz yeterli veri yok", x=0.5, y=0.5,
                               showarrow=False, font=dict(size=14, color=_GRAY))],
        ))
        return fig

    fig.add_trace(go.Scatter(
        x=snapshots_df["snapshot_date"],
        y=snapshots_df["total_value_usd"],
        name="Portföy Değeri",
        mode="lines",
        fill="tozeroy",
        line=dict(color=_CYAN, width=2),
        fillcolor="rgba(0, 212, 255, 0.12)",
        hovertemplate="%{x|%d %b %Y}<br><b>$%{y:,.0f}</b><extra>Değer</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=snapshots_df["snapshot_date"],
        y=snapshots_df["total_cost_usd"],
        name="Maliyet",
        mode="lines",
        line=dict(color=_GRAY, width=1.5, dash="dash"),
        hovertemplate="%{x|%d %b %Y}<br><b>$%{y:,.0f}</b><extra>Maliyet</extra>",
    ))
    fig.update_layout(
        **_base_layout(
            title=dict(text="Portföy Değeri Tarihçesi", font=dict(size=13)),
            xaxis=dict(
                showgrid=True, gridcolor="#30363D",
                rangeslider=dict(visible=True, thickness=0.05),
            ),
            yaxis=dict(
                title="USD",
                showgrid=True, gridcolor="#30363D",
                tickprefix="$",
            ),
            hovermode="x unified",
            legend=dict(orientation="h", y=1.08, x=0),
            height=340,
        )
    )
    return fig


def make_24h_change_chart(symbols: list, changes: list) -> go.Figure:
    """Bar chart of 24h price changes per coin."""
    if not symbols:
        fig = go.Figure()
        fig.update_layout(**_base_layout(height=300))
        return fig

    pairs = sorted(zip(changes, symbols), reverse=True)
    sorted_chg, sorted_sym = zip(*pairs)
    colors = [_GREEN if v >= 0 else _RED for v in sorted_chg]

    fig = go.Figure(go.Bar(
        x=list(sorted_sym),
        y=list(sorted_chg),
        marker=dict(color=colors, line=dict(width=0)),
        hovertemplate="<b>%{x}</b><br>%{y:+.2f}%<extra></extra>",
        text=[f"{v:+.1f}%" for v in sorted_chg],
        textposition="outside",
        textfont=dict(size=10),
    ))
    fig.add_hline(y=0, line_dash="dash", line_color=_GRAY, line_width=1)
    fig.update_layout(
        **_base_layout(
            title=dict(text="24 Saatlik Fiyat Değişimi (%)", font=dict(size=13)),
            xaxis=dict(showgrid=False),
            yaxis=dict(
                title="%",
                showgrid=True, gridcolor="#30363D",
                ticksuffix="%",
                zeroline=False,
            ),
            showlegend=False,
            height=320,
        )
    )
    return fig


def make_allocation_table_fig(df: pd.DataFrame) -> go.Figure:
    """Treemap chart for portfolio allocation (alternative view)."""
    if df.empty:
        return go.Figure()
    fig = px.treemap(
        df,
        path=["coin_symbol"],
        values="current_value",
        color="pnl_pct",
        color_continuous_scale=["#FF4444", "#333333", "#00C851"],
        color_continuous_midpoint=0,
        hover_data={"current_value": ":,.2f", "pnl_pct": ":.2f"},
    )
    fig.update_traces(
        texttemplate="<b>%{label}</b><br>$%{value:,.0f}<br>%{color:.1f}%",
        hovertemplate="<b>%{label}</b><br>Değer: $%{value:,.2f}<br>K/Z: %{color:+.2f}%<extra></extra>",
    )
    fig.update_layout(
        **_base_layout(
            title=dict(text="Portföy Dağılımı (Treemap)", font=dict(size=13)),
            coloraxis_colorbar=dict(title="K/Z %", ticksuffix="%"),
            height=380,
            margin=dict(l=0, r=0, t=40, b=0),
        )
    )
    return fig
