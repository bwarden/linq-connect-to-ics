#!/usr/bin/env python3

import argparse
import json
from datetime import datetime, timezone
import os
import textwrap

def get_meal_times(meal_name):
    """Returns start and end time strings for a given meal."""
    times = {
        "Breakfast": ("080000", "100000"),
        "Lunch": ("110000", "130000"),
        "Snack": ("140000", "160000"),
    }
    return times.get(meal_name, (None, None))

def format_description(menu_meals):
    """
    Formats the list of food items for the event description,
    ordering by Daily Special first and Milk last.
    """
    specials = []
    milk = []
    other = []

    for meal in menu_meals:
        meal_name = meal.get("MenuMealName", "")
        recipes = [
            recipe["RecipeName"]
            for category in meal.get("RecipeCategories", [])
            for recipe in category.get("Recipes", [])
        ]

        if "Daily Special" in meal_name:
            specials.extend(recipes)
        elif "Milk" in meal_name:
            milk.extend(recipes)
        else:
            # Group other items by their MenuMealName
            if recipes:
                other.append(f"== {meal_name} ==")
                other.extend(f"- {r}" for r in recipes)

    description_parts = []
    if specials:
        description_parts.append("== Daily Special ==")
        description_parts.extend(f"- {s}" for s in specials)

    if other:
        if description_parts:
            description_parts.append("\\n") # Add a newline for spacing
        description_parts.extend(other)

    if milk:
        if description_parts:
            description_parts.append("\\n") # Add a newline for spacing
        description_parts.append("== Milk ==")
        description_parts.extend(f"- {m}" for m in milk)

    # textwrap.fill is used for proper folding in ICS
    return "\\n".join(textwrap.fill(line, 72) for line in description_parts)

def create_ics_event(uid, dtstamp, start_time, end_time, summary, description):
    """Creates a single VEVENT string."""
    return (
        "BEGIN:VEVENT\n"
        f"UID:{uid}\n"
        f"DTSTAMP:{dtstamp}\n"
        f"DTSTART:{start_time}\n"
        f"DTEND:{end_time}\n"
        f"SUMMARY:{summary}\n"
        f"DESCRIPTION:{description}\n"
        "END:VEVENT\n"
    )

def process_json_file(filepath):
    """Reads a JSON file and returns its content as an ICS string."""
    print(f"Processing {filepath}...")
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error reading or parsing {filepath}: {e}")
        return None

    ics_events = []
    dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    for session in data.get("FamilyMenuSessions", []):
        serving_session = session.get("ServingSession")
        start_hhmmss, end_hhmmss = get_meal_times(serving_session)

        if not start_hhmmss:
            continue

        for plan in session.get("MenuPlans", []):
            for day in plan.get("Days", []):
                date_str = day.get("Date")
                try:
                    # Handles M/D/YYYY format
                    date_obj = datetime.strptime(date_str, "%m/%d/%Y")
                    date_yyyymmdd = date_obj.strftime("%Y%m%d")
                except (ValueError, TypeError):
                    print(f"Skipping invalid date: {date_str}")
                    continue

                start_time = f"{date_yyyymmdd}T{start_hhmmss}"
                end_time = f"{date_yyyymmdd}T{end_hhmmss}"
                summary = serving_session
                description = format_description(day.get("MenuMeals", []))
                
                # Create a unique ID for the event
                uid = f"{date_yyyymmdd}-{serving_session}-{plan.get('MenuPlanId', '')}@{os.path.basename(filepath)}"

                ics_events.append(create_ics_event(uid, dtstamp, start_time, end_time, summary, description))

    if not ics_events:
        return None

    return (
        "BEGIN:VCALENDAR\n"
        "VERSION:2.0\n"
        "PRODID:-//GeminiCodeAssist//LINQ to ICS//EN\n"
        + "".join(ics_events) +
        "END:VCALENDAR\n"
    )

def main():
    parser = argparse.ArgumentParser(description="Convert school meal JSON files to ICS calendar files.")
    parser.add_argument("json_files", nargs='+', help="One or more JSON files to process.")
    args = parser.parse_args()

    for json_file in args.json_files:
        ics_content = process_json_file(json_file)
        if ics_content:
            basename = os.path.splitext(os.path.basename(json_file))[0]
            ics_filename = f"{basename}.ics"
            with open(ics_filename, 'w') as f:
                f.write(ics_content)
            print(f"Successfully created {ics_filename}")

if __name__ == "__main__":
    main()