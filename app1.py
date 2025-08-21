import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

# ------------------------------
# BMR & TDEE Calculation
# ------------------------------
def calculate_bmr_tdee(weight, height, age, gender, activity_level, goal):
    if gender == "Male":
        bmr = 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
    else:
        bmr = 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)

    activity_factors = {
        "Sedentary": 1.2,
        "Lightly active": 1.375,
        "Moderately active": 1.55,
        "Very active": 1.725
    }
    tdee = bmr * activity_factors[activity_level]

    if goal == "Weight Loss":
        target_calories = tdee - 500
    elif goal == "Weight Gain":
        target_calories = tdee + 500
    else:
        target_calories = tdee

    return round(bmr), round(tdee), round(target_calories)

# ------------------------------
# Meal Database (Hardcoded)
# ------------------------------
meal_plans = {
    "North": {
        "Veg": [
            {
                "Breakfast": [("Oats with skim milk", 250), ("Apple", 80)],
                "Lunch": [("Dal with brown rice", 350), ("Salad", 50)],
                "Dinner": [("Paneer curry", 300), ("Roti (2 pcs)", 200)]
            },
            {
                "Breakfast": [("Upma", 250), ("Banana", 100)],
                "Lunch": [("Rajma with quinoa", 400), ("Cucumber salad", 50)],
                "Dinner": [("Mixed veg curry", 250), ("Roti (2 pcs)", 200)]
            },
            {
                "Breakfast": [("Vegetable poha", 220), ("Orange", 60)],
                "Lunch": [("Chole with brown rice", 400), ("Salad", 50)],
                "Dinner": [("Palak paneer", 300), ("Roti (2 pcs)", 200)]
            }
        ],
        "Non-Veg": [
            {
                "Breakfast": [("Boiled eggs (2)", 140), ("Brown bread toast", 160)],
                "Lunch": [("Chicken curry", 350), ("Brown rice", 200)],
                "Dinner": [("Grilled fish", 300), ("Steamed veggies", 80)]
            },
            {
                "Breakfast": [("Omelette", 180), ("Whole wheat toast", 140)],
                "Lunch": [("Chicken tikka", 300), ("Roti (2 pcs)", 200)],
                "Dinner": [("Egg curry", 250), ("Brown rice", 200)]
            },
            {
                "Breakfast": [("Scrambled eggs", 200), ("Banana", 100)],
                "Lunch": [("Grilled chicken", 350), ("Quinoa", 180)],
                "Dinner": [("Fish curry", 320), ("Steamed veggies", 80)]
            }
        ]
    },
    "South": {
        "Veg": [
            {
                "Breakfast": [("Idli (3 pcs)", 180), ("Sambar", 120)],
                "Lunch": [("Sambar with brown rice", 350), ("Cabbage poriyal", 100)],
                "Dinner": [("Vegetable upma", 250), ("Chutney", 50)]
            },
            {
                "Breakfast": [("Dosa", 150), ("Coconut chutney", 80)],
                "Lunch": [("Rasam with brown rice", 300), ("Beans poriyal", 100)],
                "Dinner": [("Curd rice (low-fat)", 300), ("Pickle", 20)]
            },
            {
                "Breakfast": [("Upma", 250), ("Papaya", 60)],
                "Lunch": [("Vegetable kurma", 280), ("Parotta (1 pc)", 200)],
                "Dinner": [("Tomato rice", 320), ("Salad", 50)]
            }
        ],
        "Non-Veg": [
            {
                "Breakfast": [("Egg dosa", 200), ("Chutney", 80)],
                "Lunch": [("Chicken curry", 350), ("Brown rice", 200)],
                "Dinner": [("Fish fry", 300), ("Rasam", 50)]
            },
            {
                "Breakfast": [("Omelette", 180), ("Idli (2 pcs)", 120)],
                "Lunch": [("Mutton curry", 400), ("Parotta (1 pc)", 200)],
                "Dinner": [("Grilled chicken", 350), ("Veg stir fry", 80)]
            },
            {
                "Breakfast": [("Boiled eggs (2)", 140), ("Upma", 200)],
                "Lunch": [("Fish curry", 350), ("Brown rice", 200)],
                "Dinner": [("Chicken stew", 320), ("Appam (1 pc)", 150)]
            }
        ]
    }
}

