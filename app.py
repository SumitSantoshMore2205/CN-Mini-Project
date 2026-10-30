"""Browser edition of Subnetting Studio for Streamlit Community Cloud."""

from __future__ import annotations

import csv
import io
from datetime import datetime

import pandas as pd
import streamlit as st

from subnet_calculator import SubnetPlan, calculate_subnets, ip_binary


st.set_page_config(
    page_title="Subnetting Studio",
    page_icon=":material/hub:",
    layout="wide",
)


def apply_appearance(dark: bool) -> None:
    """Apply the user's light or dark appearance preference."""
    if dark:
        background, surface, text, muted = "#0F172A", "#1E293B", "#E2E8F0", "#94A3B8"
        border, stripe = "#334155", "#263449"
    else:
        background, surface, text, muted = "#F8FAFC", "#FFFFFF", "#0F172A", "#64748B"
        border, stripe = "#E2E8F0", "#F1F5F9"
    st.html(f"""
    <style>
      .stApp {{ background: {background}; color: {text}; }}
      [data-testid="stHeader"] {{ background: transparent; }}
      [data-testid="stSidebar"] {{ background: {surface}; }}
      [data-testid="stMetric"] {{ background: {surface}; border: 1px solid {border};
        border-radius: 12px; padding: 16px 18px; }}
      [data-testid="stMetricLabel"] {{ color: {muted}; }}
      [data-testid="stDataFrame"] {{ border: 1px solid {border}; border-radius: 10px; }}
      [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input {{
        background: {surface}; color: {text}; }}
      [data-testid="stRadio"] label {{ color: {text}; }}
      [data-testid="stMarkdownContainer"] {{ color: {text}; }}
      div[data-testid="stVerticalBlockBorderWrapper"] {{ border-color: {border}; }}
      .stCaption {{ color: {muted}; }}
    </style>
    """)


def make_rows(plan: SubnetPlan) -> list[dict[str, object]]:
    """Build the visible table and export rows from one subnet plan."""
    return [
        {
            "#": subnet.index,
            "Network Address": str(subnet.network.network_address),
            "First Usable": str(subnet.first_usable) if subnet.first_usable is not None else "—",
            "Last Usable": str(subnet.last_usable) if subnet.last_usable is not None else "—",
            "Broadcast": str(subnet.broadcast),
            "Subnet Mask": str(subnet.network.netmask),
            "CIDR": f"/{subnet.network.prefixlen}",
            "Hosts": subnet.usable_hosts,
        }
        for subnet in plan.subnets
    ]


def make_csv(plan: SubnetPlan) -> bytes:
    output = io.StringIO(newline="")
    fields = ("#", "Network Address", "First Usable", "Last Usable", "Broadcast",
              "Subnet Mask", "CIDR", "Hosts")
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows(make_rows(plan))
    return output.getvalue().encode("utf-8-sig")


def make_txt(plan: SubnetPlan) -> bytes:
    lines = [
        "Subnetting Studio – Network Plan",
        f"Generated: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"Parent network: {plan.original_network}",
        f"New mask: {plan.new_mask} (/{plan.new_prefix})",
        f"Original IP (binary): {ip_binary(plan.original_ip)}",
        f"Original mask (binary): {ip_binary(plan.original_mask)}",
        "",
        "# | Network | First usable | Last usable | Broadcast | Mask | CIDR | Hosts",
    ]
    lines.extend(" | ".join(str(value) for value in row.values()) for row in make_rows(plan))
    return "\n".join(lines).encode("utf-8")


def reset_inputs() -> None:
    st.session_state["network_address"] = "192.168.10.0"
    st.session_state["cidr_mask"] = "24"
    st.session_state["calculation_mode"] = "Number of subnets"
    st.session_state["amount"] = 4
    st.session_state["subnet_plan"] = None
    st.session_state["calculation_error"] = None


if "subnet_plan" not in st.session_state:
    st.session_state.subnet_plan = None
if "calculation_error" not in st.session_state:
    st.session_state.calculation_error = None

