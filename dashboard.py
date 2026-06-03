import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Smart LMS Dashboard", layout="wide")

df = pd.read_csv("mdl_logstore_standard_log.csv")

# ETL / cleaning
df["datetime"] = pd.to_datetime(df["timecreated"], unit="s")
df["date"] = df["datetime"].dt.date

course_map = {
    0: "ICT 301",
    1: "ICT 302",
    2: "ICT 303",
    3: "ICT 304",
}

df["course_name"] = df["courseid"].map(course_map).fillna("Course " + df["courseid"].astype(str))

# Export full cleaned CSV
df.to_csv("cleaned_moodle_logs.csv", index=False)

st.title("Smart LMS Dashboard Prototype")

selected_unit = st.selectbox(
    "Filter by unit",
    ["All units"] + sorted(df["course_name"].unique().tolist())
)

if selected_unit == "All units":
    filtered_df = df.copy()
else:
    filtered_df = df[df["course_name"] == selected_unit]

# Download button
csv = filtered_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download Cleaned CSV",
    data=csv,
    file_name="cleaned_moodle_logs.csv",
    mime="text/csv"
)

col1, col2, col3, col4 = st.columns(4)

risk_df = filtered_df[filtered_df["action"].isin(["failed"])]

col1.metric("Total Events", len(filtered_df))
col2.metric("Active Users", filtered_df["userid"].nunique())
col3.metric("Courses", filtered_df["courseid"].nunique())
col4.metric("At-Risk Users", risk_df["userid"].nunique())

st.subheader("Activity Trend")
daily = filtered_df.groupby("date").size().reset_index(name="events")
fig = px.line(daily, x="date", y="events", markers=True)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Unit Engagement Overview")

view_mode = st.radio(
    "Select engagement view",
    ["Daily", "Week", "Month"],
    horizontal=True
)

if view_mode == "Daily":
    engagement = pd.DataFrame({
        "period": ["Mon 13", "Tue 14", "Wed 15", "Thu 16", "Fri 17", "Sat 18", "Sun 19"],
        "Active Students": [130, 137, 145, 141, 126, 45, 38],
        "Total Enrolled": [155, 155, 155, 155, 155, 155, 155]
    })

elif view_mode == "Week":
    engagement = pd.DataFrame({
        "period": ["Week 1", "Week 2", "Week 3", "Week 4", "Week 5", "Week 6", "Week 7", "Week 8"],
        "Active Students": [148, 152, 145, 141, 143, 138, 140, 136],
        "Total Enrolled": [155, 155, 155, 155, 155, 155, 155, 155]
    })

else:
    engagement = pd.DataFrame({
        "period": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
        "Active Students": [120, 132, 144, 139, 136, 141],
        "Total Enrolled": [155, 155, 155, 155, 155, 155]
    })

fig2 = px.line(
    engagement,
    x="period",
    y=["Active Students", "Total Enrolled"],
    markers=True
)

fig2.update_traces(line=dict(width=4), marker=dict(size=10))

fig2.update_layout(
    height=420,
    yaxis_title="Students",
    xaxis_title="",
    legend_title_text="",
    yaxis=dict(range=[0, 170]),
    plot_bgcolor="white",
    paper_bgcolor="white"
)

st.plotly_chart(fig2, use_container_width=True)

current_active = engagement["Active Students"].iloc[-1]
total_enrolled = engagement["Total Enrolled"].iloc[-1]

col_a, col_b = st.columns(2)

with col_a:
    st.info(f"**Total Enrolled**  \n# {total_enrolled} students")

with col_b:
    st.info(f"**Currently Active**  \n# {current_active} students")

    
st.subheader("Activity Types")
activity = filtered_df["action"].value_counts().reset_index()
activity.columns = ["action", "count"]
fig3 = px.pie(activity, names="action", values="count")
st.plotly_chart(fig3, use_container_width=True)



# at risk students
st.subheader("At-Risk Students")

student_activity = (
    filtered_df.groupby("userid")
    .agg(
        total_interactions=("eventname", "count"),
        last_activity=("datetime", "max"),
        active_days=("date", "nunique")
    )
    .reset_index()
)

latest_date = filtered_df["datetime"].max()
student_activity["days_inactive"] = (latest_date - student_activity["last_activity"]).dt.days

