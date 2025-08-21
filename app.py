import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from helpers import (
    calculate_bmr, get_activity_multiplier, adjust_calories_for_goal,
    filter_meals, scale_day_to_target
)

st.set_page_config(page_title="Indian Meal Planner", layout="wide")
st.title("🍛 Indian Meal Planner")

# =========================
# Shared helpers (Diet page)
# =========================
def protein_target_g(weight_kg: float, goal: str) -> float:
    g = goal.lower()
    if g == "loss":   return round(2.0 * weight_kg, 1)
    if g == "gain":   return round(2.2 * weight_kg, 1)
    return round(1.8 * weight_kg, 1)

def fat_target_g(target_kcal: float) -> float:
    return round((target_kcal * 0.27) / 9.0, 1)

def bmi_category(bmi: float) -> str:
    if bmi < 18.5: return "Underweight"
    if bmi < 25:   return "Normal"
    if bmi < 30:   return "Overweight"
    return "Obese"

def healthy_weight_range_kg(height_cm: float):
    h_m = height_cm / 100.0
    lo = 18.5 * (h_m ** 2)
    hi = 24.9 * (h_m ** 2)
    return (round(lo,1), round(hi,1))

def recommended_weight_kg(current_kg: float, height_cm: float, goal: str):
    lo, hi = healthy_weight_range_kg(height_cm)
    if goal.lower() == "loss":
        return min(current_kg, hi)
    if goal.lower() == "gain":
        return max(current_kg, lo)
    if current_kg < lo: return lo
    if current_kg > hi: return hi
    return current_kg

def portion_suggestion(dish_name: str) -> str:
    n = dish_name.lower()
    if "paratha" in n: return "2 small parathas (~50–60 g dough each) + 150 g side"
    if "roti" in n or "chapati" in n: return "2 small rotis/chapatis (~45–50 g flour each)"
    if "dosa" in n:   return "2 medium dosas + 150–200 g sambar"
    if "idli" in n:   return "3 small idlis + 150–200 g sambar"
    if "appam" in n:  return "2 appams + 150–200 g stew"
    if any(k in n for k in ["rice","pulao","biryani","khichdi","khichuri"]):
        return "180–220 g cooked rice/grain + 200 g curry/dal"
    if any(k in n for k in ["dal","curry","stew","sambar","rasam","kootu","kurma","pappu"]):
        return "200 g dal/curry + 2 small rotis or 150 g cooked rice"
    if "egg" in n:    return "2–3 eggs + 1 small roti or 1 toast"
    if "mutton" in n: return "100–120 g cooked mutton + 1 roti or 120 g rice"
    if "fish" in n or "prawn" in n: return "120 g fish/prawn + 150 g rice or 2 rotis"
    if "chicken" in n: return "120 g cooked chicken + 150 g carb (2 rotis / 150 g rice)"
    if "paneer" in n:  return "100 g paneer + 2 small rotis or 150 g rice"
    if "tofu" in n or "soya" in n or "soy" in n:
        return "120 g tofu/soya + 2 small rotis or 150 g rice"
    if any(k in n for k in ["oats","dalia","upma","poha","pongal","handvo","thepla","besan","chilla","thalipeeth"]):
        return "1 bowl (~250–300 g cooked/served)"
    if "roasted chana" in n: return "30 g"
    if "peanut" in n:        return "20–25 g"
    if "buttermilk" in n:    return "250 ml"
    if "yogurt" in n or "curd" in n or "parfait" in n: return "150–200 g"
    if "shake" in n or "whey" in n: return "1 scoop (~25 g protein) in water/milk"
    return "1 serving (estimate: 200–300 g)"

def water_target_ml(weight_kg: float, activity_level: str) -> int:
    base = weight_kg * 30
    bump = 300 if activity_level in ("Active","Very active") else 0
    return int(round(base + bump))

def sleep_reco_hours(age: int) -> str:
    if age < 14: return "9–11 h"
    if age < 18: return "8–10 h"
    if age < 65: return "7–9 h"
    return "7–8 h"

METS = {"Brisk walk": 4.3, "Jogging": 7.0, "Cycling (moderate)": 6.0}
def minutes_for_burn(target_kcal: float, weight_kg: float, met: float) -> int:
    if target_kcal <= 0: return 0
    kcal_per_min = met * 3.5 * weight_kg / 200.0
    mins = int(np.ceil(target_kcal / max(kcal_per_min, 1e-6)))
    return int(np.ceil(mins/5)*5)

