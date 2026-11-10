import pytest

pytestmark = pytest.mark.ui

# selenium is imported lazily so that deselecting UI tests (-m "not ui")
# works in environments where selenium is not installed. Locators use the
# string values of selenium's By constants ("tag name", "name").

@pytest.fixture(scope="module")
def driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)
    yield driver
    driver.quit()

def test_login_page_title(driver):
    driver.get("http://localhost:5000/login")
    assert "Login" in driver.title

def test_login_form_exists(driver):
    driver.get("http://localhost:5000/login")
    form = driver.find_element("tag name", "form")
    assert form is not None

def test_username_input_exists(driver):
    driver.get("http://localhost:5000/login")
    username_input = driver.find_element("name", "username")
    assert username_input is not None

def test_password_input_exists(driver):
    driver.get("http://localhost:5000/login")
    password_input = driver.find_element("name", "password")
    assert password_input is not None

if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__]))
