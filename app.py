# PREMIUM COMBINED DASHBOARD
# Cost Dashboard (full) + Revenue Dashboard (Month1 vs Month2)
# Save as app.py

import streamlit as st
import pandas as pd
import plotly.express as px
import textwrap

st.set_page_config(page_title="Project Indus", layout="wide")
st.title("Project Indus")


# =========================================================
# HELPERS
# =========================================================
def indian_format(num):
    num = float(num)
    sign = "-" if num < 0 else ""
    num = abs(num)

    if num >= 10000000:
        return f"{sign}₹{num/10000000:.2f} Cr"
    elif num >= 100000:
        return f"{sign}₹{num/100000:.2f} Lakh"
    else:
        return f"{sign}₹{num:,.0f}"

def usd_format(num):
    num = float(num)
    sign = "-" if num < 0 else ""
    num = abs(num)

    if num >= 1000000:
        return f"{sign}${num/1000000:.2f} M"
    elif num >= 1000:
        return f"{sign}${num/1000:.2f} K"
    else:
        return f"{sign}${num:,.0f}"

def clean_num(series):
    return pd.to_numeric(
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("₹", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.replace(" ", "", regex=False),
        errors="coerce"
    ).fillna(0)

# =========================================================
# FILE UPLOAD
# =========================================================
file = st.file_uploader(
    "Upload Excel file",
    type=["xlsx"]
)

if file:

    xls = pd.ExcelFile(file)

    dashboard = st.sidebar.radio(
        "Select Dashboard",
        ["Cost Dashboard", "Revenue Dashboard","Margin Dashboard","Employee Dashboard"]
    )

# =========================================================
# COST DASHBOARD
# =========================================================
    if dashboard == "Cost Dashboard":

        df = pd.read_excel(xls, sheet_name="Employee Allocation")
        df.columns = df.columns.str.strip()

        df = df[
            [
                "Month-2",
                "Employee Id",
                "Employee Name",
                "Tagging",
                "Final Allocation %",
                "Total Cost in Rs"
            ]
        ]

        df.columns = [
            "Month",
            "Employee_ID",
            "Employee_Name",
            "Customer",
            "Allocation",
            "Cost"
        ]

        df["Month"] = pd.to_datetime(df["Month"], dayfirst=True, errors="coerce")
        df["Cost"] = clean_num(df["Cost"])
        df["Allocation"] = clean_num(
            df["Allocation"].astype(str).str.replace("%", "", regex=False)
        )

        df["Allocation"] = df["Allocation"].apply(
            lambda x: x * 100 if x <= 1 else x
        )

        df["Employee_ID"] = df["Employee_ID"].astype(str).str.strip()
        df["Customer"] = df["Customer"].astype(str).str.strip()

        # -------------------------------
        # FILTERS
        # -------------------------------
        customers = sorted(df["Customer"].dropna().unique())
        customer = st.sidebar.selectbox("Customer", customers)

        months = sorted(df["Month"].dt.strftime("%d-%m-%Y").unique())

        idx1 = max(0, len(months)-2)
        idx2 = max(1, len(months)-1)

        month1 = st.sidebar.selectbox("Month 1", months, index=idx1)
        month2 = st.sidebar.selectbox("Month 2", months, index=idx2)

        m1 = pd.to_datetime(month1, dayfirst=True)
        m2 = pd.to_datetime(month2, dayfirst=True)

        emp_master = (
            df[["Employee_ID", "Employee_Name"]]
            .drop_duplicates()
            .sort_values("Employee_Name")
        )

        emp_master["Display"] = (
            emp_master["Employee_ID"] + " - " + emp_master["Employee_Name"]
        )

        emp_pick = st.sidebar.selectbox(
            "Search Employee",
            [""] + emp_master["Display"].tolist()
        )

        # -------------------------------
        # DATA
        # -------------------------------
        data = df[df["Customer"] == customer]

        df1 = data[data["Month"].dt.date == m1.date()]
        df2 = data[data["Month"].dt.date == m2.date()]

        g1 = df1.groupby(
            ["Employee_ID", "Employee_Name"],
            as_index=False
        ).agg(
            Cost_M1=("Cost", "sum"),
            Alloc_M1=("Allocation", "sum")
        )

        g2 = df2.groupby(
            ["Employee_ID", "Employee_Name"],
            as_index=False
        ).agg(
            Cost_M2=("Cost", "sum"),
            Alloc_M2=("Allocation", "sum")
        )

        merged = pd.merge(
            g1, g2,
            on=["Employee_ID", "Employee_Name"],
            how="outer"
        ).fillna(0)

        merged["Variance"] = merged["Cost_M2"] - merged["Cost_M1"]

        # -------------------------------
        # REASONS
        # -------------------------------
        def get_reason(row):

            emp = row["Employee_ID"]

            if row["Cost_M1"] > 0 and row["Cost_M2"] == 0:

                moved = df[
                    (df["Employee_ID"] == emp) &
                    (df["Month"].dt.date == m2.date()) &
                    (df["Customer"] != customer)
                ]

                if not moved.empty:
                    names = ", ".join(
                        sorted(moved["Customer"].unique())
                    )
                    return f"Moved fully to {names}"

                return "Resigned"

            elif row["Cost_M1"] == 0 and row["Cost_M2"] > 0:

                prev = df[
                    (df["Employee_ID"] == emp) &
                    (df["Month"].dt.date == m1.date()) &
                    (df["Customer"] != customer)
                ]

                if not prev.empty:
                    names = ", ".join(
                        sorted(prev["Customer"].unique())
                    )
                    return f"Moved fully from {names}"

                return "New Joiner"

            elif row["Alloc_M2"] < row["Alloc_M1"]:
                return "Decrease in %"

            elif row["Alloc_M2"] > row["Alloc_M1"]:
                return "Increase in %"

            elif row["Variance"] > 0:
                return "Cost Increased"

            elif row["Variance"] < 0:
                return "Cost Reduced"

            return "No Change"

        merged["Reason"] = merged.apply(get_reason, axis=1)

        result = merged.sort_values("Variance", ascending=False)

        # -------------------------------
        # KPI
        # -------------------------------
        total1 = result["Cost_M1"].sum()
        total2 = result["Cost_M2"].sum()
        variance = total2 - total1

        st.subheader(f"{customer}: {month1} vs {month2}")

        c1,c2,c3 = st.columns(3)
        c1.metric("Month 1 Cost", indian_format(total1))
        c2.metric("Month 2 Cost", indian_format(total2))
        c3.metric("Variance", indian_format(variance))

        # -------------------------------
        # TABLE
        # -------------------------------
        st.subheader("Employee Variance Drivers")
        st.dataframe(result, use_container_width=True)

        # -------------------------------
        # REASON CHART
        # -------------------------------
        st.subheader("Variance by Reason")

        chart = (
            result.groupby("Reason", as_index=False)["Variance"]
            .sum()
        )

        chart = chart[chart["Reason"] != "No Change"]
        chart["Abs"] = chart["Variance"].abs()
        chart = chart.sort_values("Abs", ascending=False)

        chart["Color"] = chart["Variance"].apply(
            lambda x: "Increase" if x >= 0 else "Reduction"
        )

        chart["Label"] = chart["Variance"].apply(indian_format)

        fig = px.bar(
            chart,
            x="Variance",
            y="Reason",
            orientation="h",
            color="Color",
            text="Label",
            color_discrete_map={
                "Increase":"green",
                "Reduction":"red"
            }
        )

        fig.update_traces(textposition="outside")
        fig.update_layout(height=600)

        st.plotly_chart(fig, use_container_width=True)

        # -------------------------------
        # DRILLDOWN
        # -------------------------------
        st.subheader("Variance Drill Down")

        reason_pick = st.selectbox(
            "Select Reason",
            sorted(result["Reason"].unique())
        )

        drill = result[result["Reason"] == reason_pick]

        st.dataframe(drill, use_container_width=True)

        # -------------------------------
        # TOP EMPLOYEE MOVERS
        # -------------------------------
        st.subheader("Top Employee Movers")

        movers = result.copy()
        movers["Abs"] = movers["Variance"].abs()

        movers = movers.sort_values("Abs", ascending=False).head(10)

        movers["Label"] = movers["Variance"].apply(indian_format)

        fig2 = px.bar(
            movers,
            x="Variance",
            y="Employee_Name",
            orientation="h",
            text="Label",
            color="Variance",
            color_continuous_scale="RdYlGn",
            hover_data=["Employee_ID", "Reason"]
        )

        fig2.update_traces(textposition="outside")
        fig2.update_layout(height=600)

        st.plotly_chart(fig2, use_container_width=True)

        # -------------------------------
        # TREND
        # -------------------------------
        st.subheader("Monthly Cost Trend")

        trend = (
            data.groupby("Month", as_index=False)["Cost"]
            .sum()
            .sort_values("Month")
        )

        fig3 = px.line(
            trend,
            x="Month",
            y="Cost",
            markers=True
        )

        fig3.update_layout(height=450)

        st.plotly_chart(fig3, use_container_width=True)

        # =========================================================
        # QUARTER-WISE VARIANCE ANALYSIS
        # =========================================================
        st.markdown("---")
        st.header("Quarter-wise Variance Analysis")

        # Assign quarter to every row for this customer
        qdata = data.copy()
        qdata = qdata.dropna(subset=["Month"])
        qdata["Quarter"] = qdata["Month"].dt.to_period("Q").astype(str)

        quarters_all = sorted(qdata["Quarter"].unique())

        if len(quarters_all) >= 2:

            # Quarter selectors in sidebar
            q_idx1 = max(0, len(quarters_all) - 2)
            q_idx2 = max(1, len(quarters_all) - 1)

            q1_pick = st.sidebar.selectbox("Quarter 1", quarters_all, index=q_idx1)
            q2_pick = st.sidebar.selectbox("Quarter 2", quarters_all, index=q_idx2)

            # -------------------------------
            # QUARTER DATA
            # -------------------------------
            dq1 = qdata[qdata["Quarter"] == q1_pick]
            dq2 = qdata[qdata["Quarter"] == q2_pick]

            gq1 = dq1.groupby(
                ["Employee_ID", "Employee_Name"],
                as_index=False
            ).agg(
                Cost_M1=("Cost", "sum"),
                Alloc_M1=("Allocation", "sum")
            )

            gq2 = dq2.groupby(
                ["Employee_ID", "Employee_Name"],
                as_index=False
            ).agg(
                Cost_M2=("Cost", "sum"),
                Alloc_M2=("Allocation", "sum")
            )

            qmerged = pd.merge(
                gq1, gq2,
                on=["Employee_ID", "Employee_Name"],
                how="outer"
            ).fillna(0)

            qmerged["Variance"] = qmerged["Cost_M2"] - qmerged["Cost_M1"]

            # -------------------------------
            # QUARTER REASONS
            # Use full df (all customers) with quarter col — same as monthly logic
            # -------------------------------
            df_q = df.dropna(subset=["Month"]).copy()
            df_q["Quarter"] = df_q["Month"].dt.to_period("Q").astype(str)

            def get_q_reason(row):

                emp = row["Employee_ID"]

                if row["Cost_M1"] > 0 and row["Cost_M2"] == 0:

                    moved = df_q[
                        (df_q["Employee_ID"] == emp) &
                        (df_q["Quarter"] == q2_pick) &
                        (df_q["Customer"] != customer)
                    ]

                    if not moved.empty:
                        names = ", ".join(sorted(moved["Customer"].unique()))
                        return f"Moved fully to {names}"

                    return "Resigned"

                elif row["Cost_M1"] == 0 and row["Cost_M2"] > 0:

                    prev = df_q[
                        (df_q["Employee_ID"] == emp) &
                        (df_q["Quarter"] == q1_pick) &
                        (df_q["Customer"] != customer)
                    ]

                    if not prev.empty:
                        names = ", ".join(sorted(prev["Customer"].unique()))
                        return f"Moved fully from {names}"

                    return "New Joiner"

                elif row["Alloc_M2"] < row["Alloc_M1"]:
                    return "Decrease in %"

                elif row["Alloc_M2"] > row["Alloc_M1"]:
                    return "Increase in %"

                elif row["Variance"] > 0:
                    return "Cost Increased"

                elif row["Variance"] < 0:
                    return "Cost Reduced"

                return "No Change"

            qmerged["Reason"] = qmerged.apply(get_q_reason, axis=1)

            qresult = qmerged.sort_values("Variance", ascending=False)

            # -------------------------------
            # QUARTER KPI
            # -------------------------------
            qtotal1 = qresult["Cost_M1"].sum()
            qtotal2 = qresult["Cost_M2"].sum()
            qvariance = qtotal2 - qtotal1

            st.subheader(f"{customer}: {q1_pick} vs {q2_pick}")

            qc1, qc2, qc3 = st.columns(3)
            qc1.metric("Quarter 1 Cost", indian_format(qtotal1))
            qc2.metric("Quarter 2 Cost", indian_format(qtotal2))
            qc3.metric("Variance", indian_format(qvariance))

            # -------------------------------
            # QUARTER EMPLOYEE VARIANCE DRIVERS TABLE
            # -------------------------------
            st.subheader("Employee Variance Drivers (Quarter-wise)")
            st.dataframe(qresult, use_container_width=True)

            # -------------------------------
            # QUARTER VARIANCE BY REASON CHART
            # -------------------------------
            st.subheader("Variance by Reason (Quarter-wise)")

            qchart = (
                qresult.groupby("Reason", as_index=False)["Variance"]
                .sum()
            )

            qchart = qchart[qchart["Reason"] != "No Change"]
            qchart["Abs"] = qchart["Variance"].abs()
            qchart = qchart.sort_values("Abs", ascending=False)

            qchart["Color"] = qchart["Variance"].apply(
                lambda x: "Increase" if x >= 0 else "Reduction"
            )

            qchart["Label"] = qchart["Variance"].apply(indian_format)

            fig_qr = px.bar(
                qchart,
                x="Variance",
                y="Reason",
                orientation="h",
                color="Color",
                text="Label",
                color_discrete_map={
                    "Increase": "green",
                    "Reduction": "red"
                }
            )

            fig_qr.update_traces(textposition="outside")
            fig_qr.update_layout(height=600)

            st.plotly_chart(fig_qr, use_container_width=True)

            # -------------------------------
            # QUARTER VARIANCE DRILL DOWN
            # -------------------------------
            st.subheader("Variance Drill Down (Quarter-wise)")

            q_reason_pick = st.selectbox(
                "Select Reason (Quarter)",
                sorted(qresult["Reason"].unique())
            )

            qdrill = qresult[qresult["Reason"] == q_reason_pick]

            st.dataframe(qdrill, use_container_width=True)

            # -------------------------------
            # QUARTER TOP EMPLOYEE MOVERS
            # -------------------------------
            st.subheader("Top Employee Movers (Quarter-wise)")

            qmovers = qresult.copy()
            qmovers["Abs"] = qmovers["Variance"].abs()
            qmovers = qmovers.sort_values("Abs", ascending=False).head(10)
            qmovers["Label"] = qmovers["Variance"].apply(indian_format)

            fig_qm = px.bar(
                qmovers,
                x="Variance",
                y="Employee_Name",
                orientation="h",
                text="Label",
                color="Variance",
                color_continuous_scale="RdYlGn",
                hover_data=["Employee_ID", "Reason"]
            )

            fig_qm.update_traces(textposition="outside")
            fig_qm.update_layout(height=600)

            st.plotly_chart(fig_qm, use_container_width=True)

            # -------------------------------
            # QUARTERLY COST TREND
            # -------------------------------
            st.subheader("Quarterly Cost Trend")

            q_trend = (
                qdata.groupby("Quarter", as_index=False)["Cost"]
                .sum()
                .sort_values("Quarter")
            )

            q_trend["Label"] = q_trend["Cost"].apply(indian_format)

            fig_qt = px.bar(
                q_trend,
                x="Quarter",
                y="Cost",
                text="Label",
                color_discrete_sequence=["#4C78A8"]
            )
            fig_qt.update_traces(textposition="outside")
            fig_qt.update_layout(height=450)
            st.plotly_chart(fig_qt, use_container_width=True)

        else:
            st.info("Not enough quarterly data available for this customer. At least 2 quarters of data are needed.")

        # -------------------------------
        # EMPLOYEE SEARCH
        # -------------------------------
        if emp_pick:

            emp_id = emp_pick.split(" - ")[0]

            st.subheader("Employee History")

            emp_df = df[df["Employee_ID"] == emp_id].sort_values("Month")

            st.dataframe(emp_df, use_container_width=True)

# =========================================================
# REVENUE DASHBOARD
# =========================================================
    if dashboard == "Revenue Dashboard":

            df = pd.read_excel(xls, sheet_name="Revenue Breakup")
            df.columns = df.columns.str.strip()

            month_cols = [
                "Apr25","May25","Jun25","Jul25","Aug25","Sep25",
                "Oct25","Nov25","Dec25","Jan26","Feb26","Mar26"
            ]

            df = df[["Customer","FY'26"] + month_cols]

            for c in ["FY'26"] + month_cols:
                df[c] = clean_num(df[c]).abs()

            customers = ["All Customers"] + sorted(df["Customer"].dropna().unique())

            customer = st.sidebar.selectbox("Customer", customers)

            month1 = st.sidebar.selectbox("Month", month_cols, index=10)
            month2 = st.sidebar.selectbox("Month-2", month_cols, index=11)

            top_n = st.sidebar.selectbox("Top Customers", [5,10,15,20], index=1)

            if customer == "All Customers":
                filtered = df.copy()
            else:
                filtered = df[df["Customer"] == customer]

            total1 = filtered[month1].sum()
            total2 = filtered[month2].sum()

            variance = total2 - total1
            growth = (variance / total1 * 100) if total1 != 0 else 0

            # -------------------------------
            # KPI
            # -------------------------------
            st.subheader("Revenue Dashboard")

            c1,c2,c3,c4 = st.columns(4)

            c1.metric(month1, indian_format(total1))
            c2.metric(month2, indian_format(total2))
            c3.metric("Variance", indian_format(variance))
            c4.metric("Growth %", f"{growth:.1f}%")

            # -------------------------------
            # MONTHLY TREND
            # -------------------------------
            st.subheader("Monthly Revenue Trend")

            if customer == "All Customers":

                trend = pd.DataFrame({
                    "Month": month_cols,
                    "Revenue": [df[m].sum() for m in month_cols]
                })

            else:

                row = filtered.iloc[0]

                trend = pd.DataFrame({
                    "Month": month_cols,
                    "Revenue": [row[m] for m in month_cols]
                })

            fig = px.line(
                trend,
                x="Month",
                y="Revenue",
                markers=True,
                text="Revenue"
            )

            fig.update_traces(
                texttemplate="₹%{text:,.0f}",
                textposition="top center"
            )

            fig.update_layout(height=450)

            st.plotly_chart(fig, use_container_width=True)

            # -------------------------------
            # REVENUE VARIANCE CHART
            # -------------------------------
            st.subheader(f"Revenue Variance ({month2} vs {month1})")

            rev = df[["Customer", month1, month2]].copy()

            rev["Variance"] = rev[month2] - rev[month1]
            rev["Abs"] = rev["Variance"].abs()

            rev = rev.sort_values("Abs", ascending=False).head(top_n)

            rev["Color"] = rev["Variance"].apply(
                lambda x: "Increase" if x >= 0 else "Reduction"
            )

            rev["Label"] = rev["Variance"].apply(indian_format)

            fig2 = px.bar(
                rev,
                x="Variance",
                y="Customer",
                orientation="h",
                color="Color",
                text="Label",
                color_discrete_map={
                    "Increase":"green",
                    "Reduction":"red"
                }
            )

            fig2.update_traces(textposition="outside")
            fig2.update_layout(height=650)

            st.plotly_chart(fig2, use_container_width=True)

            # -------------------------------
            # TOP CUSTOMERS
            # -------------------------------
            st.subheader(f"Top Customers - {month2}")

            top_df = df[["Customer", month2]].sort_values(
                month2, ascending=False
            ).head(top_n)

            fig3 = px.bar(
                top_df,
                x=month2,
                y="Customer",
                orientation="h",
                text=month2
            )

            fig3.update_traces(
                texttemplate="₹%{text:,.0f}",
                textposition="outside"
            )

            fig3.update_layout(height=650)

            st.plotly_chart(fig3, use_container_width=True)

            # -------------------------------
            # CHANGE TABLE
            # -------------------------------
            st.subheader("Biggest Customer Changes")

            st.dataframe(
                rev.sort_values("Variance", ascending=False),
                use_container_width=True
            )
# =========================================================
# MARGIN DASHBOARD (FIXED COST MONTH MATCH)
# =========================================================
# =========================================================
# FINAL PREMIUM MARGIN DASHBOARD (FULL + ENHANCED)
# =========================================================
    if dashboard == "Margin Dashboard":

            import numpy as np

            # ---------------------------------------------------
            # LOAD DATA
            # ---------------------------------------------------
            cost = pd.read_excel(xls, sheet_name="Employee Allocation")
            rev = pd.read_excel(xls, sheet_name="Revenue Breakup")

            cost.columns = cost.columns.str.strip()
            rev.columns = rev.columns.str.strip()

            month_cols = [
                "Apr25","May25","Jun25","Jul25","Aug25","Sep25",
                "Oct25","Nov25","Dec25","Jan26","Feb26","Mar26"
            ]

            # ---------------------------------------------------
            # CLEAN REVENUE
            # ---------------------------------------------------
            rev = rev[["Customer"] + month_cols].copy()

            for c in month_cols:
                rev[c] = clean_num(rev[c]).abs()

            # ---------------------------------------------------
            # CLEAN COST
            # ---------------------------------------------------
            cost = cost[
                [
                    "Month",
                    "Employee Id",
                    "Employee Name",
                    "Tagging",
                    "Tagging for Pivot",
                    "Final Allocation %",
                    "Total Cost in $",
                    "Total Cost in Rs"
                ]
            ].copy()

            cost["Month_Text"] = cost["Month"].astype(str).str.strip()

            cost["Employee Id"] = cost["Employee Id"].astype(str).str.strip()
            cost["Employee Name"] = cost["Employee Name"].astype(str).str.strip()

            cost["Customer"] = cost["Tagging"].astype(str).str.strip()
            cost["Pivot"] = cost["Tagging for Pivot"].astype(str).str.strip()

            cost["Alloc"] = clean_num(
                cost["Final Allocation %"].astype(str).str.replace("%","", regex=False)
            )
            cost["Alloc"] = cost["Alloc"].apply(lambda x: x*100 if x <= 1 else x)

            cost["Cost_USD"] = clean_num(cost["Total Cost in $"]).abs()
            cost["Cost_RS"] = clean_num(cost["Total Cost in Rs"]).abs()

            cost["Cost_Type"] = np.where(
                cost["Customer"] == cost["Pivot"],
                "Direct Billable",
                "Buffer / Shared"
            )

            # ---------------------------------------------------
            # FILTERS
            # ---------------------------------------------------
            customers = ["All Customers"] + sorted(rev["Customer"].dropna().unique())

            customer = st.sidebar.selectbox("Customer", customers)

            month1 = st.sidebar.selectbox("Month 1", month_cols, index=10)
            month2 = st.sidebar.selectbox("Month 2", month_cols, index=11)

            # ---------------------------------------------------
            # FILTERED DATA
            # ---------------------------------------------------
            if customer == "All Customers":
                rev_f = rev.copy()
                cost_f = cost.copy()
            else:
                rev_f = rev[rev["Customer"] == customer]
                cost_f = cost[cost["Customer"] == customer]

            # ---------------------------------------------------
            # KPI VALUES
            # ---------------------------------------------------
            rev1 = rev_f[month1].sum()
            rev2 = rev_f[month2].sum()

            c1 = cost_f[cost_f["Month_Text"] == month1]
            c2 = cost_f[cost_f["Month_Text"] == month2]

            cost1 = c1["Cost_USD"].sum()
            cost2 = c2["Cost_USD"].sum()

            gm1 = rev1 - cost1
            gm2 = rev2 - cost2

            gm_pct2 = (gm2/rev2*100) if rev2 != 0 else 0

            # ---------------------------------------------------
            # EMPLOYEE VARIANCE (for forex + drivers)
            # ---------------------------------------------------
            grp1 = c1.groupby(["Employee Id","Employee Name"], as_index=False).agg(
                Cost_M1=("Cost_USD","sum"),
                Rs_M1=("Cost_RS","sum"),
                Alloc_M1=("Alloc","sum")
            )

            grp2 = c2.groupby(["Employee Id","Employee Name"], as_index=False).agg(
                Cost_M2=("Cost_USD","sum"),
                Rs_M2=("Cost_RS","sum"),
                Alloc_M2=("Alloc","sum")
            )

            emp = pd.merge(grp1, grp2,
                on=["Employee Id","Employee Name"],
                how="outer"
            ).fillna(0)

            emp["Variance"] = emp["Cost_M2"] - emp["Cost_M1"]

            # Forex (correct)
            emp["Forex"] = np.where(
                (abs(emp["Rs_M2"] - emp["Rs_M1"]) < 1) &
                (abs(emp["Variance"]) > 1),
                emp["Variance"],
                0
            )

            forex_impact = emp["Forex"].sum()

            # ---------------------------------------------------
            # REASON LOGIC
            # ---------------------------------------------------
            def get_reason(row):

                emp = row["Employee_ID"]

                # ==========================
                # FILTERS FOR PERIODS
                # ==========================
                if view_type == "Month":

                    current_period = (
                        (df["Month"].dt.date == m2.date())
                    )

                    previous_period = (
                        (df["Month"].dt.date == m1.date())
                    )

                else:

                    current_period = (
                        (df["Quarter"] == period2)
                    )

                    previous_period = (
                        (df["Quarter"] == period1)
                    )

                # ==========================
                # MOVED OUT
                # ==========================
                if row["Cost_M1"] > 0 and row["Cost_M2"] == 0:

                    moved = df[
                        (df["Employee_ID"] == emp) &
                        current_period &
                        (df["Customer"] != customer)
                    ]

                    if not moved.empty:

                        names = ", ".join(
                            sorted(moved["Customer"].unique())
                        )

                        return f"Moved fully to {names}"

                    return "Resigned"

                # ==========================
                # MOVED IN
                # ==========================
                elif row["Cost_M1"] == 0 and row["Cost_M2"] > 0:

                    prev = df[
                        (df["Employee_ID"] == emp) &
                        previous_period &
                        (df["Customer"] != customer)
                    ]

                    if not prev.empty:

                        names = ", ".join(
                            sorted(prev["Customer"].unique())
                        )

                        return f"Moved fully from {names}"

                    return "New Joiner"

                # ==========================
                # ALLOCATION CHANGE
                # ==========================
                elif row["Alloc_M2"] < row["Alloc_M1"]:
                    return "Decrease in %"

                elif row["Alloc_M2"] > row["Alloc_M1"]:
                    return "Increase in %"

                # ==========================
                # COST CHANGE
                # ==========================
                elif row["Variance"] > 0:
                    return "Cost Increased"

                elif row["Variance"] < 0:
                    return "Cost Reduced"

                return "No Change"
  

            # ---------------------------------------------------
            # KPI DISPLAY
            # ---------------------------------------------------
            st.subheader("Premium Margin Dashboard")

            a,b,c,d = st.columns(4)
            a.metric(f"Revenue ({month1})", usd_format(rev1))
            b.metric(f"Revenue ({month2})", usd_format(rev2))
            c.metric(f"Cost ({month1})", usd_format(cost1))
            d.metric(f"Cost ({month2})", usd_format(cost2))

            e,f,g,h = st.columns(4)
            e.metric("Margin M1", usd_format(gm1))
            f.metric("Margin M2", usd_format(gm2))
            g.metric("GM Variance", usd_format(gm2-gm1))
            h.metric("GM % (M2)", f"{gm_pct2:.1f}%")

            i,j,k = st.columns(3)
            i.metric("Revenue Variance", usd_format(rev2-rev1))
            j.metric("Cost Variance", usd_format(cost2-cost1))
            k.metric("Forex Impact", usd_format(forex_impact))

            # ---------------------------------------------------
            # TREND
            # ---------------------------------------------------
            trend = []

            for m in month_cols:
                r = rev_f[m].sum()
                cst = cost_f[cost_f["Month_Text"] == m]["Cost_USD"].sum()

                trend.append({"Month": m, "Revenue": r, "Cost": cst, "Margin": r-cst})

            trend = pd.DataFrame(trend)

            st.subheader("Revenue / Cost / Margin Trend")

            fig = px.line(trend, x="Month", y=["Revenue","Cost","Margin"], markers=True)
            st.plotly_chart(fig, use_container_width=True)

            # ---------------------------------------------------
            # COST VARIANCE DRIVERS
            # ---------------------------------------------------
            st.subheader("Cost Variance Drivers (USD)")

            drv = emp.groupby("Reason", as_index=False)["Variance"].sum()

            fig2 = px.bar(
                drv,
                x="Variance",
                y="Reason",
                orientation="h",
                color="Variance",
                color_continuous_scale="RdYlGn"
            )

            st.plotly_chart(fig2, use_container_width=True)

            # ---------------------------------------------------
            # EMPLOYEE VARIANCE CHART
            # ---------------------------------------------------
            st.subheader("Employee Cost Variance")

            emp_chart = emp.copy()
            emp_chart["Abs"] = emp_chart["Variance"].abs()

            emp_chart = emp_chart.sort_values("Abs", ascending=False).head(15)

            fig_emp = px.bar(
                emp_chart,
                x="Variance",
                y="Employee Name",
                orientation="h",
                text="Variance",
                color="Variance",
                color_continuous_scale="RdYlGn",
                hover_data=["Employee Id", "Reason"]
            )

            fig_emp.update_traces(
                texttemplate="$%{text:,.0f}",
                textposition="outside"
            )

            fig_emp.update_layout(height=600)

            st.plotly_chart(fig_emp, use_container_width=True)

            # ---------------------------------------------------
            # CUSTOMER GM VARIANCE (NEW)
            # ---------------------------------------------------
            # ---------------------------------------------------
            # CUSTOMER GM VARIANCE (FIXED)
            # ---------------------------------------------------
            # ---------------------------------------------------
            # DRILLDOWN
            # ---------------------------------------------------
            st.subheader("Variance Drilldown")

            pick = st.selectbox("Select Reason", sorted(emp["Reason"].unique()))

            st.dataframe(emp[emp["Reason"] == pick], use_container_width=True)
            # =========================================================
            # CUSTOMER MONTHLY ANALYSIS (HEATMAP + INSIGHTS)
            # =========================================================
            st.subheader("Customer Monthly Performance Analysis")

            exclude_list = [
                "bench",
                "admin",
                "internal project",
                "r&d capitalised",
                "delpheon",
                "rdpms",
                "directors remuneration"
            ]

            # -----------------------------
            # FILTER CUSTOMERS
            # -----------------------------
            valid_rev = rev[~rev["Customer"].str.lower().isin(exclude_list)]

            # -----------------------------
            # BUILD DATA
            # -----------------------------
            rows = []

            for cust in valid_rev["Customer"].unique():

                rev_row = rev[rev["Customer"] == cust]

                for m in month_cols:

                    revenue = rev_row[m].sum()

                    cost_val = cost[
                        (cost["Customer"] == cust) &
                        (cost["Month_Text"] == m)
                    ]["Cost_USD"].sum()

                    margin = revenue - cost_val
                    margin_pct = (margin / revenue * 100) if revenue != 0 else 0

                    rows.append({
                        "Customer": cust,
                        "Month": m,
                        "Revenue": revenue,
                        "Cost": cost_val,
                        "Margin": margin,
                        "Margin %": margin_pct
                    })

            df_all = pd.DataFrame(rows)

            # -----------------------------
            # SORT CUSTOMERS BY REVENUE
            # -----------------------------
            order = (
                df_all.groupby("Customer")["Revenue"]
                .sum()
                .sort_values(ascending=False)
                .index
            )

            df_all["Customer"] = pd.Categorical(
                df_all["Customer"],
                categories=order,
                ordered=True
            )

            df_all = df_all.sort_values(["Customer", "Month"])

           
            # =========================================================
            # 📊 TOP 10 CUSTOMER TREND
            # =========================================================
            st.subheader("Top 10 Customers - Margin Trend")

            top10 = df_all[df_all["Customer"].isin(order[:10])]

            fig_top = px.line(
                top10,
                x="Month",
                y="Margin",
                color="Customer",
                markers=True
            )

            fig_top.update_layout(height=600)

            st.plotly_chart(fig_top, use_container_width=True)
            # =========================================================
            # =========================================================
            # CUSTOMER MONTHLY ANALYSIS (ENHANCED FINAL)
            # =========================================================
            st.subheader("Customer Monthly Revenue / Cost / Margin")

            exclude_list = [
                "bench",
                "admin",
                "internal project",
                "r&d capitalised",
                "delpheon",
                "rdpms",
                "directors remuneration"
            ]

            # -----------------------------
            # FILTER CUSTOMERS (BASE)
            # -----------------------------
            valid_rev = rev[~rev["Customer"].str.lower().isin(exclude_list)]

            # -----------------------------
            # BUILD DATA
            # -----------------------------
            rows = []

            for cust in valid_rev["Customer"].unique():

                rev_row = rev[rev["Customer"] == cust]

                for m in month_cols:

                    revenue = rev_row[m].sum()

                    cost_val = cost[
                        (cost["Customer"] == cust) &
                        (cost["Month_Text"] == m)
                    ]["Cost_USD"].sum()

                    margin = revenue - cost_val
                    margin_pct = (margin / revenue * 100) if revenue != 0 else 0

                    # 🔥 REMOVE ROWS WHERE BOTH ZERO
                    if not (revenue == 0 and cost_val == 0):
                        rows.append({
                            "Customer": cust,
                            "Month": m,
                            "Revenue": revenue,
                            "Cost": cost_val,
                            "Margin": margin,
                            "Margin %": margin_pct
                        })

            df_all = pd.DataFrame(rows)

            # -----------------------------
            # MONTH ORDER FIX
            # -----------------------------
            df_all["Month"] = pd.Categorical(
                df_all["Month"],
                categories=month_cols,
                ordered=True
            )

            # -----------------------------
            # CUSTOMER FILTER
            # -----------------------------
            st.subheader("Filters")

            selected_customers = st.multiselect(
                "Select Customers",
                sorted(df_all["Customer"].unique()),
                default=sorted(df_all["Customer"].unique())
            )

            df_filtered = df_all[df_all["Customer"].isin(selected_customers)]

            # -----------------------------
            # VIEW FILTERS
            # -----------------------------
            view_option = st.radio(
                "Select View",
                [
                    "All Data",
                    "🔴 Problem Rows",
                    "🟡 Low Margin (<20%)",
                    "🟢 High Margin (>40%)",
                    "⚠️ Revenue without Cost",
                    "⚠️ Cost without Revenue"
                ],
                horizontal=True
            )

            if view_option == "🔴 Problem Rows":
                df_filtered = df_filtered[
                    (df_filtered["Margin"] < 0) |
                    ((df_filtered["Revenue"] == 0) & (df_filtered["Cost"] > 0))
                ]

            elif view_option == "🟡 Low Margin (<20%)":
                df_filtered = df_filtered[df_filtered["Margin %"] < 20]

            elif view_option == "🟢 High Margin (>40%)":
                df_filtered = df_filtered[df_filtered["Margin %"] > 40]

            elif view_option == "⚠️ Revenue without Cost":
                df_filtered = df_filtered[
                    (df_filtered["Revenue"] > 0) & (df_filtered["Cost"] == 0)
                ]

            elif view_option == "⚠️ Cost without Revenue":
                df_filtered = df_filtered[
                    (df_filtered["Revenue"] == 0) & (df_filtered["Cost"] > 0)
                ]

            # -----------------------------
            # SORT BY CUSTOMER + MONTH
            # -----------------------------
            df_filtered = df_filtered.sort_values(["Customer", "Month"])

            # -----------------------------
            # DISPLAY (VISUAL GROUPING)
            # -----------------------------
            def highlight_rows(row):

                margin = row["Margin"]
                revenue = row["Revenue"]
                cost = row["Cost"]
                margin_pct = row["Margin %"]

                style = [""] * len(row)

                if (margin < 0) or (revenue == 0 and cost > 0):
                    style = ["background-color: #ffcccc"] * len(row)
                elif margin_pct < 20:
                    style = ["background-color: #fff3cd"] * len(row)
                elif margin_pct > 40:
                    style = ["background-color: #d4edda"] * len(row)

                return style

            # -----------------------------
            # -----------------------------
            # DISPLAY PER CUSTOMER
            # -----------------------------
            for cust in df_filtered["Customer"].unique():

                st.markdown(f"### {cust}")

                temp = df_filtered[df_filtered["Customer"] == cust].copy()

                # -----------------------------
                # KEEP RAW FOR LOGIC
                # -----------------------------
                temp_raw = temp.copy()

                # -----------------------------
                # FORMAT DISPLAY
                # -----------------------------
                display = temp.copy()

                display["Revenue"] = display["Revenue"].apply(usd_format)
                display["Cost"] = display["Cost"].apply(usd_format)
                display["Margin"] = display["Margin"].apply(usd_format)
                display["Margin %"] = display["Margin %"].apply(lambda x: f"{x:.1f}%")

                # -----------------------------
                # HIGHLIGHT FUNCTION (USES RAW)
                # -----------------------------
                def highlight_rows(row):

                    original = temp_raw.loc[row.name]

                    revenue = original["Revenue"]
                    cost = original["Cost"]
                    margin = original["Margin"]
                    margin_pct = original["Margin %"]

                    style = [""] * len(row)

                    # 🔴 Critical
                    if (margin < 0) or (revenue == 0 and cost > 0):
                        style = ["background-color: #ffcccc"] * len(row)

                    # 🟡 Warning
                    elif margin_pct < 20:
                        style = ["background-color: #fff3cd"] * len(row)

                    # 🟢 Good
                    elif margin_pct > 40:
                        style = ["background-color: #d4edda"] * len(row)

                    return style

                # -----------------------------
                # DISPLAY
                # -----------------------------
                st.dataframe(
                    display.style.apply(highlight_rows, axis=1),
                    use_container_width=True
                )
                # =========================================================
# ALLOCATION DASHBOARD (FULL FINAL)
# ================================
# =========================================================
# EMPLOYEE DASHBOARD
# =========================================================
    if dashboard == "Employee Dashboard":

        df = pd.read_excel(xls, sheet_name="Employee Allocation")
        df.columns = df.columns.str.strip()

        df = df[
            [
                "Month-2",
                "Employee Id",
                "Employee Name",
                "Tagging",
                "Final Allocation %",
                "Total Cost in Rs"
            ]
        ]

        df.columns = [
            "Month",
            "Employee_ID",
            "Employee_Name",
            "Customer",
            "Allocation",
            "Cost"
        ]

        df["Month"] = pd.to_datetime(df["Month"], dayfirst=True, errors="coerce")
        df["Cost"] = clean_num(df["Cost"])
        df["Allocation"] = clean_num(
            df["Allocation"].astype(str).str.replace("%", "", regex=False)
        )
        df["Allocation"] = df["Allocation"].apply(
            lambda x: x * 100 if x <= 1 else x
        )
        df["Employee_ID"] = df["Employee_ID"].astype(str).str.strip()
        df["Customer"] = df["Customer"].astype(str).str.strip()

        # Fix FY window: Apr 2025 - Mar 2026
        fy_start = pd.Timestamp("2025-04-01")
        fy_end   = pd.Timestamp("2026-03-31")
        df = df[(df["Month"] >= fy_start) & (df["Month"] <= fy_end)]

        # Month order label
        month_order = pd.date_range("2025-04-01", periods=12, freq="MS")
        month_labels = {m: m.strftime("%b %Y") for m in month_order}
        df["Month_Label"] = df["Month"].apply(
            lambda x: x.strftime("%b %Y") if pd.notna(x) else None
        )
        ordered_labels = [m.strftime("%b %Y") for m in month_order]

        # -------------------------------
        # EMPLOYEE SEARCH
        # -------------------------------
        emp_master = (
            df[["Employee_ID", "Employee_Name"]]
            .drop_duplicates()
            .sort_values("Employee_Name")
        )
        emp_master["Display"] = emp_master["Employee_ID"] + " - " + emp_master["Employee_Name"]

        st.sidebar.markdown("### Employee Search")
        emp_pick = st.sidebar.selectbox(
            "Select Employee",
            [""] + emp_master["Display"].tolist()
        )

        if not emp_pick:
            st.info("Please select an employee from the sidebar to view their dashboard.")
            st.stop()

        emp_id   = emp_pick.split(" - ")[0]
        emp_name = emp_pick.split(" - ", 1)[1]

        edf = df[df["Employee_ID"] == emp_id].copy()

        # -------------------------------
        # SUMMARY CARD
        # -------------------------------
        st.markdown(f"## 👤 {emp_name} ({emp_id})")
        st.markdown("**FY 2025-26 · Apr 2025 – Mar 2026**")

        latest_month = edf["Month"].max()
        latest_data  = edf[edf["Month"] == latest_month]

        total_cost_fy     = edf["Cost"].sum()
        avg_alloc_fy      = edf.groupby("Month")["Allocation"].sum().mean()
        num_customers     = edf["Customer"].nunique()
        latest_cost       = latest_data["Cost"].sum()
        latest_alloc      = latest_data["Allocation"].sum()
        latest_customers  = latest_data["Customer"].nunique()

        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("FY Total Cost",        indian_format(total_cost_fy))
        sc2.metric("Avg Monthly Allocation", f"{avg_alloc_fy:.1f}%")
        sc3.metric("Customers Worked On",  str(num_customers))
        sc4.metric(
            f"Latest Month ({latest_month.strftime('%b %Y')}) Cost",
            indian_format(latest_cost),
            delta=f"Alloc: {latest_alloc:.0f}%"
        )

        st.markdown("---")

        # -------------------------------
        # SECTION 1 — ALLOCATION STACKED BAR
        # -------------------------------
        st.subheader("Allocation Across Customers (Month-wise)")

        alloc_pivot = (
            edf.groupby(["Month_Label", "Customer"], as_index=False)["Allocation"]
            .sum()
        )

        # Force all 12 months to exist for every customer so order is always correct
        all_customers = alloc_pivot["Customer"].unique()
        full_index = pd.MultiIndex.from_product(
            [ordered_labels, all_customers],
            names=["Month_Label", "Customer"]
        )
        alloc_pivot = (
            alloc_pivot
            .set_index(["Month_Label", "Customer"])
            .reindex(full_index, fill_value=0)
            .reset_index()
        )

        alloc_pivot["Month_Label"] = pd.Categorical(
            alloc_pivot["Month_Label"], categories=ordered_labels, ordered=True
        )
        alloc_pivot = alloc_pivot.sort_values("Month_Label")

        fig_alloc = px.bar(
            alloc_pivot,
            x="Month_Label",
            y="Allocation",
            color="Customer",
            text="Allocation",
            barmode="stack",
            height=450,
            category_orders={"Month_Label": ordered_labels}
        )

        # Enforce month order on the x-axis explicitly
        fig_alloc = px.bar(
            alloc_pivot,
            x="Month_Label",
            y="Allocation",
            color="Customer",
            text="Allocation",
            barmode="stack",
            height=450,
            category_orders={"Month_Label": ordered_labels}   # ← this line fixes the order
        )

        # Enforce month order on the x-axis explicitly
        fig_alloc = px.bar(
            alloc_pivot,
            x="Month_Label",
            y="Allocation",
            color="Customer",
            text="Allocation",
            barmode="stack",
            height=450,
            category_orders={"Month_Label": ordered_labels}   # ← this line fixes the order
        )

        # Enforce month order on the x-axis explicitly
        fig_alloc = px.bar(
            alloc_pivot,
            x="Month_Label",
            y="Allocation",
            color="Customer",
            text="Allocation",
            barmode="stack",
            height=450,
            category_orders={"Month_Label": ordered_labels}   # ← this line fixes the order
        )

        # Enforce month order on the x-axis explicitly
        fig_alloc = px.bar(
            alloc_pivot,
            x="Month_Label",
            y="Allocation",
            color="Customer",
            text="Allocation",
            barmode="stack",
            height=450,
            category_orders={"Month_Label": ordered_labels}   # ← this line fixes the order
        )

        fig_alloc = px.bar(
            alloc_pivot,
            x="Month_Label",
            y="Allocation",
            color="Customer",
            text="Allocation",
            barmode="stack",
            height=450
        )
        fig_alloc.update_traces(texttemplate="%{text:.0f}%", textposition="inside")
        fig_alloc.update_layout(
            xaxis_title="Month",
            yaxis_title="Allocation %",
            legend_title="Customer",
            yaxis=dict(range=[0, 120])
        )
        st.plotly_chart(fig_alloc, use_container_width=True)

        # -------------------------------
        # ALLOCATION HEATMAP TABLE
        # -------------------------------
        st.subheader("Allocation Heatmap (Customer × Month)")

        heat_pivot = edf.pivot_table(
            index="Customer",
            columns="Month_Label",
            values="Allocation",
            aggfunc="sum"
        ).reindex(columns=ordered_labels).fillna(0)

        # Style: color intensity by value
        styled = heat_pivot.style.background_gradient(
            cmap="YlOrRd", axis=None
        ).format("{:.0f}%")

        st.dataframe(styled, use_container_width=True)

        st.markdown("---")

        # -------------------------------
        # SECTION 2 — COST TREND
        # -------------------------------
        st.subheader("Monthly Cost & Allocation Trend")

        cost_trend = (
            edf.groupby("Month_Label", as_index=False)
            .agg(Cost=("Cost", "sum"), Allocation=("Allocation", "sum"))
        )
        cost_trend["Month_Label"] = pd.Categorical(
            cost_trend["Month_Label"], categories=ordered_labels, ordered=True
        )
        cost_trend = cost_trend.sort_values("Month_Label")

        fig_cost = px.line(
            cost_trend,
            x="Month_Label",
            y="Cost",
            markers=True,
            height=400,
            labels={"Month_Label": "Month", "Cost": "Cost (₹)"}
        )

        # Overlay allocation as a secondary line on secondary y-axis
        fig_cost.add_scatter(
            x=cost_trend["Month_Label"],
            y=cost_trend["Allocation"],
            mode="lines+markers",
            name="Allocation %",
            yaxis="y2",
            line=dict(dash="dash", color="orange")
        )

        fig_cost.update_layout(
            yaxis=dict(title="Cost (₹)"),
            yaxis2=dict(
                title="Allocation %",
                overlaying="y",
                side="right",
                showgrid=False,
                range=[0, 150]
            ),
            legend=dict(x=0.01, y=0.99)
        )

        st.plotly_chart(fig_cost, use_container_width=True)

        st.markdown("---")

        # -------------------------------
        # SECTION 3 — DONUT: USER-PICKED MONTH
        # -------------------------------
        st.subheader("Customer Split — Snapshot Month")

        available_months = [m for m in ordered_labels if m in edf["Month_Label"].values]
        snap_month = st.selectbox("Select month for snapshot", available_months,
                                  index=len(available_months)-1)

        snap_data = edf[edf["Month_Label"] == snap_month]

        if snap_data.empty:
            st.info(f"No data for {snap_month}.")
        else:
            snap_grp = snap_data.groupby("Customer", as_index=False).agg(
                Allocation=("Allocation", "sum"),
                Cost=("Cost", "sum")
            )

            col_donut, col_snap = st.columns(2)

            with col_donut:
                fig_donut = px.pie(
                    snap_grp,
                    names="Customer",
                    values="Allocation",
                    hole=0.45,
                    title=f"Allocation % — {snap_month}"
                )
                fig_donut.update_traces(textinfo="label+percent")
                st.plotly_chart(fig_donut, use_container_width=True)

            with col_snap:
                fig_cost_snap = px.bar(
                    snap_grp,
                    x="Customer",
                    y="Cost",
                    text=snap_grp["Cost"].apply(indian_format),
                    color="Customer",
                    title=f"Cost by Customer — {snap_month}"
                )
                fig_cost_snap.update_traces(textposition="outside")
                fig_cost_snap.update_layout(showlegend=False, height=400)
                st.plotly_chart(fig_cost_snap, use_container_width=True)

        st.markdown("---")

        # -------------------------------
        # SECTION 4 — MONTH-ON-MONTH ALLOCATION CHANGE
        # -------------------------------
        st.subheader("Month-on-Month Allocation Change")

        mom_months = [m for m in ordered_labels if m in edf["Month_Label"].values]

        mc1, mc2 = st.columns(2)
        mom_m1 = mc1.selectbox("From Month", mom_months, index=max(0, len(mom_months)-2))
        mom_m2 = mc2.selectbox("To Month",   mom_months, index=max(1, len(mom_months)-1))

        mom_df1 = edf[edf["Month_Label"] == mom_m1].groupby("Customer", as_index=False).agg(
            Alloc_M1=("Allocation", "sum"), Cost_M1=("Cost", "sum")
        )
        mom_df2 = edf[edf["Month_Label"] == mom_m2].groupby("Customer", as_index=False).agg(
            Alloc_M2=("Allocation", "sum"), Cost_M2=("Cost", "sum")
        )

        mom_merged = pd.merge(mom_df1, mom_df2, on="Customer", how="outer").fillna(0)
        mom_merged["Alloc Change"]  = mom_merged["Alloc_M2"] - mom_merged["Alloc_M1"]
        mom_merged["Cost Variance"] = mom_merged["Cost_M2"]  - mom_merged["Cost_M1"]

        def mom_reason(row):
            if row["Alloc_M1"] > 0 and row["Alloc_M2"] == 0:
                return "Removed from project"
            elif row["Alloc_M1"] == 0 and row["Alloc_M2"] > 0:
                return "Added to project"
            elif row["Alloc Change"] < 0:
                return "Allocation decreased"
            elif row["Alloc Change"] > 0:
                return "Allocation increased"
            return "No change"

        mom_merged["Reason"] = mom_merged.apply(mom_reason, axis=1)

        # Format for display
        mom_display = mom_merged.copy()
        mom_display["Alloc_M1"]      = mom_display["Alloc_M1"].apply(lambda x: f"{x:.0f}%")
        mom_display["Alloc_M2"]      = mom_display["Alloc_M2"].apply(lambda x: f"{x:.0f}%")
        mom_display["Alloc Change"]  = mom_display["Alloc Change"].apply(lambda x: f"{x:+.0f}%")
        mom_display["Cost_M1"]       = mom_display["Cost_M1"].apply(indian_format)
        mom_display["Cost_M2"]       = mom_display["Cost_M2"].apply(indian_format)
        mom_display["Cost Variance"] = mom_display["Cost Variance"].apply(indian_format)
        mom_display = mom_display.rename(columns={
            "Alloc_M1": f"Alloc {mom_m1}",
            "Alloc_M2": f"Alloc {mom_m2}",
            "Cost_M1":  f"Cost {mom_m1}",
            "Cost_M2":  f"Cost {mom_m2}",
        })

        st.dataframe(mom_display, use_container_width=True)

        # Alloc change bar chart
        fig_mom = px.bar(
            mom_merged[mom_merged["Reason"] != "No change"],
            x="Customer",
            y="Alloc Change",
            color="Reason",
            text=mom_merged[mom_merged["Reason"] != "No change"]["Alloc Change"].apply(
                lambda x: f"{x:+.0f}%"
            ),
            color_discrete_map={
                "Allocation increased":  "green",
                "Allocation decreased":  "red",
                "Added to project":      "blue",
                "Removed from project":  "orange"
            },
            height=400,
            title=f"Allocation Change: {mom_m1} → {mom_m2}"
        )
        fig_mom.update_traces(textposition="outside")
        fig_mom.update_layout(yaxis_title="Allocation Change %")
        st.plotly_chart(fig_mom, use_container_width=True)
