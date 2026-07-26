import io
from datetime import date
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio

# Dark theme & Bengali compatible font family
pio.templates.default = "plotly_dark"
FONT_FAMILY = "Noto Sans Bengali, Kalpurush, SolaimanLipi, Vrinda, Arial, sans-serif"

def generate_daily_chart(daily_data: list, account_no: str, system: str, lang: str = "en") -> io.BytesIO | None:
    """Generates a smooth glowing Area + Line chart for daily consumption & cost."""
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

    dates = dates[-18:]
    units = units[-18:]
    taka  = taka[-18:]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. Glowing Semi-Transparent Spline Area for Units
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=units,
            name="Units (kWh)" if lang == "en" else "ইউনিট (kWh)",
            mode="lines+markers",
            line=dict(color="#89b4fa", width=3, shape="spline"),
            fill="tozeroy",
            fillcolor="rgba(137, 180, 250, 0.20)",
            marker=dict(size=7, color="#89b4fa", symbol="circle"),
            text=[f"{u:.1f}" for u in units],
            textposition="top center",
            textfont=dict(color="#cdd6f4", size=9, family=FONT_FAMILY),
        ),
        secondary_y=False,
    )

    # 2. Glowing Cost Spline Line
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=taka,
            name="Cost (৳)" if lang == "en" else "খরচ (৳)",
            mode="lines+markers",
            line=dict(color="#fab387", width=3, shape="spline", dash="solid"),
            marker=dict(size=7, color="#fab387", symbol="diamond"),
        ),
        secondary_y=True,
    )

    title_text = (
        f"📆 Daily Usage & Cost Trend — Account: {account_no} ({system})"
        if lang == "en"
        else f"📆 দৈনিক ব্যবহার ও খরচের ট্রেন্ড — অ্যাকাউন্ট: {account_no} ({system})"
    )

    fig.update_layout(
        title=dict(
            text=title_text,
            font=dict(size=15, color="#cdd6f4", family=FONT_FAMILY),
            x=0.02,
        ),
        paper_bgcolor="#11111b",
        plot_bgcolor="#181825",
        font=dict(color="#a6adc8", family=FONT_FAMILY),
        margin=dict(l=40, r=40, t=60, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(family=FONT_FAMILY)),
        xaxis=dict(title="Date (MM-DD)" if lang == "en" else "তারিখ (MM-DD)", gridcolor="#313244", showgrid=True, titlefont=dict(family=FONT_FAMILY)),
        yaxis=dict(title="Units (kWh)" if lang == "en" else "ইউনিট (kWh)", gridcolor="#313244", showgrid=True, titlefont=dict(family=FONT_FAMILY)),
        yaxis2=dict(title="Cost (৳)" if lang == "en" else "খরচ (৳)", showgrid=False, titlefont=dict(family=FONT_FAMILY)),
        width=850,
        height=480,
    )

    img_bytes = pio.to_image(fig, format="png", engine="kaleido")
    return io.BytesIO(img_bytes)


def generate_monthly_chart(monthly_data: list, account_no: str, system: str, lang: str = "en") -> io.BytesIO | None:
    """Generates a Plotly PNG chart with gradient intensity bars + bill spline curve."""
    if not monthly_data:
        return None

    sorted_mo = sorted(monthly_data, key=lambda x: str(x.get("month", "")))[-12:]
    months   = [m.get("month", "") for m in sorted_mo]
    mo_units = [float(m.get("consumedUnit") or 0) for m in sorted_mo]
    mo_taka  = [float(m.get("consumedTaka") or 0) for m in sorted_mo]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. Gradient-colored units bars
    fig.add_trace(
        go.Bar(
            x=months,
            y=mo_units,
            name="Monthly Units (kWh)" if lang == "en" else "মাসিক ইউনিট (kWh)",
            marker=dict(
                color=mo_units,
                colorscale="Tealgrn",
                showscale=False,
                line=dict(color="#a6e3a1", width=1.5),
            ),
            text=[f"{u:.0f}" for u in mo_units],
            textposition="outside",
            textfont=dict(color="#a6e3a1", size=10, family=FONT_FAMILY),
        ),
        secondary_y=False,
    )

    # 2. Glowing bill amount spline line
    fig.add_trace(
        go.Scatter(
            x=months,
            y=mo_taka,
            name="Bill Amount (৳)" if lang == "en" else "বিল (৳)",
            mode="lines+markers",
            line=dict(color="#f9e2af", width=3.5, shape="spline"),
            marker=dict(size=9, color="#f9e2af", symbol="hexagon"),
        ),
        secondary_y=True,
    )

    title_text = (
        f"📅 Monthly Usage & Bill History — Account: {account_no} ({system})"
        if lang == "en"
        else f"📅 ১২ মাসের ব্যবহার ও বিলের ইতিহাস — অ্যাকাউন্ট: {account_no} ({system})"
    )

    fig.update_layout(
        title=dict(
            text=title_text,
            font=dict(size=15, color="#cdd6f4", family=FONT_FAMILY),
            x=0.02,
        ),
        paper_bgcolor="#11111b",
        plot_bgcolor="#181825",
        font=dict(color="#a6adc8", family=FONT_FAMILY),
        margin=dict(l=40, r=40, t=60, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(family=FONT_FAMILY)),
        xaxis=dict(title="Month (YYYY-MM)" if lang == "en" else "মাস (YYYY-MM)", gridcolor="#313244", showgrid=True, titlefont=dict(family=FONT_FAMILY)),
        yaxis=dict(title="Units (kWh)" if lang == "en" else "ইউনিট (kWh)", gridcolor="#313244", showgrid=True, titlefont=dict(family=FONT_FAMILY)),
        yaxis2=dict(title="Bill (৳)" if lang == "en" else "বিল (৳)", showgrid=False, titlefont=dict(family=FONT_FAMILY)),
        width=850,
        height=480,
    )

    img_bytes = pio.to_image(fig, format="png", engine="kaleido")
    return io.BytesIO(img_bytes)


