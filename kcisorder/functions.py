import re
import requests
import traceback
from bs4 import BeautifulSoup
import urllib.parse
from .classes import Meal

base_url = "https://ordering.kcisec.com/ordering/"
login_url = urllib.parse.urljoin(base_url, "login.asp?action=login")
index_url = urllib.parse.urljoin(base_url, "index.asp")
orders_url = urllib.parse.urljoin(base_url, "orders.asp?d=3")
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"

def login(username: str, password: str, request_session: requests.Session):
    headers = {
        "User-Agent": user_agent,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = {"User": username, "Pwd": password}

    try:
        response = request_session.post(login_url, headers=headers, data=payload)
        response.raise_for_status()
        soup = BeautifulSoup(response.text.encode("iso-8859-1").decode("gbk"), "html.parser")
        if len(soup.body) == 2: # ['\n', <script>alert('帐号或密码错误，登录失败！');history.go(-1);</script>]
            return None
        return request_session
    except requests.exceptions.RequestException:
        traceback.print_exc()
        return None


def get_meals(session: requests.Session):
    """Scrapes meal data (lunch & dinner) for each available date."""
    response = get_request(session, index_url, headers={"User-Agent": user_agent})
    if response is None:
        return None

    soup = BeautifulSoup(response.text.encode("iso-8859-1").decode("gbk"), "html.parser")
    side_menu = soup.find("dl", class_="submenu")
    if side_menu is None:
        print("kcisorder: Failed to get menu items!")
        return None

    order_links = side_menu.find_all("a")
    meals_by_date = []

    for order_link in order_links:
        href = order_link.get("href")
        response = get_request(session, index_url + href, headers={"User-Agent": user_agent})
        if response is None:
            continue

        day_soup = BeautifulSoup(response.text.encode("iso-8859-1").decode("gbk"), "html.parser")
        meal_sections = day_soup.find_all("div", class_="col-xs-8 col-xs-offset-4")

        day_meals = {}
        is_lunch = True

        for meal_section in meal_sections:
            meals = []
            cafeterias = meal_section.find_all("div", class_="collapse in")

            for cafeteria_index, cafeteria_div in enumerate(cafeterias, start=1):
                meal_blocks = cafeteria_div.find("div", class_="row", recursive=False).find_all("div", recursive=False)
                previous_meal = None

                for idx, meal_block in enumerate(meal_blocks):
                    # Even index: meal info
                    if idx % 2 == 0:
                        rows = meal_block.find("div", class_="col-xs-6", style="padding-left: 0px").find_all(recursive=False)
                        names = rows[0].find("div", class_="dish-name").find_all("h5")
                        remaining = rows[1].find("strong").text

                        meal_id = None
                        add_to_cart = rows[2].find("a")
                        if add_to_cart:
                            match = re.search(r"buy_car\.asp\?id=(\d+)", add_to_cart.get("href"))
                            if match:
                                meal_id = match.group(1)

                        # previous_meal = {
                        #     "chinese_name": names[0].text.strip(),
                        #     "english_name": names[1].text.strip(),
                        #     "remaining": remaining.strip(),
                        #     "id": meal_id,
                        #     "cafeteria": cafeteria_index,
                        #     "type": "lunch" if is_lunch else "dinner",
                        # }
                        previous_meal = Meal(meal_id, names[1].text.strip(), names[0].text.strip(), int(remaining.strip()), cafeteria_index, "lunch" if is_lunch else "dinner")

                    # Odd index: meal description
                    else:
                        if previous_meal:
                            desc_div = meal_block.find("div", class_="col-xs-12")
                            description = None
                            if desc_div:
                                match = re.search(r"</h4>(.*?)$", desc_div.decode_contents(), re.DOTALL)
                                if match:
                                    description = match.group(1).strip().replace("<br/>", "\n")
                            previous_meal.description = description
                            meals.append(previous_meal)

            day_meals["lunch" if is_lunch else "dinner"] = meals
            is_lunch = False

        meals_by_date.append(day_meals)

    return meals_by_date


def add_to_cart(meal_id: str, request_session: requests.Session):
    # whoever named cart as "buy_car" is a genius :trumbsup::trumbsup::trumbsup:
    get_request(
        request_session,
        base_url + f"buy_car.asp?id={meal_id}",
        headers={"User-Agent": user_agent},
    )

def get_meals_ordered(request_session: requests.Session):
    orders_page = get_request(request_session, orders_url)

    soup = BeautifulSoup(
        orders_page.text.encode("iso-8859-1").decode("gbk"), "html.parser"
    )
    buttons = soup.findAll("input", value="delete", type="submit")

    ids = []
    for button in buttons:
        data_target = button.get("data-target")
        match_result = re.search(
            "\\d+$",
            data_target
        ).group(0)
        ids.append(match_result)

    return ids

def delete_meal_ordered(request_session: requests.Session, meal_id):
    get_request(request_session, f"{orders_url}&did={meal_id}")

def clean_meals_ordered(request_session: requests.Session):
    meals_ordered = get_meals_ordered(request_session)
    if meals_ordered is None:
        return
    for meal_id in meals_ordered:
        delete_meal_ordered(request_session, meal_id)

def submit_order(request_session: requests.Session, meal_list: list[Meal]):
    headers = {
        "User-Agent": user_agent,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = []
    for meal in meal_list:
        payload.append(("reaID", meal.id))

    response = post_request(
        request_session,
        base_url + "orders.asp?action=order_ok",
        headers=headers,
        payload=payload,
    )

    return response

def get_request(request_session: requests.Session, url, headers=None, payload=None):
    try:
        response = request_session.get(url, headers=headers, data=payload)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException:
        traceback.print_exc()
        return None

def post_request(request_session: requests.Session, url, headers=None, payload=None):
    try:
        response = request_session.post(url, headers=headers, data=payload)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException:
        traceback.print_exc()
        return None