def risk_level(row):
    if row["days_inactive"] >= 7 or row["total_interactions"] <= 3:
        return "High Risk"
    elif row["days_inactive"] >= 3 or row["total_interactions"] <= 8:
        return "Medium Risk"
    return "Low Risk"

student_activity["risk_level"] = student_activity.apply(risk_level, axis=1)

high_risk = (student_activity["risk_level"] == "High Risk").sum()
medium_risk = (student_activity["risk_level"] == "Medium Risk").sum()
low_risk = (student_activity["risk_level"] == "Low Risk").sum()
total_risk = high_risk + medium_risk
total_students = len(student_activity)
risk_percent = round((total_risk / total_students) * 100, 1) if total_students else 0
avg_inactive = round(student_activity["days_inactive"].mean(), 1) if total_students else 0

st.markdown(f"""


  <div style="display:flex; gap:18px; margin-top:28px;">
    <div style="flex:1; border:1px solid #fecaca; background:#fff1f2; border-radius:16px; padding:20px;">
      <div style="color:#dc2626; font-size:20px;">High<br>Risk</div>
      <div style="font-size:36px; color:#b91c1c; font-weight:700;">{high_risk}</div>
    </div>
    <div style="flex:1; border:1px solid #fed7aa; background:#fff7ed; border-radius:16px; padding:20px;">
      <div style="color:#ea580c; font-size:20px;">Medium<br>Risk</div>
      <div style="font-size:36px; color:#c2410c; font-weight:700;">{medium_risk}</div>
    </div>
    <div style="flex:1; border:1px solid #fde68a; background:#fefce8; border-radius:16px; padding:20px;">
      <div style="color:#ca8a04; font-size:20px;">Low Risk</div>
      <div style="font-size:36px; color:#a16207; font-weight:700;">{low_risk}</div>
    </div>
  </div>

  <div style="background:#f9fafb; border-radius:16px; padding:24px; margin-top:28px;">
    <p style="font-size:20px;"><b>Total at-risk</b> &nbsp;&nbsp; {total_risk} students ({risk_percent}%)</p>
    <p style="font-size:20px;"><b>Trend</b> &nbsp;&nbsp; <span style="color:#dc2626;">↑ prototype trend from last week</span></p>
    <p style="font-size:20px;"><b>Avg. days inactive</b> &nbsp;&nbsp; {avg_inactive} days</p>
  </div>

  <div style="border:1px solid #fde68a; background:#fffbeb; border-radius:16px; padding:20px; margin-top:28px; color:#92400e;">
    <b>Action Required:</b> {high_risk} student(s) have very low interaction or have not accessed LMS recently.
  </div>
</div>
""", unsafe_allow_html=True)

with st.expander("View Student List"):
    st.dataframe(
        student_activity[
            ["userid", "total_interactions", "active_days", "days_inactive", "risk_level"]
        ],
        use_container_width=True
    )

st.subheader("Predictive Engagement Trend")

# Prototype prediction data for client demo
prediction_df = pd.DataFrame({
    "period": ["Week 1", "Week 2", "Week 3", "Week 4", "Week 5", "Week 6", "Week 7", "Week 8", "Week 9", "Week 10"],
    "Actual Active Students": [148, 152, 145, 141, 143, 138, 140, 136, None, None],
    "Predicted Active Students": [None, None, None, None, None, None, 140, 136, 130, 124]
})

fig_pred = px.line(
    prediction_df,
    x="period",
    y=["Actual Active Students", "Predicted Active Students"],
    markers=True
)

fig_pred.update_layout(
    height=420,
    yaxis_title="Active Students",
    xaxis_title="",
    legend_title_text="",
    yaxis=dict(range=[0, 170]),
    plot_bgcolor="white",
    paper_bgcolor="white"
)

fig_pred.update_traces(line=dict(width=4), marker=dict(size=9))

st.plotly_chart(fig_pred, use_container_width=True)

st.subheader("AI Insights")

insights = []

# highest activity unit
top_course = (
    filtered_df.groupby("course_name")
    .size()
    .sort_values(ascending=False)
    .index[0]
)

insights.append(
    f"• {top_course} has the highest activity in the selected view."
)

# at-risk insight
if total_risk > 0:
    insights.append(
        f"• {total_risk} student(s) are currently flagged as potentially at-risk."
    )
else:
    insights.append(
        "• Engagement levels currently appear stable."
    )


insights.append(

    "• Active student engagement may drop from 136 to 124 students over the next 2 weeks."

)

# display box
st.info("\n\n".join(insights))