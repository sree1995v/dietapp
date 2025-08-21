
import pandas as pd
import numpy as np

def calculate_bmr(weight, height, age, gender):
    if gender.lower() == "male":
        return 10 * weight + 6.25 * height - 5 * age + 5
    return 10 * weight + 6.25 * height - 5 * age - 161

def get_activity_multiplier(level):
    return {
        "Sedentary": 1.2,
        "Light": 1.375,
        "Moderate": 1.55,
        "Active": 1.725,
        "Very active": 1.9
    }.get(level, 1.2)

def adjust_calories_for_goal(tdee, goal):
    g = goal.lower()
    if g == "loss": return max(1200, tdee - 500)
    if g == "gain": return tdee + 500
    return tdee

def filter_conditions(row, conditions):
    restr = str(row["Tags"]).lower()
    if conditions.get("diabetes") and ("highgi" in restr):  # we avoid explicit 'HighGI'
        return False
    if conditions.get("bp") and ("highsodium" in restr):
        return False
    if conditions.get("cholesterol") and ("highsatfat" in restr):
        return False
    return True

def filter_meals(df, region, diet, conditions):
    sub = df[(df.Region==region) & (df.Diet==diet)].copy()
    sub = sub[sub.apply(lambda r: filter_conditions(r, conditions), axis=1)]
    return sub

def pick_week_plan(filtered_df, target_cal):
    # Build day-wise picks: Breakfast, Lunch, Dinner, Snack per day
    week = []
    for day in range(1,8):
        day_plan = {}
        for meal in ["Breakfast","Lunch","Dinner","Snack"]:
            opts = filtered_df[(filtered_df.Day==day) & (filtered_df.MealType==meal)]
            if opts.empty:
                opts = filtered_df[filtered_df.MealType==meal]
            if opts.empty:
                raise ValueError(f"No options for {meal}")
            row = opts.sample(1, random_state=day).iloc[0]
            day_plan[meal] = row
        week.append(day_plan)
    return week

def scale_day_to_target(day_plan, target_cal):
    # Scale Snack primarily, then Dinner if needed, to hit ±50
    total = sum([day_plan[m]["Calories"] for m in ["Breakfast","Lunch","Dinner","Snack"]])
    diff = target_cal - total
    # Copy rows to dict of dicts
    plan = {}
    for m in ["Breakfast","Lunch","Dinner","Snack"]:
        r = day_plan[m]
        plan[m] = {"name": r["Dish"], "cal": float(r["Calories"]), "p": float(r["Protein"]), "c": float(r["Carbs"]), "f": float(r["Fat"])}
    if abs(diff) <= 50:
        return plan, total
    # scale snack
    s = plan["Snack"]
    if s["cal"] > 0:
        factor = (s["cal"] + diff) / s["cal"]
        factor = max(0.2, factor)  # avoid negative/zero
        for k in ["cal","p","c","f"]:
            s[k] = round(s[k]*factor,1)
        plan["Snack"] = s
    total = plan["Breakfast"]["cal"] + plan["Lunch"]["cal"] + plan["Dinner"]["cal"] + plan["Snack"]["cal"]
    if abs(total - target_cal) > 50:
        # minor adjust dinner
        d = plan["Dinner"]
        if d["cal"] > 0:
            factor = (d["cal"] + (target_cal - total)) / d["cal"]
            factor = max(0.5, factor)
            for k in ["cal","p","c","f"]:
                d[k] = round(d[k]*factor,1)
            plan["Dinner"] = d
        total = plan["Breakfast"]["cal"] + plan["Lunch"]["cal"] + plan["Dinner"]["cal"] + plan["Snack"]["cal"]
    return plan, total

def build_shopping_list(week_plan):
    inv = {}
    for d in week_plan:
        for m in ["Breakfast","Lunch","Dinner","Snack"]:
            name = d[m]["name"]
            key = name.split()[0]
            inv[key] = inv.get(key,0) + 1
    return sorted(inv.items(), key=lambda x: -x[1])