with st.sidebar:
    st.markdown("### Appearance")
    dark_mode = st.toggle("Dark mode", value=False, key="dark_mode")
    st.caption("Subnetting Studio · IPv4 planning")

apply_appearance(dark_mode)

st.markdown(":blue-badge[NETWORK DESIGN TOOLKIT]")
st.title("Subnetting Studio")
st.caption("Plan IPv4 address spaces and inspect every subnet allocation.")

with st.container(border=True):
    st.subheader("Configure your network", divider="gray")
    with st.form("subnet_calculation", clear_on_submit=False):
        address_col, mask_col, mode_col, amount_col = st.columns([1.45, 1, 1.5, 0.7])
        with address_col:
            address = st.text_input("Network address", value="192.168.10.0", key="network_address",
                                    placeholder="192.168.10.0")
        with mask_col:
            prefix_or_mask = st.text_input("CIDR / subnet mask", value="24", key="cidr_mask",
                                            placeholder="24 or 255.255.255.0")
        with mode_col:
            mode_label = st.radio("Calculation mode", ("Number of subnets", "Hosts / subnet"),
                                  horizontal=True, key="calculation_mode")
        with amount_col:
            amount = st.number_input("Amount", min_value=1, value=4, step=1, key="amount")
        submitted = st.form_submit_button("Calculate network", type="primary", icon=":material/calculate:",
                                          width="stretch")

    st.button("Reset inputs and results", icon=":material/refresh:",
              on_click=reset_inputs, key="reset_button")

if submitted:
    mode = "subnets" if mode_label == "Number of subnets" else "hosts"
    try:
        st.session_state.subnet_plan = calculate_subnets(address, prefix_or_mask, mode, int(amount))
        st.session_state.calculation_error = None
        st.toast("Subnet plan calculated", icon=":material/check_circle:")
    except ValueError as exc:
        st.session_state.calculation_error = str(exc)

if st.session_state.calculation_error:
    st.error(st.session_state.calculation_error, icon=":material/error:")

plan: SubnetPlan | None = st.session_state.subnet_plan
if plan:
    st.subheader("Subnet summary")
    metric_cols = st.columns(3)
    metric_cols[0].metric("Total subnets", f"{plan.subnet_count:,}")
    metric_cols[1].metric("Usable hosts / subnet", f"{plan.subnets[0].usable_hosts:,}")
    metric_cols[2].metric("New subnet mask", f"{plan.new_mask}  (/{plan.new_prefix})")

    with st.container(border=True):
        st.markdown("**Binary reference**")
        st.code(
            f"IP    {ip_binary(plan.original_ip)}\nMASK  {ip_binary(plan.original_mask)}",
            language="text",
        )

    st.subheader("Subnet allocations")
    st.dataframe(
        pd.DataFrame(make_rows(plan)),
        width="stretch",
        height=480,
        hide_index=True,
        column_config={
            "#": st.column_config.NumberColumn("#", width="small"),
            "Network Address": st.column_config.TextColumn("Network Address", width="medium"),
            "First Usable": st.column_config.TextColumn("First Usable", width="medium"),
            "Last Usable": st.column_config.TextColumn("Last Usable", width="medium"),
            "Broadcast": st.column_config.TextColumn("Broadcast", width="medium"),
            "Subnet Mask": st.column_config.TextColumn("Subnet Mask", width="medium"),
            "CIDR": st.column_config.TextColumn("CIDR", width="small"),
            "Hosts": st.column_config.NumberColumn("Hosts", width="small", format="localized"),
        },
    )

    st.markdown("#### Export results")
    download_txt, download_csv = st.columns(2)
    with download_txt:
        st.download_button("Download TXT", data=make_txt(plan), file_name="subnet_plan.txt",
                           mime="text/plain", icon=":material/download:", width="stretch")
    with download_csv:
        st.download_button("Download CSV", data=make_csv(plan), file_name="subnet_plan.csv",
                           mime="text/csv", icon=":material/download:", width="stretch")
else:
    st.info("Enter a network and calculate to view subnet details.", icon=":material/info:")
