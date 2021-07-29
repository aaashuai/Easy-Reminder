import httpx

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from settings import Config


class WeatherSelenium:
    def __init__(self):
        chrome_options = Options()
        chrome_options.headless = True
        self.driver = webdriver.Chrome(options=chrome_options)
        self.geokey = Config.GEO_KEY

    def screenshot(self, url: str) -> bytes:
        self.driver.get(url)
        elem_summary = self.driver.find_element_by_xpath('//div[@class="c-city-weather-current__bg"]')
        summary = elem_summary.screenshot_as_png
        return summary

    def query_city_id(self, location: str, adm: str) -> str:
        url = "https://geoapi.qweather.com/v2/city/lookup"
        res = httpx.get(url, params=dict(key=self.geokey, location=location, adm=adm))
        assert res.status_code == 200, "查询city id 失败"
        j = res.json()
        assert j["code"] == "200", "查询city id 失败"
        return j["location"][0]["id"]

    def query_weather(self, city_id: str) -> str:
        url = "https://devapi.qweather.com/v7/weather/now"
        res = httpx.get(url, params=dict(key=self.geokey, location=city_id))
        assert res.status_code == 200, "查询天气失败"
        j = res.json()
        assert j["code"] == "200", "查询天气失败"
        return j["fxLink"]

    def craw_weather(self, location: str, adm: str = None) -> bytes:
        city_id = weather_selenium.query_city_id(location, adm)
        url = weather_selenium.query_weather(city_id)
        return self.screenshot(url)


weather_selenium = WeatherSelenium()
