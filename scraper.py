import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin


def get_book_data(book_url: str) -> dict:
    """
    Собирает информацию о книге со страницы товара на сайте Books to Scrape.

    Выполняется запрос по переданному URL, проверяется успешность ответа.
    С помощью BeautifulSoup и извлекает основные сведения
    о книге, а также все характеристики из таблицы Product Information.
    Если какие-то данные отстутвуют они заменяются дефолтными значениями

    Args:
        book_url (str): Прямая ссылка на страницу конкретной книги.

    Returns:
        dict: Словарь с данными о книге, включающий ключи:
            - 'title' (str): Название книги.
            - 'price' (str): Цена книги с символом валюты.
            - 'rating' (int): Рейтинг книги (0 - если не найден).
            - 'availability' (str): Информация о наличии и количестве экземпляров.
            - 'description' (str): Текстовое описание книги.
            - 'product_information' (dict): Словарь характеристик из таблицы
              Product Information (UPC, Product Type, Price, Tax, Availability,
              Number of reviews).
            Если запрос не удался, возвращается пустой словарь.
    """

    # НАЧАЛО ВАШЕГО РЕШЕНИЯ
    try:
        response = requests.get(book_url, timeout=20)
    except requests.RequestException as e:
        print(f"Не удалось загрузить книгу {book_url}: {e}")
        return {}

    # Проверка статуса запроса
    if response.status_code != 200:
        print(f"Request error: {response.status_code}")
        return {}

    soup = BeautifulSoup(response.content, "html.parser")

    # Название книги
    product_main = soup.find("div", class_="product_main")
    title_tag = product_main.find("h1") if product_main else None
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Цена
    price_tag = soup.find("p", class_="price_color")
    price = price_tag.get_text(strip=True) if price_tag else ""

    # Рейтинг (хранится во втором классе тега <p class="star-rating Three">)
    rating_tag = soup.find("p", class_="star-rating")
    rating_classes = rating_tag.get("class", []) if rating_tag else []
    rating_name = rating_classes[1] if len(rating_classes) > 1 else "Unknown"
    rating_dict = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
    rating = rating_dict.get(rating_name, 0)

    # Наличие (количество в наличии)
    availability_tag = soup.find("p", class_="instock availability")
    availability = availability_tag.get_text(strip=True) if availability_tag else ""

    # Описание книги
    description_header = soup.find("div", id="product_description")
    if description_header:
        description_tag = description_header.find_next_sibling("p")
        description = description_tag.get_text(strip=True) if description_tag else ""
    else:
        description = ""

    # Дополнительные характеристики из таблицы Product Information
    product_info = {}
    info_table = soup.find("table", class_="table table-striped")
    if info_table:
        for row in info_table.find_all("tr"):
            header_cell = row.find("th")
            value_cell = row.find("td")
            if header_cell and value_cell:
                key = header_cell.get_text(strip=True)
                value = value_cell.get_text(strip=True)
                product_info[key] = value

    return {
        "title": title,
        "price": price,
        "rating": rating,
        "availability": availability,
        "description": description,
        "product_information": product_info,
    }
    # КОНЕЦ ВАШЕГО РЕШЕНИЯ


def scrape_books(is_save: bool = False):
    """
    Сбор информацию обо всех книгах из каталога Books to Scrape.

    Проходим по всем страницам каталога и извлекаем ссылки на книг.
    С помощью функции get_book_data извлекаем данные о книги.
    При необходимости сохраняет результат в файл.

    Args:
        is_save (bool): Флаг сохранения результата. Если True данные записываются в файл 'books_data.txt' в формате JSON.
        По умолчанию значение False.

    Returns:
        list: Список с информацией о каждой книге.
    """

    # НАЧАЛО ВАШЕГО РЕШЕНИЯ
    base_url = "http://books.toscrape.com/catalogue/"
    books = []
    page_number = 1

    while True:
        # URL текущей страницы каталога
        page_url = f"{base_url}page-{page_number}.html"

        try:
            response = requests.get(page_url, timeout=10)
        except requests.RequestException as e:
            print(f"Ошибка соединения на странице {page_number}: {e}")
            break

        # Если страницы не существует (конец каталога), штатно выходим
        if response.status_code == 404:
            print("Каталог полностью пройден.")
            break

        if response.status_code != 200:
            print(f"Request error: {response.status_code}")
            break

        soup = BeautifulSoup(response.content, "html.parser")
        # Теги ссылок на страницы всех книг на текущей странице
        book_links = soup.select("article.product_pod h3 a")

        # Проходим по каждой ссылке и собираем данные о книге
        for link in book_links:
            href = link.get("href")
            if not href:
                continue

            book_url = urljoin(base_url, href)
            book_data = get_book_data(book_url)

            if book_data:
                books.append(book_data)

        print(f"Обработана страница {page_number}")

        # next_page = soup.find("li", class_="next")
        # if not next_page:
        #     break

        page_number += 1

    # Сохраняем собранный список книг в текстовый файл, если необходимо
    if is_save:
        with open("books_data.txt", "w", encoding="utf-8") as file:
            json.dump(books, file, ensure_ascii=False, indent=4)

    return books
    # КОНЕЦ ВАШЕГО РЕШЕНИЯ
