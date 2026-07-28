import io
from datetime import date
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio

# Dark theme & Bengali compatible font family
pio.templates.default = "plotly_dark"
FONT_FAMILY = "Noto Sans Bengali, Kalpurush, SolaimanLipi, Vrinda, Arial, sans-serif"

def generate_daily_chart(daily_data: list, account_no: str, system: str, lang: str = "en") -> io.BytesIO | None:
    """Generates a date-wise Bar + Cost spline chart for daily consumption."""
    if not daily_data or len(daily_data) < 1:
        return None

    sorted_daily = sorted(daily_data, key=lambda x: str(x.get("date") or x.get("readingDate") or x.get("created_at") or ""))
    dates, units, taka = [], [], []

    # Check if consumedUnit values are cumulative meter readings vs daily values
    is_cumulative = False
    if len(sorted_daily) >= 2:
        val1 = float(sorted_daily[0].get("consumedUnit") or sorted_daily[0].get("consumption") or sorted_daily[0].get("unit") or 0)
        val2 = float(sorted_daily[1].get("consumedUnit") or sorted_daily[1].get("consumption") or sorted_daily[1].get("unit") or 0)
        if val1 > 300 and val2 >= val1:
            is_cumulative = True

    if is_cumulative and len(sorted_daily) >= 2:
        for i in range(1, len(sorted_daily)):
            d_str = sorted_daily[i].get("date") or sorted_daily[i].get("readingDate") or ""
            u_curr = float(sorted_daily[i].get("consumedUnit") or sorted_daily[i].get("consumption") or sorted_daily[i].get("unit") or 0)
            u_prev = float(sorted_daily[i-1].get("consumedUnit") or sorted_daily[i-1].get("consumption") or sorted_daily[i-1].get("unit") or 0)
            t_curr = float(sorted_daily[i].get("consumedTaka") or sorted_daily[i].get("amount") or sorted_daily[i].get("billAmount") or 0)
            t_prev = float(sorted_daily[i-1].get("consumedTaka") or sorted_daily[i-1].get("amount") or sorted_daily[i-1].get("billAmount") or 0)

            dates.append(str(d_str)[-5:] if len(str(d_str)) >= 5 else str(d_str))
            units.append(round(max(u_curr - u_prev, 0), 2))
            taka.append(round(max(t_curr - t_prev, 0), 2))
    else:
        for item in sorted_daily:
            d_str = item.get("date") or item.get("readingDate") or ""
            u_val = float(item.get("consumedUnit") or item.get("consumption") or item.get("unit") or 0)
            t_val = float(item.get("consumedTaka") or item.get("amount") or item.get("billAmount") or 0)

            dates.append(str(d_str)[-5:] if len(str(d_str)) >= 5 else str(d_str))
            units.append(round(u_val, 2))
            taka.append(round(t_val, 2))

    if not dates:
        return None

    dates = dates[-18:]
    units = units[-18:]
    taka  = taka[-18:]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. Date-wise Bars for Units (kWh)
    fig.add_trace(
        go.Bar(
            x=dates,
            y=units,
            name="Units (kWh)" if lang == "en" else "ইউনিট (kWh)",
            marker=dict(
                color="#89b4fa",
                line=dict(color="#b4befe", width=1),
            ),
            text=[f"{u:.1f}" for u in units],
            textposition="outside",
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
            line=dict(color="#fab387", width=3, shape="spline"),
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
        xaxis=dict(
            type="category",
            title="Date (MM-DD)" if lang == "en" else "তারিখ (MM-DD)",
            gridcolor="#313244",
            showgrid=True,
            title_font=dict(family=FONT_FAMILY),
            tickangle=-45,
        ),
        yaxis=dict(title="Units (kWh)" if lang == "en" else "ইউনিট (kWh)", gridcolor="#313244", showgrid=True, title_font=dict(family=FONT_FAMILY)),
        yaxis2=dict(title="Cost (৳)" if lang == "en" else "খরচ (৳)", showgrid=False, title_font=dict(family=FONT_FAMILY)),
        width=850,
        height=480,
    )

    img_bytes = pio.to_image(fig, format="png", engine="kaleido")
    return io.BytesIO(img_bytes)


def generate_monthly_chart(monthly_data: list, account_no: str, system: str, lang: str = "en") -> io.BytesIO | None:
    """Generates a Plotly PNG chart with gradient intensity bars + bill spline curve."""
    if not monthly_data:
        return None

    sorted_mo = sorted(monthly_data, key=lambda x: str(x.get("month") or x.get("readingMonth", "")))[-12:]
    months   = [m.get("month") or m.get("readingMonth", "") for m in sorted_mo]
    mo_units = [float(m.get("consumedUnit") or m.get("consumption") or m.get("unit") or 0) for m in sorted_mo]
    mo_taka  = [float(m.get("consumedTaka") or m.get("amount") or m.get("billAmount") or 0) for m in sorted_mo]

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
        xaxis=dict(type="category", title="Month (YYYY-MM)" if lang == "en" else "মাস (YYYY-MM)", gridcolor="#313244", showgrid=True, title_font=dict(family=FONT_FAMILY)),
        yaxis=dict(title="Units (kWh)" if lang == "en" else "ইউনিট (kWh)", gridcolor="#313244", showgrid=True, title_font=dict(family=FONT_FAMILY)),
        yaxis2=dict(title="Bill (৳)" if lang == "en" else "বিল (৳)", showgrid=False, title_font=dict(family=FONT_FAMILY)),
        width=850,
        height=480,
    )

    img_bytes = pio.to_image(fig, format="png", engine="kaleido")
    return io.BytesIO(img_bytes)


