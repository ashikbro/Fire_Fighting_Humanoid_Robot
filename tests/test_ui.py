import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

@pytest.fixture(scope="module")
def driver():
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
    form = driver.find_element(By.TAG_NAME, "form")
    assert form is not None

def test_username_input_exists(driver):
    driver.get("http://localhost:5000/login")
    username_input = driver.find_element(By.NAME, "username")
    assert username_input is not None

def test_password_input_exists(driver):
    driver.get("http://localhost:5000/login")
    password_input = driver.find_element(By.NAME, "password")
    assert password_input is not None

if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__]))
