import os
import sys
import pytest

# Добавляем корневую папку проекта в пути поиска модулей Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import scraper


@pytest.fixture
def sample_book_html() -> bytes:
    """Фикстура с эталонной HTML-разметкой страницы одной книги."""
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
    """Проверяет сбор книг со страницы каталога и сохранение результата в файл."""
    catalog_html = """
    <html>
        <article class="product_pod">
            <h3>
                <a href="book1.html" title="Test Book">Test Book</a>
            </h3>
        </article>
    </html>
    """

    class MockResponse:
        status_code = 200
        content = catalog_html.encode("utf-8")

    def mock_get(*args, **kwargs):
        return MockResponse()

    def mock_get_book_data(url: str) -> dict:
        return {
            "title": "Test Book",
            "price": "£25.00",
            "rating": 3,
        }

    monkeypatch.setattr(scraper.requests, "get", mock_get)
    monkeypatch.setattr(scraper, "get_book_data", mock_get_book_data)
    monkeypatch.chdir(tmp_path)

    result = scraper.scrape_books(is_save=True)

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["title"] == "Test Book"

    file_path = tmp_path / "books_data.txt"
    assert file_path.exists()

    with open(file_path, "r", encoding="utf-8") as file:
        saved_data = json.load(file)

    assert len(saved_data) == 1
    assert saved_data[0]["title"] == "Test Book"