def generate_recharge_chart(recharge_data: list, account_no: str, system: str, lang: str = "en") -> io.BytesIO | None:
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
            name="Recharge Amount (৳)" if lang == "en" else "রিচার্জের টাকা (৳)",
            marker=dict(
                color=amts,
                colorscale="Viridis",
                showscale=False,
                line=dict(color="#a6e3a1", width=1),
            ),
            text=[f"৳{int(a)}" for a in amts],
            textposition="outside",
            textfont=dict(color="#a6e3a1", size=9, family=FONT_FAMILY),
        )
    )

    title_text = (
        f"💳 Recharge History — Account: {account_no} ({system})"
        if lang == "en"
        else f"💳 রিচার্জের ইতিহাস — অ্যাকাউন্ট: {account_no} ({system})"
    )

    fig.update_layout(
        title=dict(
            text=title_text,
            font=dict(size=15, color="#cdd6f4", family=FONT_FAMILY),
            x=0.02,
        ),
        paper_bgcolor="#11111b",
        plot_bgcolor="#181825",
        font=dict(color="#a6adc8", family=FONT_FAMILY),
        margin=dict(l=40, r=40, t=60, b=40),
        xaxis=dict(title="Recharge Date" if lang == "en" else "রিচার্জের তারিখ", gridcolor="#313244", showgrid=True, titlefont=dict(family=FONT_FAMILY)),
        yaxis=dict(title="Amount (৳)" if lang == "en" else "টাকা (৳)", gridcolor="#313244", showgrid=True, titlefont=dict(family=FONT_FAMILY)),
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
    lang: str = "en",
    days: int = 15
) -> io.BytesIO:
    """
    Generates a 4-tier Executive Dashboard featuring KPI cards + Glowing Area Line Chart + Gradient Bar Chart.
    """
    bal_val = float((bal_data or {}).get("balance", 0))
    mo_use  = float((bal_data or {}).get("currentMonthConsumption", 0))
    today   = date.today()
    days_elapsed = max(today.day, 1)
    daily_avg    = round(mo_use / days_elapsed, 1) if days_elapsed else 0
    projected_mo = round(daily_avg * 30, 1)

    t_bal   = "💰 Current Balance" if lang == "en" else "💰 বর্তমান ব্যালেন্স"
    t_mo    = "⚡ Month Consumption" if lang == "en" else "⚡ চলতি মাসের ব্যবহার"
    t_avg   = "📉 Daily Average" if lang == "en" else "📉 দৈনিক গড় ব্যবহার"
    t_proj  = "🔮 Projected Usage" if lang == "en" else "🔮 আনুমানিক মাসিক ব্যবহার"
    t_daily = f"⚡ Daily Consumption & Cost Line Trend (Past {days} Days)" if lang == "en" else f"⚡ দৈনিক ব্যবহার ও খরচের লাইন গ্রাফ (গত {days} দিন)"
    t_mo_tr = "📅 12-Month Consumption & Bill Trend" if lang == "en" else "📅 ১২ মাসের ব্যবহার ও বিলের গ্রাফ"
    t_title = f"📊 DESCO Executive Dashboard — Account: {account_no} ({system})" if lang == "en" else f"📊 ডেসকো এক্সিকিউটিভ ড্যাশবোর্ড — অ্যাকাউন্ট: {account_no} ({system})"

    fig = make_subplots(
        rows=4, cols=2,
        column_widths=[0.5, 0.5],
        row_heights=[0.12, 0.12, 0.38, 0.38],
        specs=[
            [{"type": "indicator"}, {"type": "indicator"}],
            [{"type": "indicator"}, {"type": "indicator"}],
            [{"colspan": 2, "secondary_y": True}, None],
            [{"colspan": 2, "secondary_y": True}, None],
        ],
        subplot_titles=(
            "", "", "", "",
            t_daily,
            t_mo_tr
        ),
        vertical_spacing=0.08,
        horizontal_spacing=0.05,
    )

    # --- Row 1: KPI 1 & 2 ---
    fig.add_trace(
        go.Indicator(
            mode="number",
            value=bal_val,
            number={"prefix": "৳", "font": {"color": "#a6e3a1", "size": 28, "family": FONT_FAMILY}},
            title={"text": t_bal, "font": {"color": "#cdd6f4", "size": 12, "family": FONT_FAMILY}},
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Indicator(
            mode="number",
            value=mo_use,
            number={"suffix": " kWh", "font": {"color": "#89b4fa", "size": 28, "family": FONT_FAMILY}},
            title={"text": t_mo, "font": {"color": "#cdd6f4", "size": 12, "family": FONT_FAMILY}},
        ),
        row=1, col=2
    )

    # --- Row 2: KPI 3 & 4 ---
    fig.add_trace(
        go.Indicator(
            mode="number",
            value=daily_avg,
            number={"suffix": " kWh/d", "font": {"color": "#f9e2af", "size": 28, "family": FONT_FAMILY}},
            title={"text": t_avg, "font": {"color": "#cdd6f4", "size": 12, "family": FONT_FAMILY}},
        ),
        row=2, col=1
    )

    fig.add_trace(
        go.Indicator(
            mode="number",
            value=projected_mo,
            number={"suffix": " kWh", "font": {"color": "#fab387", "size": 28, "family": FONT_FAMILY}},
            title={"text": t_proj, "font": {"color": "#cdd6f4", "size": 12, "family": FONT_FAMILY}},
        ),
        row=2, col=2
    )

    # --- Row 3: Daily Area Subplot ---
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

        dates = dates[-days:]
        units = units[-days:]
        taka  = taka[-days:]

        fig.add_trace(
            go.Scatter(
                x=dates,
                y=units,
                name="Daily Units" if lang == "en" else "দৈনিক ইউনিট",
                mode="lines+markers",
                line=dict(color="#89b4fa", width=2.5, shape="spline"),
                fill="tozeroy",
                fillcolor="rgba(137, 180, 250, 0.18)",
                marker=dict(size=6, color="#89b4fa"),
                text=[f"{u:.1f}" for u in units],
                textposition="top center",
                textfont=dict(size=8, family=FONT_FAMILY),
            ),
            row=3, col=1, secondary_y=False
        )
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=taka,
                name="Daily Cost (৳)" if lang == "en" else "দৈনিক খরচ (৳)",
                mode="lines+markers",
                line=dict(color="#fab387", width=2.5, shape="spline"),
                marker=dict(size=6, color="#fab387"),
            ),
            row=3, col=1, secondary_y=True
        )

    # --- Row 4: Monthly Gradient Bar Subplot ---
    if monthly_data:
        sorted_mo = sorted(monthly_data, key=lambda x: str(x.get("month", "")))[-12:]
        months   = [m.get("month", "")[-5:] for m in sorted_mo]
        mo_units = [float(m.get("consumedUnit") or 0) for m in sorted_mo]
        mo_taka  = [float(m.get("consumedTaka") or 0) for m in sorted_mo]

        fig.add_trace(
            go.Bar(
                x=months,
                y=mo_units,
                name="Monthly Units" if lang == "en" else "মাসিক ইউনিট",
                marker=dict(
                    color=mo_units,
                    colorscale="Tealgrn",
                    showscale=False,
                    line=dict(color="#a6e3a1", width=1),
                ),
                text=[f"{u:.0f}" for u in mo_units],
                textposition="outside",
                textfont=dict(size=8, family=FONT_FAMILY),
            ),
            row=4, col=1, secondary_y=False
        )
        fig.add_trace(
            go.Scatter(
                x=months,
                y=mo_taka,
                name="Monthly Bill (৳)" if lang == "en" else "মাসিক বিল (৳)",
                mode="lines+markers",
                line=dict(color="#f9e2af", width=3, shape="spline"),
                marker=dict(size=7, color="#f9e2af"),
            ),
            row=4, col=1, secondary_y=True
        )

    fig.update_annotations(font=dict(family=FONT_FAMILY, color="#cdd6f4"))

    fig.update_layout(
        title=dict(
            text=t_title,
            font=dict(size=16, color="#cdd6f4", family=FONT_FAMILY),
            x=0.02,
        ),
        paper_bgcolor="#11111b",
        plot_bgcolor="#181825",
        font=dict(color="#a6adc8", family=FONT_FAMILY),
        margin=dict(l=40, r=40, t=70, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1, font=dict(family=FONT_FAMILY)),
        width=950,
        height=950,
    )

    img_bytes = pio.to_image(fig, format="png", engine="kaleido")
    return io.BytesIO(img_bytes)
