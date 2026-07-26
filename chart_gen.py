import io
import matplotlib
matplotlib.use("Agg")  # Non-gui backend suitable for headless servers
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import date

# Set dark theme aesthetic
plt.style.use("dark_background")

def generate_usage_chart(daily_data: list, monthly_data: list, account_no: str, system: str) -> io.BytesIO:
    """
    Generates a dual-panel modern dark-themed chart:
    - Top: Daily unit consumption (past 15-30 days)
    - Bottom: Monthly unit & bill consumption (past 12 months)
    Returns an in-memory BytesIO PNG image buffer.
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), dpi=150)
    fig.patch.set_facecolor('#11111b')
    ax1.set_facecolor('#181825')
    ax2.set_facecolor('#181825')

    # --- 1. DAILY CONSUMPTION CHART ---
    if daily_data and len(daily_data) >= 2:
        # Sort chronologically
        sorted_daily = sorted(daily_data, key=lambda x: str(x.get("date", "")))
        dates = []
        units = []
        
        for i in range(1, len(sorted_daily)):
            d_str = sorted_daily[i].get("date", "")
            u_curr = float(sorted_daily[i].get("consumedUnit") or 0)
            u_prev = float(sorted_daily[i-1].get("consumedUnit") or 0)
            u_delta = max(u_curr - u_prev, 0)
            
            # Keep last 15 days
            dates.append(d_str[-5:])  # MM-DD
            units.append(u_delta)

        dates = dates[-15:]
        units = units[-15:]

        bars = ax1.bar(dates, units, color='#89b4fa', edgecolor='#b4befe', alpha=0.85, width=0.6)
        ax1.set_title(f"⚡ Daily Unit Consumption (Past {len(dates)} Days)", color='#cdd6f4', fontsize=12, fontweight='bold', pad=10)
        ax1.set_ylabel("Units (kWh)", color='#a6adc8', fontsize=10)
        ax1.tick_params(colors='#a6adc8', labelsize=8)
        ax1.grid(axis='y', color='#313244', linestyle='--', alpha=0.5)

        # Add data values on top of bars
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax1.annotate(f"{height:.1f}",
                             xy=(bar.get_x() + bar.get_width() / 2, height),
                             xytext=(0, 3),
                             textcoords="offset points",
                             ha='center', va='bottom',
                             color='#f5e0dc', fontsize=7, fontweight='bold')
    else:
        ax1.text(0.5, 0.5, "No Daily Data Available", color='#a6adc8', ha='center', va='center')

    # --- 2. MONTHLY CONSUMPTION & BILL CHART ---
    if monthly_data:
        sorted_mo = sorted(monthly_data, key=lambda x: str(x.get("month", "")))[-12:]
        months = [m.get("month", "")[-5:] for m in sorted_mo]  # YY-MM
        mo_units = [float(m.get("consumedUnit") or 0) for m in sorted_mo]
        mo_taka = [float(m.get("consumedTaka") or 0) for m in sorted_mo]

        ax2_taka = ax2.twinx()

        bars_mo = ax2.bar(months, mo_units, color='#a6e3a1', alpha=0.65, width=0.5, label='Units (kWh)')
        line_taka = ax2_taka.plot(months, mo_taka, color='#fab387', marker='o', linewidth=2, markersize=5, label='Cost (৳)')

        ax2.set_title("📅 Monthly Usage & Cost Trend (Past 12 Months)", color='#cdd6f4', fontsize=12, fontweight='bold', pad=10)
        ax2.set_ylabel("Units (kWh)", color='#a6e3a1', fontsize=10)
        ax2_taka.set_ylabel("Cost (৳)", color='#fab387', fontsize=10)

        ax2.tick_params(colors='#a6adc8', labelsize=8)
        ax2_taka.tick_params(colors='#fab387', labelsize=8)
        ax2.grid(axis='y', color='#313244', linestyle='--', alpha=0.5)

        # Annotate monthly cost
        for i, taka in enumerate(mo_taka):
            if taka > 0:
                ax2_taka.annotate(f"৳{int(taka)}",
                                  xy=(months[i], taka),
                                  xytext=(0, 5),
                                  textcoords="offset points",
                                  ha='center', va='bottom',
                                  color='#fab387', fontsize=7, fontweight='bold')
    else:
        ax2.text(0.5, 0.5, "No Monthly Data Available", color='#a6adc8', ha='center', va='center')

    # Title & Layout adjustments
    fig.suptitle(f"DESCO Analytics Dashboard — Account: {account_no} ({system})", color='#cdd6f4', fontsize=14, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])

    buf = io.BytesIO()
    plt.savefig(buf, format='png', facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf
