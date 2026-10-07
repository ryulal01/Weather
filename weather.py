import json
import urllib.request
import urllib.error
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

CLOUD_URL = "https://cloud.mail.ru/public/LWcw/kpMqFgztw"
LOCAL_FILE = Path("cities.txt")
API_URL = "https://wttr.in/{city}?format=j1"
REQUEST_TIMEOUT = 15
RETRIES = 3


@dataclass
class WeatherData:
    city: str
    temperature_c: float
    country: str


def load_cities() -> list[str]:
    if LOCAL_FILE.exists():
        lines = LOCAL_FILE.read_text(encoding="utf-8").splitlines()
    else:
        print(f"Файл {LOCAL_FILE} не найден, пробую скачать из облака...")
        with urllib.request.urlopen(CLOUD_URL, timeout=REQUEST_TIMEOUT) as resp:
            lines = resp.read().decode("utf-8").splitlines()

    cities = [line.strip() for line in lines if line.strip()]
    unique = list(dict.fromkeys(cities))
    print(f"Загружено городов: {len(unique)} (уникальных)\n")
    return unique


def fetch_weather(city: str) -> WeatherData:
    url = API_URL.format(city=urllib.parse.quote(city))
    last_error = None

    for attempt in range(1, RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "curl"})
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            temperature = float(data["current_condition"][0]["temp_C"])
            country = data["nearest_area"][0]["country"][0]["value"]
            return WeatherData(city=city, temperature_c=temperature, country=country)
        except (urllib.error.URLError, KeyError, IndexError, ValueError,
                json.JSONDecodeError) as err:
            last_error = err
            print(f"  [{city}] попытка {attempt}/{RETRIES} не удалась: {err}")

    raise RuntimeError(f"Не удалось получить данные по городу '{city}': {last_error}")


def print_city_info(weather: WeatherData) -> None:
    sign = "+" if weather.temperature_c >= 0 else "-"
    print(f"{weather.city}, {weather.country} {sign}{abs(weather.temperature_c):.0f} °C")


def print_country_stats(weather_list: list[WeatherData]) -> None:
    groups: dict[str, list[float]] = defaultdict(list)
    for w in weather_list:
        groups[w.country].append(w.temperature_c)

    print("\nСтатистика по странам:")
    for country in sorted(groups):
        temps = groups[country]
        avg = round(sum(temps) / len(temps))
        print(
            f"{country} — {len(temps)} cities, "
            f"avg: {avg:+.0f} °C, "
            f"min: {min(temps):+.0f} °C, "
            f"max: {max(temps):+.0f} °C"
        )


def main() -> None:
    try:
        cities = load_cities()
    except Exception as err:
        print(f"Ошибка при загрузке списка городов: {err}")
        return

    weather_list: list[WeatherData] = []
    for city in cities:
        try:
            data = fetch_weather(city)
        except RuntimeError as err:
            print(err)
            continue
        weather_list.append(data)
        print_city_info(data)

    if weather_list:
        print_country_stats(weather_list)
    else:
        print("Не удалось получить данные ни по одному городу.")


if __name__ == "__main__":
    main()