# =========================
# Mode switch
# =========================
mode = st.sidebar.radio("Mode", ["Diet Plan", "Workout Plan"], index=0)

# ======================================================
# ===============  MODE 1: DIET PLAN  ==================
# ======================================================
if mode == "Diet Plan":
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
        plan_len = st.selectbox("Plan length", ["7-day","3-day"])
        if_days = st.multiselect("Intermittent Fasting (16:8): IF day(s) to skip breakfast", [1,2,3,4,5,6,7], default=[])
        btn_generate = st.button("Generate / Refresh plan")

    df = pd.read_csv("meals.csv")

    bmr = calculate_bmr(weight, height, age, gender)
    tdee = bmr * get_activity_multiplier(activity)
    target = adjust_calories_for_goal(tdee, goal)
    bmi = weight / ((height/100)**2)

    lo_wt, hi_wt = healthy_weight_range_kg(height)
    rec_wt = recommended_weight_kg(weight, height, goal)

    wml = water_target_ml(weight, activity)
    water_l = wml / 1000
    glasses = int(np.round(wml / 250))

    col1,col2,col3,col4 = st.columns(4)
    col1.metric("BMR", f"{bmr:.0f} kcal/day")
    col2.metric("TDEE", f"{tdee:.0f} kcal/day")
    col3.metric("Target", f"{target:.0f} kcal/day")
    col4.metric("BMI", f"{bmi:.1f} ({bmi_category(bmi)})")

    st.caption(f"Healthy weight: **{lo_wt}–{hi_wt} kg**. Recommended for your goal: **{rec_wt} kg**.")
    st.info(f"💧 Water: **{wml} ml** (~{water_l:.1f} L ≈ {glasses} glasses) • 😴 Sleep: **{sleep_reco_hours(age)}**")

    ptarget = protein_target_g(weight, goal)
    ftarget = fat_target_g(target)
    st.markdown(f"**Daily Macro Targets** → Protein: **{ptarget} g**, Fat: **{ftarget} g**")

    # Session state for persistent plan & swaps
    def init_state():
        ss = st.session_state
        ss.setdefault("plan_ready", False)
        ss.setdefault("filtered_df", None)
        ss.setdefault("raw_week", None)
        ss.setdefault("N_days", 7)
        ss.setdefault("if_days_set", set())
        ss.setdefault("params_hash", None)
    init_state()

    def hash_params():
        return (age, gender, weight, height, activity, goal, region, diet, tuple(sorted(conds)), plan_len)

    def build_initial_plan(filtered_df: pd.DataFrame, N: int) -> list:
        week = []
        rng = np.random.default_rng(42)
        for day_num in range(1, N+1):
            day_plan = {}
            for meal in ["Breakfast","Lunch","Dinner","Snack"]:
                sub = filtered_df[(filtered_df["MealType"]==meal) & (filtered_df["Day"]==day_num)]
                if sub.empty:
                    sub = filtered_df[filtered_df["MealType"]==meal]
                idx = int(rng.integers(0, len(sub)))
                row = sub.iloc[idx]
                day_plan[meal] = row
            week.append(day_plan)
        return week

    current_hash = hash_params()
    if btn_generate or (not st.session_state.plan_ready) or (st.session_state.params_hash != current_hash):
        conditions = {"diabetes":"Diabetes" in conds, "bp":"High BP" in conds, "cholesterol":"High Cholesterol" in conds}
        filt = filter_meals(df, region, diet, conditions)
        if filt.empty:
            st.error("No meals match your filters. Try relaxing health conditions or change region/diet.")
            st.stop()
        N = 7 if plan_len == "7-day" else 3
        st.session_state.filtered_df = filt.reset_index(drop=True)
        st.session_state.raw_week   = build_initial_plan(st.session_state.filtered_df, N)
        st.session_state.N_days     = N
        st.session_state.if_days_set = set(if_days)
        st.session_state.plan_ready = True
        st.session_state.params_hash = current_hash
    else:
        st.session_state.if_days_set = set(if_days)

    def compute_scaled_day(raw_day: dict, day_index: int, target_kcal: float):
        day_for_scale = {}
        for meal in ["Breakfast","Lunch","Dinner","Snack"]:
            day_for_scale[meal] = raw_day[meal]
        if (day_index+1) in st.session_state.if_days_set:
            B = day_for_scale["Breakfast"].copy()
            B["Dish"] = "Skip (IF 16:8)"
            B["Calories"] = 0; B["Protein"] = 0; B["Carbs"] = 0; B["Fat"] = 0
            day_for_scale["Breakfast"] = B
        scaled, total_kcal = scale_day_to_target(day_for_scale, target_kcal)
        return scaled, total_kcal

    if st.session_state.plan_ready and st.session_state.raw_week:
        rows_out = []
        cal_series = []

        st.markdown("---")
        for i, raw_day in enumerate(st.session_state.raw_week):
            scaled, total_kcal = compute_scaled_day(raw_day, i, target)
            cal_series.append(total_kcal)

            p_day = sum([scaled[m]["p"] for m in ["Breakfast","Lunch","Dinner","Snack"]])
            f_day = sum([scaled[m]["f"] for m in ["Breakfast","Lunch","Dinner","Snack"]])
            c_day = sum([scaled[m]["c"] for m in ["Breakfast","Lunch","Dinner","Snack"]])

            prot_def = max(0.0, round(ptarget - p_day, 1))
            fat_def  = max(0.0, round(ftarget - f_day, 1))
            shakes = int(np.ceil(prot_def / 25.0)) if prot_def > 0 else 0
            shake_g = round(shakes * 25.0, 1)
            shake_kcal = int(shake_g * 4.0) if shakes else 0

            surplus = max(0, total_kcal - target) if goal != "Gain" else 0
            mins_walk   = minutes_for_burn(surplus, weight, METS["Brisk walk"]) if surplus>0 else 0
            mins_jog    = minutes_for_burn(surplus, weight, METS["Jogging"]) if surplus>0 else 0
            mins_cycle  = minutes_for_burn(surplus, weight, METS["Cycling (moderate)"]) if surplus>0 else 0

            tag = " (IF day — breakfast skipped)" if (i+1) in st.session_state.if_days_set else ""
            st.subheader(f"Day {i+1}{tag} — {total_kcal:.0f} kcal")
            if surplus > 0:
                st.caption(f"🔥 Burn surplus ~{surplus:.0f} kcal → {mins_walk} min walk • {mins_jog} min jog • {mins_cycle} min cycle")

            day_rows = []
            for meal_key in ["Breakfast","Lunch","Dinner","Snack"]:
                item = scaled[meal_key]
                portion = portion_suggestion(item["name"])
                row = {
                    "Meal": meal_key,
                    "Dish": item["name"],
                    "Portion": portion,
                    "Calories": item["cal"],
                    "Protein (g)": item["p"],
                    "Carbs (g)": item["c"],
                    "Fat (g)": item["f"],
                }
                day_rows.append(row)
                rows_out.append({"Day": i+1, **row})
            st.dataframe(pd.DataFrame(day_rows), use_container_width=True)

            # Swap controls (no full refresh; shows what changed)
            with st.expander(f"Swap a meal on Day {i+1}"):
                meal_to_swap = st.selectbox(
                    f"Select meal to swap (Day {i+1})",
                    ["Breakfast","Lunch","Dinner","Snack"], key=f"swap_sel_{i}"
                )
                if (i+1) in st.session_state.if_days_set and meal_to_swap == "Breakfast":
                    st.warning("Breakfast is skipped on this IF day. Choose Lunch/Dinner/Snack.")
                else:
                    current_name = st.session_state.raw_week[i][meal_to_swap]["Dish"]
                    st.caption(f"Current: **{current_name}**")
                    alt_df = st.session_state.filtered_df
                    alts = alt_df[(alt_df["MealType"]==meal_to_swap) & (alt_df["Dish"] != current_name)]
                    if alts.empty:
                        st.info("No alternatives available for this meal.")
                    else:
                        alt_names = alts["Dish"].unique().tolist()
                        alt_choice = st.selectbox("Choose alternative", alt_names, key=f"alt_name_{i}")
                        if st.button(f"Swap {meal_to_swap} on Day {i+1}", key=f"swap_btn_{i}"):
                            new_row = alts[alts["Dish"]==alt_choice].iloc[0]
                            old = st.session_state.raw_week[i][meal_to_swap]["Dish"]
                            # update raw plan in-place
                            st.session_state.raw_week[i][meal_to_swap] = new_row
                            st.success(f"✅ Swapped {meal_to_swap} on Day {i+1}: **{old} → {alt_choice}**")

            st.markdown(
                f"- **Totals** → Protein: **{p_day:.1f} g**, Fat: **{f_day:.1f} g**, Carbs: **{c_day:.1f} g**  \n"
                f"- **Targets** → Protein: **{ptarget:.1f} g**, Fat: **{ftarget:.1f} g**"
            )
            if shakes > 0 or fat_def > 0:
                msg = []
                if shakes > 0:
                    msg.append(f"Add **{shakes} scoop(s)** protein (~**{shake_g} g**, **{shake_kcal} kcal**).")
                if fat_def > 0:
                    msg.append(f"Add healthy fats: **{fat_def} g** (~**{int(fat_def*9)} kcal**) — nuts or 1–2 tsp olive/flaxseed oil.")
                st.info(" ".join(msg))
            else:
                st.success("Protein & fat targets met. 🎯")

        # Dashboard + export
        st.markdown("### 📊 Daily Calories")
        st.line_chart(pd.Series(cal_series, name="Calories"))
        out_df = pd.DataFrame(rows_out)
        st.download_button("⬇️ Download Diet Plan (CSV)", out_df.to_csv(index=False).encode(), "diet_plan.csv", "text/csv")

