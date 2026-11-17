import os
import sys
import pytest
import json

# Добавляем корневую папку проекта в пути поиска модулей Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import scraper


@pytest.fixture
def sample_book_html() -> bytes:
    """Структура с эталонной HTML-разметкой страницы одной книги."""
    html = """
    <html>
        <div class="product_main">
            <h1>Test Book</h1>
            <p class="price_color">£25.00</p>
            <p class="star-rating Three"></p>
            <p class="instock availability">
                In stock (10 available)
            </p>
        </div>

        <div id="product_description">
            <h2>Description</h2>
        </div>
        <p>Test description</p>

        <table class="table table-striped">
            <tr>
                <th>UPC</th>
                <td>123456789</td>
            </tr>
        </table>
    </html>
    """
    return html.encode("utf-8")


def test_get_book_data_structure(monkeypatch, sample_book_html: bytes) -> None:
    """Проверяет, что данные о книге возвращаются в виде словаря с нужными ключами."""

    class MockResponse:
        status_code = 200
        content = sample_book_html

    def mock_get(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(scraper.requests, "get", mock_get)

    result = scraper.get_book_data("http://example.com")

    expected_keys = {
        "title",
        "price",
        "rating",
        "availability",
        "description",
        "product_information",
    }

    assert isinstance(result, dict)
    assert expected_keys.issubset(result.keys())


def test_get_book_data_values(monkeypatch, sample_book_html: bytes) -> None:
    """Проверяет корректность извлечения значений отдельных полей книги."""

    class MockResponse:
        status_code = 200
        content = sample_book_html

    def mock_get(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(scraper.requests, "get", mock_get)

    result = scraper.get_book_data("http://example.com")

    assert result["title"] == "Test Book"
    assert result["price"] == "£25.00"
    assert result["rating"] == 3
    assert result["availability"] == "In stock (10 available)"
    assert result["description"] == "Test description"
    assert result["product_information"]["UPC"] == "123456789"


def test_get_book_data_request_error(monkeypatch) -> None:
    """Проверяет негативный сценарий: возврат пустого словаря при ошибке запроса."""

    class MockResponse:
        status_code = 404

    def mock_get(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(scraper.requests, "get", mock_get)

    result = scraper.get_book_data("http://example.com")

    assert result == {}


def test_scrape_books_and_save(monkeypatch, tmp_path) -> None:
    """Проверяет переход между страницами каталога, сбор книг и сохранение результата."""
    catalog_pages = {
        "page-1.html": """
            <html>
                <article class="product_pod">
                    <h3><a href="book1.html">Book 1</a></h3>
                </article>
                <li class="next"><a href="page-2.html">next</a></li>
            </html>
        """,
        "page-2.html": """
            <html>
                <article class="product_pod">
                    <h3><a href="book2.html">Book 2</a></h3>
                </article>
            </html>
        """,
    }
    requested_pages = []

    class MockResponse:
        def __init__(self, status_code, content=b""):
            self.status_code = status_code
            self.content = content

    def mock_get(url, *args, **kwargs):
        requested_pages.append(url)
        for page_name, html in catalog_pages.items():
            if page_name in url:
                return MockResponse(200, html.encode("utf-8"))
        return MockResponse(404)

    def mock_get_book_data(url: str) -> dict:
        return {"title": url.split("/")[-1]}

    monkeypatch.setattr(scraper.requests, "get", mock_get)
    monkeypatch.setattr(scraper, "get_book_data", mock_get_book_data)
    monkeypatch.chdir(tmp_path)
    result = scraper.scrape_books(is_save=True)
    # Проверяем сбор книг с обеих страниц
    assert len(result) == 2
    assert result[0]["title"] == "book1.html"
    assert result[1]["title"] == "book2.html"
    # Проверяем, что парсер запросил все три страницы
    assert any("page-1.html" in url for url in requested_pages)
    assert any("page-2.html" in url for url in requested_pages)
    assert any("page-3.html" in url for url in requested_pages)
    # Проверяем сохранение данных в файл
    file_path = tmp_path / "books_data.txt"
    assert file_path.exists()
    with open(file_path, "r", encoding="utf-8") as file:
        saved_data = json.load(file)
    assert len(saved_data) == 2
    assert saved_data[0]["title"] == "book1.html"
