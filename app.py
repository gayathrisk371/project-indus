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
        ["Cost Dashboard", "Revenue Dashboard","Margin Dashboard","Allocation Dashboard"]
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
                if row["Cost_M1"] == 0 and row["Cost_M2"] > 0:
                    return "New Joiner"
                if row["Cost_M1"] > 0 and row["Cost_M2"] == 0:
                    return "Resigned"
                if row["Alloc_M2"] > row["Alloc_M1"]:
                    return "Increase in Allocation %"
                if row["Alloc_M2"] < row["Alloc_M1"]:
                    return "Decrease in Allocation %"
                if abs(row["Rs_M2"] - row["Rs_M1"]) < 1 and abs(row["Variance"]) > 1:
                    return "Forex Fluctuation"
                if row["Variance"] > 0:
                    return "Salary Increase"
                if row["Variance"] < 0:
                    return "Salary Reduction"
                return "Miscellaneous"

            emp["Reason"] = emp.apply(get_reason, axis=1)

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

# =========================
# ALLOCATION DASHBOARD
# =========================
    if dashboard == "Allocation Dashboard":

                st.header("Allocation Dashboard")
                st.subheader("Employee Allocation Drilldown")

                # ---------- LOAD DATA ----------
                try:
                    alloc = pd.read_excel(xls, sheet_name="Employee Allocation")
                except:
                    st.error("Sheet 'Employee Allocation' not found")
                    st.stop()

                # ---------- COLUMN CLEANUP ----------
                alloc.columns = alloc.columns.str.strip()

                required_cols = ["Month", "Employee Name", "Tagging", "Final Allocation %"]

                for col in required_cols:
                    if col not in alloc.columns:
                        st.error(f"Missing column: {col}")
                        st.stop()

                # ---------- CLEAN DATA ----------
                alloc["Month"] = alloc["Month"].astype(str)

                alloc["Final Allocation %"] = (
                    alloc["Final Allocation %"]
                    .astype(str)
                    .str.replace("%", "", regex=False)
                    .str.strip()
                )

                alloc["Final Allocation %"] = pd.to_numeric(alloc["Final Allocation %"], errors="coerce").fillna(0)

                # ---------- EMPLOYEE SELECT ----------
                emp_list = sorted(alloc["Employee Name"].dropna().unique())

                selected_emp = st.selectbox("Select Employee", emp_list)

                emp_df = alloc[alloc["Employee Name"] == selected_emp].copy()

                if emp_df.empty:
                    st.warning("No data for selected employee")
                    st.stop()

                # ---------- GROUP LOGIC ----------
                def simplify(group):
                    big = group[group["Final Allocation %"] >= 50]

                    if len(big) == 0:
                        return pd.Series({
                            "Customer": "Multiple",
                            "Allocation": group["Final Allocation %"].sum()
                        })

                    top = big.sort_values("Final Allocation %", ascending=False).iloc[0]

                    return pd.Series({
                        "Customer": top["Tagging"],
                        "Allocation": top["Final Allocation %"]
                    })

                plot_df = emp_df.groupby("Month").apply(simplify).reset_index()

                # ---------- SORT MONTHS ----------
                def sort_month(m):
                    try:
                        return pd.to_datetime(m, format="%b%y")
                    except:
                        return pd.to_datetime(m, errors="coerce")

                plot_df["Month_sort"] = plot_df["Month"].apply(sort_month)
                plot_df = plot_df.sort_values("Month_sort")

                # ---------- CHART ----------
                fig = px.bar(
                    plot_df,
                    x="Month",
                    y="Allocation",
                    color="Customer",
                    text="Allocation",
                    title=f"{selected_emp} Allocation Trend"
                )

                fig.update_traces(
                    texttemplate="%{text:.0f}%",
                    textposition="inside"
                )

                fig.update_layout(
                    yaxis_title="Allocation %",
                    xaxis_title="Month",
                    uniformtext_minsize=8,
                    uniformtext_mode="hide"
                )

                st.plotly_chart(fig, use_container_width=True)
