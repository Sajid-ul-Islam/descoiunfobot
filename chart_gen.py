import io
from datetime import date
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio

# Use dark theme
pio.templates.default = "plotly_dark"

def generate_daily_chart(daily_data: list, account_no: str, system: str) -> io.BytesIO | None:
    """Generates a Plotly PNG chart for daily consumption & cost."""
    if not daily_data or len(daily_data) < 2:
        return None

    sorted_daily = sorted(daily_data, key=lambda x: str(x.get("date", "")))
    dates, units, taka = [], [], []

    for i in range(1, len(sorted_daily)):
        d_str  = sorted_daily[i].get("date", "")
        u_curr = float(sorted_daily[i].get("consumedUnit") or 0)
        u_prev = float(sorted_daily[i-1].get("consumedUnit") or 0)
        u_delta = max(u_curr - u_prev, 0)

        t_curr  = float(sorted_daily[i].get("consumedTaka") or 0)
        t_prev  = float(sorted_daily[i-1].get("consumedTaka") or 0)
        t_delta = max(t_curr - t_prev, 0)

        dates.append(d_str[-5:])  # MM-DD
        units.append(round(u_delta, 2))
        taka.append(round(t_delta, 2))

    # Keep last 18 days for clear spacing
    dates = dates[-18:]
    units = units[-18:]
    taka  = taka[-18:]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Units Bar
    fig.add_trace(
        go.Bar(
            x=dates,
            y=units,
            name="Units (kWh)",
            marker_color="#89b4fa",
            text=[f"{u:.1f}" for u in units],
            textposition="outside",
            textfont=dict(color="#cdd6f4", size=9),
        ),
        secondary_y=False,
    )

    # Cost Line
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=taka,
            name="Cost (৳)",
            mode="lines+markers",
            line=dict(color="#fab387", width=3),
            marker=dict(size=7, color="#fab387"),
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title=dict(
            text=f"📆 Daily Usage & Cost Trend — Account: {account_no} ({system})",
            font=dict(size=15, color="#cdd6f4"),
            x=0.02,
        ),
        paper_bgcolor="#11111b",
        plot_bgcolor="#181825",
        font=dict(color="#a6adc8"),
        margin=dict(l=40, r=40, t=60, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(title="Date (MM-DD)", gridcolor="#313244", showgrid=True),
        yaxis=dict(title="Units (kWh)", gridcolor="#313244", showgrid=True),
        yaxis2=dict(title="Cost (৳)", showgrid=False),
        width=850,
        height=480,
    )

    img_bytes = pio.to_image(fig, format="png", engine="kaleido")
    return io.BytesIO(img_bytes)


def generate_monthly_chart(monthly_data: list, account_no: str, system: str) -> io.BytesIO | None:
    """Generates a Plotly PNG chart for 12-month historical consumption & cost."""
    if not monthly_data:
        return None

    sorted_mo = sorted(monthly_data, key=lambda x: str(x.get("month", "")))[-12:]
    months   = [m.get("month", "") for m in sorted_mo]
    mo_units = [float(m.get("consumedUnit") or 0) for m in sorted_mo]
    mo_taka  = [float(m.get("consumedTaka") or 0) for m in sorted_mo]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Monthly Units Bar
    fig.add_trace(
        go.Bar(
            x=months,
            y=mo_units,
            name="Monthly Units (kWh)",
            marker_color="#a6e3a1",
            text=[f"{u:.0f}" for u in mo_units],
            textposition="outside",
            textfont=dict(color="#a6e3a1", size=10),
        ),
        secondary_y=False,
    )

    # Monthly Cost Line
    fig.add_trace(
        go.Scatter(
            x=months,
            y=mo_taka,
            name="Bill Amount (৳)",
            mode="lines+markers",
            line=dict(color="#f9e2af", width=3),
            marker=dict(size=8, color="#f9e2af"),
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title=dict(
            text=f"📅 Monthly Usage & Bill History — Account: {account_no} ({system})",
            font=dict(size=15, color="#cdd6f4"),
            x=0.02,
        ),
        paper_bgcolor="#11111b",
        plot_bgcolor="#181825",
        font=dict(color="#a6adc8"),
        margin=dict(l=40, r=40, t=60, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(title="Month (YYYY-MM)", gridcolor="#313244", showgrid=True),
        yaxis=dict(title="Units (kWh)", gridcolor="#313244", showgrid=True),
        yaxis2=dict(title="Bill (৳)", showgrid=False),
        width=850,
        height=480,
    )

    img_bytes = pio.to_image(fig, format="png", engine="kaleido")
    return io.BytesIO(img_bytes)


def generate_recharge_chart(recharge_data: list, account_no: str, system: str) -> io.BytesIO | None:
    """Generates a Plotly PNG bar chart for recharge history."""
    if not recharge_data:
        return None

    records = recharge_data if isinstance(recharge_data, list) else [recharge_data]
    records = sorted(records, key=lambda x: str(x.get("rechargeDate") or x.get("date", "")))[-15:]

    dates = []
    amts  = []
    for r in records:
        raw_dt = r.get("rechargeDate") or r.get("date", "")
        dt = raw_dt[:10] if len(raw_dt) >= 10 else raw_dt
        amt = float(r.get("totalAmount") or r.get("rechargeAmount") or r.get("amount") or 0)
        dates.append(dt)
        amts.append(amt)

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=dates,
            y=amts,
            name="Recharge Amount (৳)",
            marker_color="#a6e3a1",
            text=[f"৳{int(a)}" for a in amts],
            textposition="outside",
            textfont=dict(color="#a6e3a1", size=9),
        )
    )

    fig.update_layout(
        title=dict(
            text=f"💳 Recharge History — Account: {account_no} ({system})",
            font=dict(size=15, color="#cdd6f4"),
            x=0.02,
        ),
        paper_bgcolor="#11111b",
        plot_bgcolor="#181825",
        font=dict(color="#a6adc8"),
        margin=dict(l=40, r=40, t=60, b=40),
        xaxis=dict(title="Recharge Date", gridcolor="#313244", showgrid=True),
        yaxis=dict(title="Amount (৳)", gridcolor="#313244", showgrid=True),
        width=850,
        height=480,
    )

    img_bytes = pio.to_image(fig, format="png", engine="kaleido")
    return io.BytesIO(img_bytes)