def generate_recharge_chart(recharge_data: list, account_no: str, system: str, lang: str = "en") -> io.BytesIO | None:
    """Generates a Plotly PNG bar chart for recharge history with pattern insights."""
    from tariff_calc import analyze_recharge_pattern

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

    pattern = analyze_recharge_pattern(recharge_data, lang=lang)

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

    if pattern and pattern.get("avg_amount", 0) > 0:
        avg_amt = pattern["avg_amount"]
        fig.add_shape(
            type="line",
            x0=0, x1=1, xref="x domain",
            y0=avg_amt, y1=avg_amt, yref="y",
            line=dict(color="#f9e2af", width=1.5, dash="dash"),
        )
        fig.add_annotation(
            x=1, xref="x domain",
            y=avg_amt, yref="y",
            text=f"avg ৳{avg_amt:,.0f}",
            showarrow=False,
            font=dict(color="#f9e2af", size=9, family=FONT_FAMILY),
            xanchor="right", yanchor="bottom"
        )

    EN = (lang == "en")
    sub_info = ""
    if pattern and pattern.get("has_pattern"):
        avg_d = pattern.get("avg_days_between", 0)
        top_b = pattern.get("top_bracket", "")
        wd = pattern.get("most_common_weekday", "")
        if EN:
            sub_info = f"<br><span style='font-size:11px;color:#a6adc8'>Frequency: Every ~{avg_d} days | Peak Period: {top_b} ({wd}s)</span>"
        else:
            sub_info = f"<br><span style='font-size:11px;color:#a6adc8'>সময়সীমা: প্রতি ~{avg_d} দিন পর | সম্ভাব্য সময়: {top_b} ({wd})</span>"

    title_text = (
        f"💳 Recharge History & Pattern — Account: {account_no} ({system}){sub_info}"
        if EN
        else f"💳 রিচার্জের ইতিহাস ও বিশ্লেষণ — অ্যাকাউন্ট: {account_no} ({system}){sub_info}"
    )

    fig.update_layout(
        title=dict(
            text=title_text,
            font=dict(size=14, color="#cdd6f4", family=FONT_FAMILY),
            x=0.02,
        ),
        paper_bgcolor="#11111b",
        plot_bgcolor="#181825",
        font=dict(color="#a6adc8", family=FONT_FAMILY),
        margin=dict(l=40, r=40, t=65, b=40),
        xaxis=dict(type="category", title="Recharge Date" if lang == "en" else "রিচার্জের তারিখ", gridcolor="#313244", showgrid=True, title_font=dict(family=FONT_FAMILY)),
        yaxis=dict(title="Amount (৳)" if lang == "en" else "টাকা (৳)", gridcolor="#313244", showgrid=True, title_font=dict(family=FONT_FAMILY)),
        width=850,
        height=500,
    )

    try:
        img_bytes = pio.to_image(fig, format="png", engine="kaleido")
    except Exception:
        img_bytes = pio.to_image(fig, format="png")
    return io.BytesIO(img_bytes)