# ======================================================
# ============  MODE 2: WORKOUT PLAN  ==================
# ======================================================
else:
    st.subheader("🏋️ Fitness Exercise Planner")

    # Sidebar config
    with st.sidebar:
        exp_level = st.selectbox("Experience", ["Beginner","Intermediate","Advanced"], index=0)
        split = st.selectbox("Split", ["3-day Push/Pull/Legs", "4-day Upper/Lower", "5-day Bro Split"], index=0)
        base_reps = st.slider("Base reps (adapts by level)", 6, 15, 10)
        base_rest = st.slider("Base rest between sets (sec)", 45, 150, 90)
        include_core = st.checkbox("Include core each day", True)

    # Exercise libraries ("Name","Type")
    PUSH = [
        ("Bench Press","compound"), ("Incline DB Press","compound"),
        ("Overhead Press","compound"), ("Lateral Raises","accessory"),
        ("Push-ups","accessory"), ("Triceps Pushdown","isolation"),
        ("Cable Fly","isolation")
    ]
    PULL = [
        ("Lat Pulldown","compound"), ("Barbell Row","compound"),
        ("Seated Cable Row","accessory"), ("Face Pulls","accessory"),
        ("DB Bicep Curls","isolation"), ("Hammer Curls","isolation"),
        ("Reverse Fly","isolation")
    ]
    LEGS = [
        ("Back Squat","compound"), ("Romanian Deadlift","compound"),
        ("Leg Press","accessory"), ("Walking Lunges","accessory"),
        ("Leg Extension","isolation"), ("Leg Curl","isolation"),
        ("Calf Raises","isolation")
    ]
    UPPER = [
        ("Bench Press","compound"), ("Overhead Press","compound"),
        ("Lat Pulldown","compound"), ("Barbell Row","compound"),
        ("Lateral Raises","accessory"), ("DB Curls","isolation"),
        ("Triceps Pushdown","isolation")
    ]
    LOWER = [
        ("Back Squat","compound"), ("Romanian Deadlift","compound"),
        ("Leg Press","accessory"), ("Leg Curl","isolation"),
        ("Leg Extension","isolation"), ("Calf Raises","isolation")
    ]
    BRO = {
        "Day 1 – Chest":  [("Bench Press","compound"), ("Incline DB Press","compound"), ("Cable Fly","isolation"), ("Push-ups","accessory")],
        "Day 2 – Back":   [("Barbell Row","compound"), ("Lat Pulldown","compound"), ("Seated Cable Row","accessory"), ("Face Pulls","accessory")],
        "Day 3 – Shoulders":[("Overhead Press","compound"), ("Lateral Raises","accessory"), ("Rear Delt Fly","isolation")],
        "Day 4 – Legs":   [("Back Squat","compound"), ("Leg Press","accessory"), ("Leg Curl","isolation"), ("Calf Raises","isolation")],
        "Day 5 – Arms":   [("Barbell Curls","isolation"), ("Triceps Pushdown","isolation"), ("Hammer Curls","isolation"), ("Cable Fly","isolation")],
    }
    CORE = [("Plank (sec)","conditioning"), ("Hanging Knee Raises","conditioning"), ("Cable Woodchop","conditioning")]

    # Experience-level rules
    def level_rules(level:str):
        level = level.lower()
        if level == "beginner":
            return {
                "sets_compound": 3, "sets_accessory": 3, "sets_isolation": 2,
                "reps_compound": (10,12), "reps_other": (12,15),
                "rest_compound": max(60, base_rest-15), "rest_other": max(45, base_rest-30),
                "max_moves": 5, "notes": ""
            }
        if level == "intermediate":
            return {
                "sets_compound": 3, "sets_accessory": 3, "sets_isolation": 3,
                "reps_compound": (8,10), "reps_other": (10,12),
                "rest_compound": max(90, base_rest), "rest_other": max(60, base_rest-15),
                "max_moves": 6, "notes": "Last set near failure (1–2 RIR)."
            }
        # advanced
        return {
            "sets_compound": 4, "sets_accessory": 3, "sets_isolation": 3,
            "reps_compound": (5,8), "reps_other": (8,12),
            "rest_compound": max(120, base_rest+15), "rest_other": max(75, base_rest),
            "max_moves": 7, "notes": "Optional: top set heavy + back-off; use tempo/paused reps."
        }

    rules = level_rules(exp_level)

    def reps_range(is_compound: bool):
        lo, hi = rules["reps_compound"] if is_compound else rules["reps_other"]
        target = int(np.clip(base_reps, lo, hi))
        return f"{target}"

    def sets_for(kind:str):
        if kind=="compound": return rules["sets_compound"]
        if kind=="accessory": return rules["sets_accessory"]
        return rules["sets_isolation"]

    def rest_for(kind:str):
        return rules["rest_compound"] if kind=="compound" else rules["rest_other"]

    def session_table(title, lib, include_core):
        compounds = [e for e in lib if e[1]=="compound"]
        others    = [e for e in lib if e[1]!="compound"]
        plan = (compounds + others)[:rules["max_moves"]]

        rows = []
        for name,kind in plan:
            rows.append({
                "Exercise": name,
                "Sets": sets_for(kind),
                "Reps": reps_range(kind=="compound"),
                "Rest (s)": rest_for(kind),
                "Notes": rules["notes"]
            })
        if include_core:
            c = CORE[:2] if exp_level=="Beginner" else CORE
            for name,_ in c:
                rows.append({
                    "Exercise": name,
                    "Sets": 3 if "sec" not in name else 3,
                    "Reps": "45–60 sec" if "sec" in name else "12–15",
                    "Rest (s)": 60,
                    "Notes": ""
                })
        st.markdown(f"**{title}**")
        st.table(pd.DataFrame(rows))

    # Render split using experience-aware session_table
    if split == "3-day Push/Pull/Legs":
        st.markdown(f"**Plan: 3 days/week — Push / Pull / Legs**  \n*Level:* **{exp_level}**")
        session_table("Day 1 – Push (Chest/Shoulders/Triceps)", PUSH, include_core)
        session_table("Day 2 – Pull (Back/Biceps)", PULL, include_core)
        session_table("Day 3 – Legs (Quads/Hamstrings/Glutes/Calves)", LEGS, include_core)

    elif split == "4-day Upper/Lower":
        st.markdown(f"**Plan: 4 days/week — Upper / Lower (x2)**  \n*Level:* **{exp_level}**")
        session_table("Day 1 – Upper", UPPER, include_core)
        session_table("Day 2 – Lower", LOWER, include_core)
        session_table("Day 3 – Upper (variation)", list(reversed(UPPER)), include_core)
        session_table("Day 4 – Lower (variation)", list(reversed(LOWER)), include_core)

    else:  # 5-day bro split
        st.markdown(f"**Plan: 5 days/week — Body-part split (3–4 sets)**  \n*Level:* **{exp_level}**")
        for day_title, exs in BRO.items():
            session_table(day_title, exs, include_core)

    st.caption("Sets/reps/rest auto-adjust with your level. Progress weekly: add reps or weight while keeping 1–2 RIR.")