# ------------------------------
# Adjust Meals for Health Conditions
# ------------------------------
def adjust_for_health(meal, condition):
    adjustments = {
        "Diabetes": lambda food: (food[0], food[1] - 10 if "rice" in food[0].lower() else food[1]),
        "BP": lambda food: (food[0] + " (low salt)" if "curry" in food[0].lower() else food[0], food[1]),
        "Cholesterol": lambda food: (food[0], food[1] - 20 if "fried" in food[0].lower() else food[1])
    }
    return [adjustments[condition](item) for item in meal] if condition in adjustments else meal

# ------------------------------
# Generate Meal Plan
# ------------------------------
def generate_plan(region, diet, condition):
    plans = meal_plans[region][diet]
    adjusted_plans = []
    for day in plans:
        day_adjusted = {
            meal: adjust_for_health(items, condition) for meal, items in day.items()
        }
        adjusted_plans.append(day_adjusted)
    return adjusted_plans

# ------------------------------
# PDF Export
# ------------------------------
def create_pdf(meal_plan):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    y = 750
    day_num = 1
    for day in meal_plan:
        c.drawString(30, y, f"Day {day_num} Plan:")
        y -= 20
        for meal, items in day.items():
            c.drawString(50, y, f"{meal}:")
            y -= 20
            for food, cal in items:
                c.drawString(70, y, f"- {food} ({cal} kcal)")
                y -= 15
        y -= 30
        day_num += 1
    c.save()
    buffer.seek(0)
    return buffer

# ------------------------------
# Streamlit UI
# ------------------------------
st.title("BMR, TDEE & Meal Planner 🍽️")

with st.form("user_input"):
    age = st.number_input("Age", 18, 100, 25)
    gender = st.selectbox("Gender", ["Male", "Female"])
    height = st.number_input("Height (cm)", 100, 250, 170)
    weight = st.number_input("Weight (kg)", 30, 200, 70)
    activity_level = st.selectbox("Activity Level", ["Sedentary", "Lightly active", "Moderately active", "Very active"])
    goal = st.selectbox("Goal", ["Maintain Weight", "Weight Loss", "Weight Gain"])
    region = st.selectbox("Region", ["North", "South"])
    diet = st.selectbox("Diet Preference", ["Veg", "Non-Veg"])
    condition = st.selectbox("Health Condition", ["None", "Diabetes", "BP", "Cholesterol"])
    submitted = st.form_submit_button("Generate Plan")

if submitted:
    bmr, tdee, target_cal = calculate_bmr_tdee(weight, height, age, gender, activity_level, goal)
    st.subheader(f"Your BMR: {bmr} kcal/day")
    st.subheader(f"Your TDEE: {tdee} kcal/day")
    st.subheader(f"Target Calories: {target_cal} kcal/day")

    meal_plan = generate_plan(region, diet, condition)
    df_list = []
    for i, day in enumerate(meal_plan, 1):
        st.write(f"### Day {i}")
        for meal, items in day.items():
            st.write(f"**{meal}:**")
            for food, cal in items:
                st.write(f"- {food} ({cal} kcal)")
                df_list.append({"Day": i, "Meal": meal, "Food": food, "Calories": cal})

    df = pd.DataFrame(df_list)

    # CSV Download
    csv = df.to_csv(index=False).encode()
    st.download_button("Download as CSV", csv, "meal_plan.csv", "text/csv")

    # PDF Download
    pdf_buffer = create_pdf(meal_plan)
    st.download_button("Download as PDF", pdf_buffer, "meal_plan.pdf", "application/pdf")