def generate_usage_chart(
    daily_data: list,
    monthly_data: list,
    account_no: str,
    system: str,
    bal_data: dict | None = None,
    info_data: dict | None = None,
) -> io.BytesIO:
    """
    Generates a 3-tier Plotly Executive Dashboard with KPI Cards + Daily Trend + Monthly History.
    """
    bal_val = float((bal_data or {}).get("balance", 0))
    mo_use  = float((bal_data or {}).get("currentMonthConsumption", 0))

    fig = make_subplots(
        rows=3, cols=2,
        column_widths=[0.5, 0.5],
        row_heights=[0.18, 0.41, 0.41],
        specs=[
            [{"type": "indicator"}, {"type": "indicator"}],
            [{"colspan": 2, "secondary_y": True}, None],
            [{"colspan": 2, "secondary_y": True}, None],
        ],
        subplot_titles=(
            "", "",
            "⚡ Daily Unit Consumption & Cost Trend (Past 15 Days)",
            "📅 12-Month Consumption & Bill Trend"
        ),
        vertical_spacing=0.10,
        horizontal_spacing=0.05,
    )

    # --- KPI Indicators (Row 1) ---
    fig.add_trace(
        go.Indicator(
            mode="number",
            value=bal_val,
            number={"prefix": "৳", "font": {"color": "#a6e3a1", "size": 32}},
            title={"text": "💰 Current Balance", "font": {"color": "#cdd6f4", "size": 13}},
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Indicator(
            mode="number",
            value=mo_use,
            number={"suffix": " kWh", "font": {"color": "#89b4fa", "size": 32}},
            title={"text": "⚡ Month Usage", "font": {"color": "#cdd6f4", "size": 13}},
        ),
        row=1, col=2
    )

    # --- Daily Subplot (Row 2) ---
    if daily_data and len(daily_data) >= 2:
        sorted_daily = sorted(daily_data, key=lambda x: str(x.get("date", "")))
        dates, units, taka = [], [], []

        for i in range(1, len(sorted_daily)):
            d_str  = sorted_daily[i].get("date", "")
            u_curr = float(sorted_daily[i].get("consumedUnit") or 0)
            u_prev = float(sorted_daily[i-1].get("consumedUnit") or 0)
            units.append(max(u_curr - u_prev, 0))

            t_curr  = float(sorted_daily[i].get("consumedTaka") or 0)
            t_prev  = float(sorted_daily[i-1].get("consumedTaka") or 0)
            taka.append(max(t_curr - t_prev, 0))
            dates.append(d_str[-5:])

        dates = dates[-15:]
        units = units[-15:]
        taka  = taka[-15:]

        fig.add_trace(
            go.Bar(x=dates, y=units, name="Daily Units", marker_color="#89b4fa", text=[f"{u:.1f}" for u in units], textposition="outside", textfont=dict(size=8)),
            row=2, col=1, secondary_y=False
        )
        fig.add_trace(
            go.Scatter(x=dates, y=taka, name="Daily Cost (৳)", mode="lines+markers", line=dict(color="#fab387", width=2.5), marker=dict(size=6)),
            row=2, col=1, secondary_y=True
        )

    # --- Monthly Subplot (Row 3) ---
    if monthly_data:
        sorted_mo = sorted(monthly_data, key=lambda x: str(x.get("month", "")))[-12:]
        months   = [m.get("month", "")[-5:] for m in sorted_mo]
        mo_units = [float(m.get("consumedUnit") or 0) for m in sorted_mo]
        mo_taka  = [float(m.get("consumedTaka") or 0) for m in sorted_mo]

        fig.add_trace(
            go.Bar(x=months, y=mo_units, name="Monthly Units", marker_color="#a6e3a1", text=[f"{u:.0f}" for u in mo_units], textposition="outside", textfont=dict(size=8)),
            row=3, col=1, secondary_y=False
        )
        fig.add_trace(
            go.Scatter(x=months, y=mo_taka, name="Monthly Bill (৳)", mode="lines+markers", line=dict(color="#f9e2af", width=2.5), marker=dict(size=6)),
            row=3, col=1, secondary_y=True
        )

    fig.update_layout(
        title=dict(
            text=f"📊 DESCO Executive Analytics Dashboard — Account: {account_no} ({system})",
            font=dict(size=16, color="#cdd6f4"),
            x=0.02,
        ),
        paper_bgcolor="#11111b",
        plot_bgcolor="#181825",
        font=dict(color="#a6adc8"),
        margin=dict(l=40, r=40, t=70, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1),
        width=950,
        height=850,
    )

    img_bytes = pio.to_image(fig, format="png", engine="kaleido")
    return io.BytesIO(img_bytes)
