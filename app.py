
import streamlit as st
import pandas as pd
import numpy as np
from helpers import (
    calculate_bmr, get_activity_multiplier, adjust_calories_for_goal,
    filter_meals, pick_week_plan, scale_day_to_target, build_shopping_list
)

st.set_page_config(page_title="Indian Meal Planner (Clean)", layout="wide")

st.title("🍛 Indian Meal Planner — Clean (No Images)")

with st.sidebar:
    st.header("Your details")
    age = st.number_input("Age", 10, 100, 30)
    gender = st.selectbox("Gender", ["Male","Female"])
    weight = st.number_input("Weight (kg)", 30.0, 200.0, 70.0)
    height = st.number_input("Height (cm)", 120.0, 220.0, 170.0)
    activity = st.selectbox("Activity", ["Sedentary","Light","Moderate","Active","Very active"], index=2)
    goal = st.selectbox("Goal", ["Maintain","Loss","Gain"])
    region = st.selectbox("Region", ["North","South","East","West"])
    diet = st.selectbox("Diet", ["Veg","Non-Veg","Jain","Vegan"])
    conds = st.multiselect("Health conditions", ["Diabetes","High BP","High Cholesterol"])
    days_sel = st.selectbox("Plan length", ["7-day","3-day"])
    go = st.button("Generate plan")

# Load meals
df = pd.read_csv("meals.csv")

# Compute BMR/TDEE/Target
bmr = calculate_bmr(weight, height, age, gender)
tdee = bmr * get_activity_multiplier(activity)
target = adjust_calories_for_goal(tdee, goal)
bmi = weight / ((height/100)**2)

col1,col2,col3,col4 = st.columns(4)
col1.metric("BMR", f"{bmr:.0f} kcal/day")
col2.metric("TDEE", f"{tdee:.0f} kcal/day")
col3.metric("Target", f"{target:.0f} kcal/day")
col4.metric("BMI", f"{bmi:.1f}")

if go:
    conditions = {"diabetes":"Diabetes" in conds, "bp":"High BP" in conds, "cholesterol":"High Cholesterol" in conds}
    filt = filter_meals(df, region, diet, conditions)
    if filt.empty:
        st.error("No meals match your filters. Try relaxing health conditions or change region/diet.")
    else:
        week_raw = pick_week_plan(filt, target)
        plan_len = 7 if days_sel=="7-day" else 3
        week_raw = week_raw[:plan_len]

        final_days = []
        rows_out = []
        totals = []
        for i, day in enumerate(week_raw, start=1):
            scaled, total = scale_day_to_target(day, target)
            final_days.append(scaled)
            totals.append(total)
            st.subheader(f"Day {i} — {total:.0f} kcal")
            day_df = pd.DataFrame([
                {"Meal":"Breakfast", **scaled["Breakfast"]},
                {"Meal":"Lunch", **scaled["Lunch"]},
                {"Meal":"Dinner", **scaled["Dinner"]},
                {"Meal":"Snack", **scaled["Snack"]},
            ])
            st.dataframe(day_df, use_container_width=True)
            for r in day_df.to_dict("records"):
                rows_out.append({"Day":i, **r})

        # Shopping List
        shop = build_shopping_list(final_days)
        st.subheader("Shopping list (approx)")
        st.dataframe(pd.DataFrame(shop, columns=["Ingredient","ApproxCount"]), use_container_width=True)

        # Export CSV
        out_df = pd.DataFrame(rows_out)
        st.download_button("⬇️ Download Plan CSV", out_df.to_csv(index=False).encode(), "meal_plan.csv", "text/csv")

st.caption("Tip: Upload this repo to GitHub and deploy on Streamlit Community Cloud for a public link.")
