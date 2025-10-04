import re
import kcisorder
import requests
import json
from datetime import datetime
import yaml
import os
import random
from requests.adapters import HTTPAdapter, Retry

print("KCIS auto order script")
print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
print()

print("Loading config file")
if not os.path.exists("config.yaml"):
    print(
        "Config file not found. Check docs to create a config file"
    )
    exit(1)

config = None
with open("config.yaml") as f:
    try:
        config = yaml.load(f, Loader=yaml.SafeLoader)
    except yaml.YAMLError as exc:
        print("Cannot read config.yaml, check ur syntax!")
        print(exc)

if config is None:
    print("WARNING: config file is empty!")
    exit(0)

target_list = config.get("orders")
if target_list is None:
    print("WARNING: no orders found in config file")
    exit(0)

print(f"{len(target_list)} orders loaded")

crawl_every = config.get("crawl_every")
if crawl_every is None:
    crawl_every = True

if not crawl_every:
    print(
        "WARNING: crawl_every is set to false, all orders will match list crawled from the first order"
    )

# preprocess follows
by_name = {t["name"]: t for t in target_list if t.get("name") is not None}
by_id   = {t["id"]: t for t in target_list if t.get("id") is not None}
for target in target_list:
    target.setdefault("lunch", [])
    target.setdefault("dinner", [])
    for follow_id in target.get("follow", []):
        if (followed := by_id.get(follow_id)):
            target["lunch"] += followed.get("lunch", [])
            target["dinner"] += followed.get("dinner", [])
    for follow_name in target.get("follow_by_name", []):
        if (followed := by_name.get(follow_name)):
            target["lunch"] += followed.get("lunch", [])
            target["dinner"] += followed.get("dinner", [])

clean_existing = config.get("clean_existing")
if clean_existing is None:
    clean_existing = False
if clean_existing:
    print(
        "WARNING: clean_existing is set to true, meals that are already been ordered will be cleaned"
    )

def check_remaining(meal):
    return meal.id is None or meal.remaining == 0

def does_hit_rule(rule, meal):
    if not (
        rule.get("cafeteria") is None
        or rule.get("cafeteria") == meal.cafeteria
    ):
        return False
    # print(meal_description)
    # print()

    matches = rule.get("match")

    if matches is None:
        return True

    for regex in matches:
        if regex is None:
            continue
        regex_pattern = regex.get("regex")

        if regex_pattern is None:
            return True
        pattern = re.compile(regex_pattern)
        search_result = pattern.search(meal.get_description())
        if regex.get("not") is not None and regex.get("not"):
            if search_result:
                return False
            continue
        if not search_result:
            return False
    return True

def match_meal(rule, meals, print_hit=True) -> kcisorder.Meal | None:
    if rule.get("random") is not None and rule.get("random"):
        if rule.get('match') is None:
            hit = meals
        else:
            hit = []
            for single_meal in meals:
                if does_hit_rule(rule, single_meal) and check_remaining(single_meal):
                    hit.append(single_meal)
            if len(hit) == 0:
                return
        random_hit = hit[random.randint(0, len(hit) - 1)]
        if print_hit:
            print(
                f"Hit {random_hit} (random: {rule})"
            )
        return random_hit
    for meal in meals:
        if does_hit_rule(rule, meal):
            if check_remaining(meal):
                print(
                    f"Hit {meal} (match: {rule}) but it is sold out"
                )
                continue
            if print_hit:
                print(
                    f"Hit {meal} (match: {rule})"
                )
            return meal

meal_list = None
retries_adapter = HTTPAdapter(max_retries=Retry(total=config.get('retries', 5), backoff_factor=0.1, status_forcelist=[ 500, 502, 503, 504 ]))

print()
for target in target_list:
    if 'dinner' not in target and 'lunch' not in target:
        print(f"WARNING: no rule specified for order {target.get('name', '[unnamed]')}")
        continue

    if 'id' not in target or 'password' not in target:
        continue

    print(f"Processing order for {target.get('name', '[unnamed]')} - {target.get('id', '')}")
    session = requests.session()
    session.mount('http://', retries_adapter)
    session.mount('https://', retries_adapter)
    if kcisorder.login(target.get("id", ''), target.get("password", ''), session) != None:
        print("Logged in")
    else:
        print("Failed to log in! pls check your login credentials. skipping")
        continue

    if crawl_every or meal_list is None:
        print("Getting meals")
        meal_list = kcisorder.get_meals(session)
        # print(meal_list)

    if meal_list is None:
        print(
            "Failed to get meal list. pls check your internet! skipping"
        )
        continue

    # print(json.dumps(meals))
    print("Matching meals")
    meals_to_order = []
    for current_day in meal_list:  # current_day structure: {"lunch": [], "dinner": []}
        for key, meals in current_day.items():
            if meals is None or len(meals) == 0:
                continue
            flag_done_finding_meal = False
            for rule in target.get(key, []):
                meal_hit = match_meal(rule, meals)
                if meal_hit is not None:
                    flag_done_finding_meal = True
                    meals_to_order.append(meal_hit)
                    meal_hit.remaining -= 1 # for crawl_every = false
                    break
            if not flag_done_finding_meal:
                print("No match, skipping")

    if target.get("clean_existing", False) or clean_existing:
        print("Cleaning existing orders")
        kcisorder.clean_meals_ordered(session)

    print("Submitting")

    kcisorder.submit_order(session, meals_to_order)

    print()

print("All done")