def _to_units_and_taka(raw_unit, raw_taka):
    """Auto-detect if consumedUnit is actually Taka or real kWh units.
    Returns (units_kwh, taka_bdt) as floats."""
    from tariff_calc import estimate_bill, estimate_units_from_taka
    u = float(raw_unit or 0)
    t = float(raw_taka or 0)
    if u > 500 and t == 0:
        # API returned Taka in the unit field
        t = u
        u = estimate_units_from_taka(t)
    elif u == 0 and t == 0:
        pass
    elif t == 0 and u > 0:
        t = estimate_bill(u)
    return round(u, 2), round(t, 2)


def generate_usage_chart(
    daily_data: list,
    monthly_data: list,
    account_no: str,
    system: str,
    bal_data: dict | None = None,
    info_data: dict | None = None,
    lang: str = "en",
    days: int = 7,
    stats: dict | None = None,
) -> io.BytesIO:
    """
    6-row Executive Dashboard:
      Row 1-2 : KPI indicator cards
      Row 3   : 30-day daily timeline (kWh bars + ৳ cost spline)
      Row 4   : This week vs Last week comparison
      Row 5   : This month vs Last month comparison
      Row 6   : 12-month kWh & bill trend
    """
    from tariff_calc import estimate_bill, estimate_units_from_taka
    from datetime import date, timedelta
    import calendar

    # ── KPI values ──────────────────────────────────────────────────────────
    if stats:
        bal_val = float((bal_data or {}).get("balance", 0))
        mo_units = float(stats.get("mo_units", 0))
        mo_taka = float(stats.get("mo_taka", 0))
        daily_units_avg = float(stats.get("daily_units_avg", 0))
        daily_taka_avg = float(stats.get("daily_taka_avg", 0))
        projected_units = float(stats.get("projected_units", 0))
        projected_taka = float(stats.get("projected_taka", 0))
        days_bal_lasts = stats.get("days_bal_lasts", "∞")
    else:
        bal_val = float((bal_data or {}).get("balance", 0))
        raw_cons = float((bal_data or {}).get("currentMonthConsumption", 0))
        if raw_cons > 500:
            mo_taka = raw_cons
            mo_units = estimate_units_from_taka(mo_taka)
        else:
            mo_units = raw_cons
            mo_taka = estimate_bill(mo_units)
        today = date.today()
        days_elapsed = max(today.day, 1)
        daily_units_avg = round(mo_units / days_elapsed, 1) if days_elapsed else 0
        daily_taka_avg = round(mo_taka / days_elapsed, 1) if days_elapsed else 0
        projected_units = round(daily_units_avg * 30, 1)
        projected_taka = estimate_bill(projected_units)
        days_bal_lasts = round(bal_val / daily_taka_avg, 1) if daily_taka_avg > 0 else "∞"

    today = date.today()

    def _parse_daily(raw: list) -> dict:
        if not raw: return {}
        sorted_r = sorted(raw, key=lambda x: str(x.get("date", "") or x.get("readingDate", "")))
        result = {}
        first_u = float(sorted_r[0].get("consumedUnit") or sorted_r[0].get("consumption") or 0)
        is_cumul = (len(sorted_r) >= 2 and first_u > 300)
        if is_cumul:
            for i in range(1, len(sorted_r)):
                d = sorted_r[i].get("date", "") or sorted_r[i].get("readingDate", "")
                uc = float(sorted_r[i].get("consumedUnit") or sorted_r[i].get("consumption") or 0)
                up = float(sorted_r[i-1].get("consumedUnit") or sorted_r[i-1].get("consumption") or 0)
                tc = float(sorted_r[i].get("consumedTaka") or sorted_r[i].get("amount") or 0)
                tp = float(sorted_r[i-1].get("consumedTaka") or sorted_r[i-1].get("amount") or 0)
                u_d, t_d = _to_units_and_taka(max(uc - up, 0), max(tc - tp, 0))
                result[str(d)] = (u_d, t_d)
        else:
            for r in sorted_r:
                d = str(r.get("date", "") or r.get("readingDate", ""))
                u_r = r.get("consumedUnit") or r.get("consumption") or 0
                t_r = r.get("consumedTaka") or r.get("amount") or 0
                u_d, t_d = _to_units_and_taka(u_r, t_r)
                result[d] = (u_d, t_d)
        return result

    daily_dict = _parse_daily(daily_data)
    timeline_dates, timeline_kwh, timeline_taka = [], [], []
    for i in range(29, -1, -1):
        d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        kwh_val, taka_val = daily_dict.get(d, (0, 0))
        timeline_dates.append(d[-5:])
        timeline_kwh.append(kwh_val)
        timeline_taka.append(taka_val)

    this_week_dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
    last_week_dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(13, 6, -1)]
    week_labels = [d[-5:] for d in this_week_dates]
    this_week_kwh = [daily_dict.get(d, (0, 0))[0] for d in this_week_dates]
    last_week_kwh = [daily_dict.get(d, (0, 0))[0] for d in last_week_dates]
    this_week_taka = [daily_dict.get(d, (0, 0))[1] for d in this_week_dates]
    last_week_taka = [daily_dict.get(d, (0, 0))[1] for d in last_week_dates]

    this_week_total_kwh = round(sum(this_week_kwh), 1)
    last_week_total_kwh = round(sum(last_week_kwh), 1)
    this_week_total_taka = round(sum(this_week_taka), 0)
    last_week_total_taka = round(sum(last_week_taka), 0)
    week_diff_pct = round((this_week_total_kwh - last_week_total_kwh) / last_week_total_kwh * 100, 1) if last_week_total_kwh > 0 else 0

    mo_dict = {}
    for m in (monthly_data or []):
        key = str(m.get("month") or m.get("readingMonth", ""))
        u_r = m.get("consumedUnit") or m.get("consumption") or 0
        t_r = m.get("consumedTaka") or m.get("amount") or m.get("billAmount") or 0
        mo_dict[key] = _to_units_and_taka(u_r, t_r)
    cur_month = today.strftime("%Y-%m")
    prev_month = (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    cur_mo_kwh, cur_mo_taka = mo_dict.get(cur_month, (mo_units, mo_taka))
    prev_mo_kwh, prev_mo_taka = mo_dict.get(prev_month, (0, 0))
    mo_diff_pct = round((cur_mo_kwh - prev_mo_kwh) / prev_mo_kwh * 100, 1) if prev_mo_kwh > 0 else 0

    EN = lang == "en"
    t_bal, t_mo_lbl, t_avg, t_proj = ("Current Balance", "Month Consumption", "Daily Average", "Projected Month Bill") if EN else ("বর্তমান ব্যালেন্স", "চলতি মাসের ব্যবহার", "দৈনিক গড় ব্যবহার", "আনুমানিক মাসিক বিল")
    t_30d = "📅 30-Day Daily Timeline — kWh & Cost (৳)" if EN else "📅 ৩০ দিনের দৈনিক ইউনিট ও খরচ"
    t_week, t_month = f"📊 This Week vs Last Week | {'▲' if week_diff_pct>=0 else '▼'} {abs(week_diff_pct)}%", f"📊 {cur_month} vs {prev_month} | {'▲' if mo_diff_pct>=0 else '▼'} {abs(mo_diff_pct)}%"
    t_12mo, t_title = ("📈 12-Month kWh & Bill (৳) Trend", f"DESCO Executive Dashboard — {account_no} ({system})") if EN else ("📈 ১২ মাসের ইউনিট ও বিলের ট্রেন্ড", f"ডেসকো ড্যাশবোর্ড — {account_no} ({system})")

    fig = make_subplots(
        rows=6, cols=2, column_widths=[0.5, 0.5], row_heights=[0.09, 0.09, 0.22, 0.20, 0.20, 0.20],
        specs=[[{"type":"indicator"}, {"type":"indicator"}], [{"type":"indicator"}, {"type":"indicator"}], [{"colspan":2, "secondary_y":True}, None], [{"colspan":2}, None], [{"colspan":2}, None], [{"colspan":2, "secondary_y":True}, None]],
        subplot_titles=("", "", "", "", t_30d, t_week, t_month, t_12mo), vertical_spacing=0.055, horizontal_spacing=0.05
    )

    # ── Row 1: Balance | Month kWh ───────────────────────────────────────────
    fig.add_trace(go.Indicator(
        mode="number", value=bal_val,
        number={"prefix": "৳", "font": {"color": "#a6e3a1", "size": 26, "family": FONT_FAMILY}},
        title={"text": t_bal + f"<br><span style='font-size:10px;color:#6c7086'>lasts ~{days_bal_lasts} days</span>",
               "font": {"color": "#cdd6f4", "size": 11, "family": FONT_FAMILY}},
    ), row=1, col=1)

    fig.add_trace(go.Indicator(
        mode="number", value=mo_units,
        number={"suffix": " kWh", "font": {"color": "#89b4fa", "size": 26, "family": FONT_FAMILY}},
        title={"text": t_mo_lbl + f"<br><span style='font-size:10px;color:#6c7086'>৳{mo_taka:.0f} cost</span>",
               "font": {"color": "#cdd6f4", "size": 11, "family": FONT_FAMILY}},
    ), row=1, col=2)

    # ── Row 2: Daily avg | Projected ─────────────────────────────────────────
    fig.add_trace(go.Indicator(
        mode="number", value=daily_units_avg,
        number={"suffix": " kWh/d", "font": {"color": "#f9e2af", "size": 26, "family": FONT_FAMILY}},
        title={"text": t_avg + f"<br><span style='font-size:10px;color:#6c7086'>~৳{daily_taka_avg:.0f}/day</span>",
               "font": {"color": "#cdd6f4", "size": 11, "family": FONT_FAMILY}},
    ), row=2, col=1)

    fig.add_trace(go.Indicator(
        mode="number", value=projected_taka,
        number={"prefix": "৳", "font": {"color": "#fab387", "size": 26, "family": FONT_FAMILY}},
        title={"text": t_proj + f"<br><span style='font-size:10px;color:#6c7086'>{projected_units:.0f} kWh</span>",
               "font": {"color": "#cdd6f4", "size": 11, "family": FONT_FAMILY}},
    ), row=2, col=2)

    bar_colors = ["#a6e3a1" if v <= daily_units_avg else "#f38ba8" for v in timeline_kwh]
    fig.add_trace(go.Bar(x=timeline_dates, y=timeline_kwh, name="kWh/day", marker=dict(color=bar_colors), text=[f"{v:.1f}" if v > 0 else "" for v in timeline_kwh], textposition="outside", textfont=dict(size=7)), row=3, col=1, secondary_y=False)
    fig.add_trace(go.Scatter(x=timeline_dates, y=timeline_taka, name="৳ Cost/day", mode="lines+markers", line=dict(color="#fab387", width=2, shape="spline", dash="dot"), marker=dict(size=4)), row=3, col=1, secondary_y=True)
    fig.add_shape(
        type="line",
        x0=0, x1=1, xref="x3 domain",
        y0=daily_units_avg, y1=daily_units_avg, yref="y3",
        line=dict(color="#6c7086", width=1.5, dash="dash"),
    )

    fig.add_trace(go.Bar(x=week_labels, y=last_week_kwh, name="Last Week", marker=dict(color="#585b70")), row=4, col=1)
    fig.add_trace(go.Bar(x=week_labels, y=this_week_kwh, name="This Week", marker=dict(color="#89b4fa")), row=4, col=1)

    def _half_sums(month_str: str) -> tuple:
        y, m = int(month_str[:4]), int(month_str[5:7])
        n = calendar.monthrange(y, m)[1]
        h1, h2, h1t, h2t = 0, 0, 0, 0
        for d in range(1, n + 1):
            k, t = daily_dict.get(f"{month_str}-{d:02d}", (0, 0))
            if d <= 15: h1 += k; h1t += t
            else: h2 += k; h2t += t
        return round(h1,1), round(h2,1), round(h1t,0), round(h2t,0)
    cur_h1, cur_h2, _, _ = _half_sums(cur_month)
    prev_h1, prev_h2, _, _ = _half_sums(prev_month)
    if prev_h1 == 0 and prev_h2 == 0 and prev_mo_kwh > 0: prev_h1, prev_h2 = round(prev_mo_kwh * 0.5, 1), round(prev_mo_kwh * 0.5, 1)
    fig.add_trace(go.Bar(x=["1–15", "16–end"], y=[prev_h1, prev_h2], name=prev_month, marker=dict(color="#585b70")), row=5, col=1)
    fig.add_trace(go.Bar(x=["1–15", "16–end"], y=[cur_h1, cur_h2], name=cur_month, marker=dict(color="#cba6f7")), row=5, col=1)

    if monthly_data:
        sorted_mo = sorted(monthly_data, key=lambda x: str(x.get("month", "") or x.get("readingMonth", "")))[-12:]
        m12_months, m12_kwh, m12_taka = [], [], []
        for m in sorted_mo:
            raw_u = m.get("consumedUnit") or m.get("consumption") or 0
            raw_t = m.get("consumedTaka") or m.get("amount") or m.get("billAmount") or 0
            u_k, t_b = _to_units_and_taka(raw_u, raw_t)
            m12_months.append(str(m.get("month") or m.get("readingMonth", ""))[-5:])
            m12_kwh.append(u_k)
            m12_taka.append(t_b)

        fig.add_trace(go.Bar(
            x=m12_months, y=m12_kwh,
            name="Monthly kWh" if EN else "মাসিক kWh",
            marker=dict(color=m12_kwh, colorscale="Tealgrn", showscale=False, line=dict(color="#a6e3a1", width=1)),
            text=[f"{v:.0f}" for v in m12_kwh],
            textposition="outside",
            textfont=dict(size=8, family=FONT_FAMILY),
        ), row=6, col=1, secondary_y=False)

        fig.add_trace(go.Scatter(
            x=m12_months, y=m12_taka,
            name="Bill (৳)" if EN else "বিল (৳)",
            mode="lines+markers",
            line=dict(color="#f9e2af", width=3, shape="spline"),
            marker=dict(size=7, color="#f9e2af"),
            text=[f"৳{v:.0f}" for v in m12_taka],
            textposition="top center",
            textfont=dict(size=8, family=FONT_FAMILY),
        ), row=6, col=1, secondary_y=True)

    # ── Axis formatting ───────────────────────────────────────────────────────
    fig.update_annotations(font=dict(family=FONT_FAMILY, color="#cdd6f4", size=10))

    fig.update_yaxes(title_text="kWh", row=3, col=1, secondary_y=False,
                     gridcolor="#313244", title_font=dict(color="#89b4fa", size=10, family=FONT_FAMILY))
    fig.update_yaxes(title_text="৳", row=3, col=1, secondary_y=True,
                     showgrid=False, title_font=dict(color="#fab387", size=10, family=FONT_FAMILY))
    fig.update_xaxes(type="category", gridcolor="#313244", tickangle=-60,
                     tickfont=dict(size=7), row=3, col=1)

    fig.update_yaxes(title_text="kWh", row=4, col=1,
                     gridcolor="#313244", title_font=dict(color="#89b4fa", size=10, family=FONT_FAMILY))
    fig.update_xaxes(type="category", gridcolor="#313244", row=4, col=1)

    fig.update_yaxes(title_text="kWh", row=5, col=1,
                     gridcolor="#313244", title_font=dict(color="#cba6f7", size=10, family=FONT_FAMILY))
    fig.update_xaxes(type="category", gridcolor="#313244", row=5, col=1)

    fig.update_yaxes(title_text="kWh", row=6, col=1, secondary_y=False,
                     gridcolor="#313244", title_font=dict(color="#a6e3a1", size=10, family=FONT_FAMILY))
    fig.update_yaxes(title_text="৳ Taka", row=6, col=1, secondary_y=True,
                     showgrid=False, title_font=dict(color="#f9e2af", size=10, family=FONT_FAMILY))
    fig.update_xaxes(type="category", gridcolor="#313244", tickangle=-45,
                     tickfont=dict(size=8), row=6, col=1)

    fig.update_layout(
        barmode="group",
        title=dict(text=t_title, font=dict(size=15, color="#cdd6f4", family=FONT_FAMILY), x=0.02),
        paper_bgcolor="#11111b",
        plot_bgcolor="#181825",
        font=dict(color="#a6adc8", family=FONT_FAMILY),
        margin=dict(l=55, r=55, t=65, b=35),
        legend=dict(
            orientation="h", yanchor="top", y=-0.02, xanchor="center", x=0.5,
            font=dict(family=FONT_FAMILY, size=9),
            bgcolor="rgba(24,24,37,0.8)",
        ),
        width=1000,
        height=1400,
    )

    try:
        img_bytes = pio.to_image(fig, format="png", engine="kaleido")
    except Exception:
        img_bytes = pio.to_image(fig, format="png")
    return io.BytesIO(img_bytes)


def generate_custom_date_range_chart(
    filtered_records: list,
    account_no: str,
    system: str,
    start_date: str,
    end_date: str,
    lang: str = "en"
) -> io.BytesIO | None:
    """Generates a Plotly PNG Spline Area chart for a custom date-to-date range."""
    if not filtered_records or len(filtered_records) < 1:
        return None

    dates = [r["date"][-5:] for r in filtered_records]
    units = [r["units"] for r in filtered_records]
    taka  = [r["taka"]  for r in filtered_records]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. Date-wise Bars for Units (kWh)
    fig.add_trace(
        go.Bar(
            x=dates,
            y=units,
            name="Units (kWh)" if lang == "en" else "ইউনিট (kWh)",
            marker=dict(
                color="#89b4fa",
                line=dict(color="#b4befe", width=1),
            ),
            text=[f"{u:.1f}" for u in units],
            textposition="outside",
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
            line=dict(color="#fab387", width=3, shape="spline"),
            marker=dict(size=7, color="#fab387", symbol="diamond"),
        ),
        secondary_y=True,
    )

    title_text = (
        f"Date Range Usage: {start_date} to {end_date} — Account: {account_no} ({system})"
        if lang == "en"
        else f"তারিখের পরিসীমা ব্যবহার: {start_date} থেকে {end_date} — অ্যাকাউন্ট: {account_no} ({system})"
    )

    fig.update_layout(
        title=dict(
            text=title_text,
            font=dict(size=14, color="#cdd6f4", family=FONT_FAMILY),
            x=0.02,
        ),
        paper_bgcolor="#11111b",
        plot_bgcolor="#181825",
        font=dict(color="#a6adc8", family=FONT_FAMILY),
        margin=dict(l=40, r=40, t=60, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(family=FONT_FAMILY)),
        xaxis=dict(
            type="category",
            title="Date (MM-DD)" if lang == "en" else "তারিখ (MM-DD)",
            gridcolor="#313244",
            showgrid=True,
            title_font=dict(family=FONT_FAMILY),
            tickangle=-45,
        ),
        yaxis=dict(title="Units (kWh)" if lang == "en" else "ইউনিট (kWh)", gridcolor="#313244", showgrid=True, title_font=dict(family=FONT_FAMILY)),
        yaxis2=dict(title="Cost (৳)" if lang == "en" else "খরচ (৳)", showgrid=False, title_font=dict(family=FONT_FAMILY)),
        width=850,
        height=480,
    )

    img_bytes = pio.to_image(fig, format="png", engine="kaleido")
    return io.BytesIO(img_bytes)
