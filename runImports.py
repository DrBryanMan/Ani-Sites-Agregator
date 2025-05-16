import requests
from bs4 import BeautifulSoup
import json
import os
import time
import re
from typing import List, Dict, Any, Optional, Union
import random

class ScraperException(Exception):
    """Виключення для скрапера"""
    pass

class UniversalScraper:
    def __init__(self, site_type="anitube"):
        """
        Ініціалізація скрапера для конкретного сайту
        
        :param site_type: тип сайту: 'anitube', 'uakino', 'uaserial' або 'toloka'
        """
        self.site_type = site_type.lower()
        
        if self.site_type == "anitube":
            self.base_url = "https://anitube.in.ua/anime"
            self.img_url = "https://anitube.in.ua"
            self.links_file = "data/anitube_links.json"
            self.site_field = "anitube"
        elif self.site_type == "uakino":
            self.base_url = "https://uakino.me/animeukr"
            self.img_url = "https://uakino.me"
            self.links_file = "data/uakino_links.json"
            self.site_field = "uakino"
        elif self.site_type == "uaserial":
            self.base_url = "https://uaserial.me/anime"
            self.img_url = "https://uaserial.me"
            self.links_file = "data/uaserial_links.json"
            self.site_field = "uaserial"
        elif self.site_type == "toloka":
            # self.base_url = "https://toloka.to/f127"
            self.base_url = "https://toloka.to/f194"
            self.link_url = "https://toloka.to"
            self.img_url = "https:"
            # self.links_file = "data/toloka_links.json"
            self.links_file = "data/toloka-sub_links.json"
            self.site_field = "toloka"
            self.items_per_page = 90
        else:
            raise ScraperException(f"Невідомий тип сайту: {site_type}")
        
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "referrerpolicy": "no-referrer"
        }
        
    def login(self) -> None:
        """Авторизація на сайті (лише для Толоки)"""
        if self.site_type != "toloka":
            print("Авторизація потрібна лише для Толоки")
            return
            
        login_url = "https://toloka.to/login.php"
        username = os.environ.get("TOLOKA_USERNAME")
        password = os.environ.get("TOLOKA_PASSWORD")

        if not username or not password:
            raise ScraperException("TOLOKA_USERNAME або TOLOKA_PASSWORD не задані в середовищі.")

        payload = {
            "username": username,
            "password": password,
            "autologin": "on",
            "login": "Вхід"
        }
        response = self.session.post(login_url, data=payload, headers=self.headers)
        if "Вихід" not in response.text and "вийти" not in response.text.lower():
            raise ScraperException("Не вдалося авторизуватися. Перевір логін або пароль.")
        print("Успішний вхід!")
        
    def make_request(self, url: str) -> BeautifulSoup:
        """Виконує HTTP запит і повертає об'єкт BeautifulSoup"""
        try:
            if self.site_type == "toloka":
                response = self.session.get(url, headers=self.headers)
            else:
                response = requests.get(url, headers=self.headers)
                
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except requests.RequestException as e:
            raise ScraperException(f"Помилка запиту до {url}: {e}")
    
    def extract_id(self, link: str) -> str:
        """Витягує ID з посилання в залежності від типу сайту"""
        if self.site_type == "anitube":
            # Шукаємо ID у посиланні вигляду https://anitube.in.ua/123-anime-name/
            match = re.match(r"https?://anitube\.in\.ua/(\d+)-", link)
            if match:
                return match.group(1)
        elif self.site_type == "uakino":
            # Шукаємо ID у посиланні вигляду https://uakino.me/animeukr/.../123-film-name.html
            match = re.match(r"https?://uakino\.me/animeukr/(?:[\w\-]+/)*(\d+)-", link)
            if match:
                return match.group(1)
        elif self.site_type == "toloka":
            # Шукаємо ID у посиланні вигляду https://toloka.to/t123456
            match = re.match(r"https?://toloka\.to/t(\d+)", link)
            if match:
                return match.group(1)
                
        # Повертаємо "0", якщо ID не знайдено
        return "0"
    
    def get_poster_from_detail_page(self, detail_url: str) -> str:
        """Отримує URL постера з детальної сторінки (використовується для Толоки)"""
        if self.site_type != "toloka":
            return ""
            
        try:
            soup = self.make_request(detail_url)
            poster_element = soup.select_one(".postbody div img")
            if poster_element:
                poster_url = poster_element.get("src")
                if poster_url and not poster_url.startswith("http"):
                    poster_url = f"{self.img_url}{poster_url}"
                return poster_url
            return ""
        except Exception as e:
            print(f"Помилка при отриманні постера з {detail_url}: {e}")
            return ""
    
    def extract_item_info(self, item_block) -> Optional[Dict[str, str]]:
        """Витягує інформацію про елемент (аніме, фільм, серіал) з блоку HTML"""
        try:
            if self.site_type == "anitube":
                # Знаходимо назву аніме
                title_element = item_block.select_one(".story_c h2 a")
                title = title_element.text.strip() if title_element else "Без назви"
                
                # Знаходимо посилання на аніме
                link = title_element.get("href") if title_element else ""
                
                # Знаходимо посилання на постер
                poster_element = item_block.select_one(".story_c_l .story_post img")
                poster_url = poster_element.get("src") if poster_element else ""
                
                # Повний URL постера
                if poster_url and not poster_url.startswith("http"):
                    poster_url = f"{self.img_url}{poster_url}"
                
            elif self.site_type == "uakino":
                # Знаходимо назву фільму
                title_element = item_block.select_one(".movie-title")
                title = title_element.text.strip() if title_element else "Без назви"
                
                # Знаходимо посилання на фільм
                link = title_element.get("href") if title_element else ""
                if link and not link.startswith("http"):
                    link = f"{self.img_url}{link}"
                
                # Знаходимо посилання на постер
                poster_element = item_block.select_one(".movie-img img")
                poster_url = poster_element.get("src") if poster_element else ""
                
                # Повний URL постера
                if poster_url and not poster_url.startswith("http"):
                    poster_url = f"{self.img_url}{poster_url}"
                
            elif self.site_type == "uaserial":
                # Знаходимо назву серіалу
                title_element = item_block.select_one("a")
                title = title_element.get("title") if title_element else "Без назви"
                
                # Знаходимо посилання на серіал
                link = title_element.get("href") if title_element else ""
                if link and not link.startswith("http"):
                    link = f"{self.img_url}{link}"
                
                # Знаходимо посилання на постер
                poster_element = item_block.select_one("a .absolute__fill")
                poster_url = poster_element.get("src") if poster_element else ""
                
                # Повний URL постера
                if poster_url and not poster_url.startswith("http"):
                    poster_url = f"{self.img_url}{poster_url}"
                
            elif self.site_type == "toloka":
                # Знаходимо назву і посилання
                title_element = item_block.select_one("a.topictitle")
                if not title_element:
                    return None
                    
                title = title_element.text.strip()
                link = title_element.get("href")
                
                if link and not link.startswith("http"):
                    link = f"{self.link_url}/{link}"
                    
                # Для Толоки постер отримується з детальної сторінки
                poster_url = self.get_poster_from_detail_page(link)
            
            return {
                "title": title,
                "link": link,
                "poster": poster_url
            }
        except Exception as e:
            print(f"Помилка при витяганні інформації для {self.site_type}: {e}")
            return None
    
    def get_max_pages(self) -> int:
        """Визначає максимальну кількість сторінок пагінації"""
        try:
            soup = self.make_request(self.base_url)
            
            if self.site_type == "anitube":
                last_page_element = soup.select_one(".navigation .navi_pages a:last-child")
            elif self.site_type == "uakino":
                last_page_element = soup.select_one(".navigation a:last-child")
                # Для UAKino зменшуємо максимальну кількість сторінок на 2
                page_reduction = 2
            elif self.site_type == "uaserial":
                pages = soup.select('.pagination li.page a')
                last_page_element = pages[-1] if pages else None
                page_reduction = 0
            elif self.site_type == "toloka":
                navigation = soup.select_one("span.navigation")
                if not navigation:
                    print("Пагінація не знайдена, припускаємо 1 сторінку")
                    return 1
                    
                links = navigation.find_all("a")
                page_numbers = []
                for link in links:
                    text = link.get_text(strip=True)
                    if text.isdigit():
                        page_numbers.append(int(text))
                
                if page_numbers:
                    max_page = max(page_numbers)
                    print(f"Знайдено {max_page} сторінок")
                    return max_page
                    
                print("Не вдалося знайти числові сторінки, припускаємо 1")
                return 1
            else:
                last_page_element = None
                page_reduction = 0
            
            # Цей код не виконується для Толоки, оскільки вище є return
            if not last_page_element:
                print("Елемент пагінації не знайдено, припускаємо, що є лише 1 сторінка")
                return 1
            
            # Отримуємо текст або перевіряємо посилання
            if last_page_element.text.strip().isdigit():
                # Якщо текст посилання є числом
                max_pages = int(last_page_element.text.strip())
            else:
                # Якщо текст не є числом, спробуємо витягти число з URL
                href = last_page_element.get("href", "")
                
                if self.site_type == "anitube" or self.site_type == "uakino":
                    page_numbers = re.findall(r'/page/(\d+)/', href)
                elif self.site_type == "uaserial":
                    page_numbers = re.findall(r'/anime/(\d+)/', href)
                else:
                    page_numbers = []
                    
                if page_numbers:
                    max_pages = int(page_numbers[0])
                else:
                    print("Не вдалося визначити кількість сторінок, припускаємо, що є лише 1 сторінка")
                    return 1
            
            # Застосовуємо зменшення для UAKino
            if self.site_type == "uakino" and max_pages > page_reduction:
                max_pages -= page_reduction
                
            return max_pages
        
        except Exception as e:
            print(f"Помилка при визначенні кількості сторінок: {e}")
            return 1
    
    def get_page_url(self, page: int) -> str:
        """Формує URL для певної сторінки (використовується для Толоки)"""
        if self.site_type != "toloka":
            return self.base_url
            
        if page == 1:
            return f"{self.base_url}?sort=8"
        else:
            offset = (page - 1) * self.items_per_page
            return f"{self.base_url}-{offset}?sort=8"
    
    def collect_links_without_details(self, max_pages: int = None) -> List[str]:
        """Збирає лише URL-адреси без отримання детальної інформації (для Толоки)"""
        if self.site_type != "toloka":
            return []
            
        if max_pages is None:
            max_pages = self.get_max_pages()
            
        print(f"Збираю посилання з {max_pages} сторінок (без деталей)...")
        all_links = []
        
        for page in range(1, max_pages + 1):
            try:
                page_url = self.get_page_url(page)
                print(f"Обробка сторінки {page}/{max_pages}: {page_url}")
                
                soup = self.make_request(page_url)
                anime_rows = soup.select("table.forumline td.row1")
                
                for row in anime_rows:
                    title_element = row.select_one("a.topictitle")
                    if title_element:
                        link = title_element.get("href")
                        if link and not link.startswith("http"):
                            link = f"{self.link_url}/{link}"
                        all_links.append(link)
                        
                time.sleep(random.uniform(1.0, 2.0))
            except Exception as e:
                print(f"Помилка при обробці сторінки {page}: {e}")
                
        return all_links
    
    def collect_links(self, max_pages: int = None) -> List[Dict[str, str]]:
        """Збирає посилання на елементи з усіх або вказаної кількості сторінок"""
        if max_pages is None:
            max_pages = self.get_max_pages()
        
        print(f"Збираю посилання з {max_pages} сторінок для {self.site_type}...")
        all_items = []
        
        for page in range(1, max_pages + 1):
            try:
                if self.site_type == "anitube" or self.site_type == "uakino":
                    page_url = f"{self.base_url}/page/{page}/" if page > 1 else self.base_url
                elif self.site_type == "uaserial":
                    page_url = f"{self.base_url}/{page}/" if page > 1 else self.base_url
                elif self.site_type == "toloka":
                    page_url = self.get_page_url(page)
                else:
                    page_url = self.base_url
                    
                print(f"Обробка сторінки {page}/{max_pages}: {page_url}")
                
                soup = self.make_request(page_url)
                
                if self.site_type == "anitube":
                    item_blocks = soup.select(".story")
                elif self.site_type == "uakino":
                    item_blocks = soup.select(".movie-item")
                elif self.site_type == "uaserial":
                    item_blocks = soup.select("#filters-grid-content .col .item")
                elif self.site_type == "toloka":
                    item_blocks = soup.select("table.forumline td.row1")
                else:
                    item_blocks = []
                
                for block in item_blocks:
                    item_info = self.extract_item_info(block)
                    if item_info:
                        all_items.append(item_info)
                        if self.site_type == "toloka":
                            time.sleep(random.uniform(0.5, 1.0))
                
                # Затримка між запитами для запобігання блокуванню
                if self.site_type == "toloka":
                    time.sleep(random.uniform(2.0, 3.5))
                else:
                    time.sleep(random.uniform(1.0, 2.5))
            except Exception as e:
                print(f"Помилка при обробці сторінки {page}: {e}")
        
        return all_items
    
    def save_links(self, links: List[Dict[str, str]]) -> None:
        """Зберігає посилання у JSON файл"""
        try:
            # Створюємо директорію, якщо вона не існує
            os.makedirs(os.path.dirname(self.links_file), exist_ok=True)
            
            with open(self.links_file, "w", encoding="utf-8") as f:
                json.dump(links, f, ensure_ascii=False, indent=2)
            print(f"Посилання збережено у файл {self.links_file}")
        except Exception as e:
            raise ScraperException(f"Помилка при збереженні посилань: {e}")
    
    def load_links(self) -> List[Dict[str, str]]:
        """Завантажує посилання з JSON файлу"""
        try:
            if not os.path.exists(self.links_file):
                return []
                
            with open(self.links_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise ScraperException(f"Помилка при завантаженні посилань: {e}")
    
    def update_links(self, pages_to_check: int = None) -> List[Dict[str, str]]:
        """Оновлює список посилань, перевіряючи вказану кількість останніх сторінок"""
        # Визначаємо кількість сторінок для перевірки в залежності від сайту
        if pages_to_check is None:
            if self.site_type == "anitube":
                pages_to_check = 10
            elif self.site_type == "toloka":
                pages_to_check = 3
            else:
                pages_to_check = 5
        
        existing_links = self.load_links()
        existing_urls = {item["link"] for item in existing_links}
        
        # Для Толоки є особливий метод оновлення
        if self.site_type == "toloka":
            print(f"Перевіряю {pages_to_check} останніх сторінок на наявність нових аніме...")
            new_urls = self.collect_links_without_details(max_pages=pages_to_check)
            
            # Знайти нові URL-адреси, яких немає в існуючому списку
            completely_new_urls = [url for url in new_urls if url not in existing_urls]
            
            if not completely_new_urls:
                print("Нових аніме не знайдено")
                return existing_links
            
            # Отримати повну інформацію тільки для нових посилань
            added_count = 0
            for new_url in completely_new_urls:
                try:
                    print(f"Отримання інформації для нового аніме: {new_url}")
                    soup = self.make_request(new_url)
                    
                    # Отримати назву
                    title_element = soup.select_one("a.maintitle")
                    if not title_element:
                        print(f"Не вдалося отримати назву для {new_url}")
                        continue
                        
                    title = title_element.text.strip()
                    
                    # Отримати постер
                    print(f"Отримання постера для {title} з {new_url}")
                    poster_url = self.get_poster_from_detail_page(new_url)
                    
                    # Додати нове аніме до списку
                    new_anime = {
                        "title": title,
                        "link": new_url,
                        "poster": poster_url
                    }
                    
                    existing_links.insert(0, new_anime)
                    existing_urls.add(new_url)
                    added_count += 1
                    print(f"Додано нове аніме: {title} із постером {poster_url}")
                    
                    time.sleep(random.uniform(0.5, 1.0))
                except Exception as e:
                    print(f"Помилка при отриманні інформації для {new_url}: {e}")
            
            if added_count > 0:
                print(f"Додано {added_count} нових аніме")
                self.save_links(existing_links)
            else:
                print("Нових аніме не додано через помилки")
                
            return existing_links
        else:
            # Для інших сайтів
            print(f"Перевіряю {pages_to_check} останніх сторінок для {self.site_type} на наявність нових елементів...")
            new_links = self.collect_links(max_pages=pages_to_check)
            
            added_count = 0
            for link in new_links:
                if link["link"] not in existing_urls:
                    existing_links.insert(0, link)
                    existing_urls.add(link["link"])
                    added_count += 1
                    print(f"Додано новий елемент: {link['title']} із постером {link['poster']}")
            
            if added_count > 0:
                print(f"Додано {added_count} нових елементів")
                self.save_links(existing_links)
            else:
                print("Нових елементів не знайдено")
            
            return existing_links

    def run(self):
        """Запускає процес скрапінгу"""
        try:
            print(f"Запуск скрапінгу для {self.site_type.upper()}")
            
            # Для Толоки потрібна авторизація перед початком скрапінгу
            if self.site_type == "toloka":
                self.login()
                
            if not os.path.exists(self.links_file):
                print("Файл зі списком посилань не знайдено. Збираю всі посилання...")
                links = self.collect_links()
                self.save_links(links)
            else:
                print("Файл зі списком посилань знайдено. Оновлюю список...")
                self.update_links()
            
            print(f"Скрапінг {self.site_type.upper()} завершено успішно!")
        except Exception as e:
            print(f"Помилка при виконанні скрапінгу для {self.site_type}: {e}")


def run_all_scrapers():
    """Запускає скрапінг для всіх сайтів"""
    sites = ["anitube", "uakino", "uaserial", "toloka"]
    
    for site in sites:
        print(f"\n{'-'*50}")
        print(f"Запуск скрапера для {site.upper()}")
        print(f"{'-'*50}\n")
        
        scraper = UniversalScraper(site)
        scraper.run()
        
        print(f"\n{'-'*50}")
        print(f"Завершено скрапінг для {site.upper()}")
        print(f"{'-'*50}\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Універсальний скрапер для аніме сайтів.')
    parser.add_argument('--site', type=str, choices=['anitube', 'uakino', 'uaserial', 'toloka', 'all'],
                        default='all', help='Сайт для скрапінгу (за замовчуванням: all)')
    
    args = parser.parse_args()
    
    if args.site == 'all':
        run_all_scrapers()
    else:
        print(f"\n{'-'*50}")
        print(f"Запуск скрапера для {args.site.upper()}")
        print(f"{'-'*50}\n")
        
        scraper = UniversalScraper(args.site)
        scraper.run()
        
        print(f"\n{'-'*50}")
        print(f"Завершено скрапінг для {args.site.upper()}")
        print(f"{'-'*50}\n")
