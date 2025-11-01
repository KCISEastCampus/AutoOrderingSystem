from os import error
import re
import requests
from bs4 import BeautifulSoup, Tag
import urllib.parse
from .classes import *

base_url = "https://ordering.kcisec.com/ordering/"
login_url = urllib.parse.urljoin(base_url, "login.asp?action=login")
index_url = urllib.parse.urljoin(base_url, "index.asp")
orders_url = urllib.parse.urljoin(base_url, "orders.asp?d=3")
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"

def login(username: str, password: str, request_session: requests.Session, verify=True):
    headers = {
        "User-Agent": user_agent,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = {"User": username, "Pwd": password}

    try:
        response = request_session.post(login_url, headers=headers, data=payload, verify=verify)
        response.raise_for_status()
        soup = BeautifulSoup(response.text.encode("iso-8859-1").decode("gbk"), "html.parser")
        if soup.body and len(soup.body) == 2: # ['\n', <script>alert('帐号或密码错误，登录失败！');history.go(-1);</script>]
            alert_script = list(soup.body.children)[1]
            if error_info := re.match(r"alert\s*\(\s*['\"](.*?)['\"]\s*\)", alert_script.string or ""):
                raise LoginError(error_info.group(1))
            raise LoginError("unknown error")
        return request_session
    except requests.exceptions.RequestException as e:
        # traceback.print_exc()
        raise e

def add_to_cart(meal_id: str, request_session: requests.Session, verify=True):
    # whoever named cart as "buy_car" is a genius :trumbsup::trumbsup::trumbsup:
    get_request(
        request_session,
        base_url + f"buy_car.asp?id={meal_id}",
        headers={"User-Agent": user_agent},
        verify=verify
    )

def get_meals_ordered(request_session: requests.Session, verify=True):
    orders_page = get_request(request_session, orders_url, verify=verify)

    soup = BeautifulSoup(
        orders_page.text.encode("iso-8859-1").decode("gbk"), "html.parser"
    )

    ids = [
        m.group(0)
        for b in soup.find_all("input", value="delete", type="submit")
        if isinstance(b, Tag)
        and isinstance((dt := b.get("data-target")), str)
        and (m := re.search(r"\d+$", dt))
    ]

    return ids

def delete_meal_ordered(request_session: requests.Session, meal_id, verify=True):
    get_request(request_session, f"{orders_url}&did={meal_id}", verify=verify)

def clean_meals_ordered(request_session: requests.Session, verify=True):
    meals_ordered = get_meals_ordered(request_session, verify=verify)
    if meals_ordered is None:
        return
    for meal_id in meals_ordered:
        delete_meal_ordered(request_session, meal_id, verify=verify)

def submit_order(request_session: requests.Session, meal_list: list[Meal], verify=True):
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
        verify=verify
    )

    return response

def get_request(request_session: requests.Session, url, headers=None, payload=None, verify=True):
    response = request_session.get(url, headers=headers, data=payload, verify=verify)
    response.raise_for_status()
    return response

def post_request(request_session: requests.Session, url, headers=None, payload=None, verify=True):
    response = request_session.post(url, headers=headers, data=payload, verify=verify)
    response.raise_for_status()
    return response

def get_meals(session: requests.Session, verify=True):
    """Scrapes meal data (lunch & dinner) for each available date."""
    response = get_request(session, index_url, headers={"User-Agent": user_agent}, verify=verify)

    soup = BeautifulSoup(response.text.encode("iso-8859-1").decode("gbk"), "html.parser")
    side_menu = soup.find("dl", class_="submenu")
    if side_menu is None:
        raise Exception("Cannot load meals")

    order_links = side_menu.find_all("a")
    meals_by_date = []

    for order_link in order_links:
        href = order_link.get("href")
        if not href:
            continue
        response = get_request(session, index_url + href, headers={"User-Agent": user_agent}, verify=verify)
        if not response:
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
