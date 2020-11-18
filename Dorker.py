import re
import time

import requests
from bs4 import BeautifulSoup
from selenium import webdriver


class SqlDorker:

    def __init__(self):
        self.dorks = []
        self.dork = ''
        self.browser = None
        self.viewed_page = 0
        self.navigation_links = []
        self.links_for_test = []
        self.sql_errors = {
            "MySQL": (r"SQL syntax.*MySQL", r"Warning.*mysql_.*", r"MySQL Query fail.*", r"SQL syntax.*MariaDB server"),
            "PostgreSQL": (r"PostgreSQL.*ERROR", r"Warning.*\Wpg_.*", r"Warning.*PostgreSQL"),
            "Microsoft SQL Server": (
                r"OLE DB.* SQL Server", r"(\W|\A)SQL Server.*Driver", r"Warning.*odbc_.*", r"Warning.*mssql_",
                r"Msg \d+, Level \d+, State \d+", r"Unclosed quotation mark after the character string",
                r"Microsoft OLE DB Provider for ODBC Drivers"),
            "Microsoft Access": (
            r"Microsoft Access Driver", r"Access Database Engine", r"Microsoft JET Database Engine",
            r".*Syntax error.*query expression"),
            "Oracle": (
                r"\bORA-[0-9][0-9][0-9][0-9]", r"Oracle error", r"Warning.*oci_.*",
                "Microsoft OLE DB Provider for Oracle"),
            "IBM DB2": (r"CLI Driver.*DB2", r"DB2 SQL error"),
            "SQLite": (r"SQLite/JDBCDriver", r"System.Data.SQLite.SQLiteException"),
            "Informix": (r"Warning.*ibase_.*", r"com.informix.jdbc"),
            "Sybase": (r"Warning.*sybase.*", r"Sybase message")}
        self.webdriver_init()

    def webdriver_init(self):
        opts = webdriver.ChromeOptions()
        opts.headless = True
        self.browser = webdriver.Chrome(options=opts)

    def get_dorks(self):
        with open('dorks.txt', 'r', encoding='utf8') as dork_file:
            self.dorks = dork_file.readlines()

    def get_dorked_page(self, dork_for_test):
        print(f'Проверяю дорк {dork_for_test}')
        self.browser.get('https://cse.google.com/cse?cx=009462381166450434430:dqo-6rxvieq')
        login = self.browser.find_element_by_name('search')
        login.send_keys(dork_for_test)
        search_button = self.browser.find_element_by_css_selector('.gsc-search-button')
        search_button.click()
        time.sleep(3)

    def get_links_for_test(self):
        self.links_for_test = [i for i in self.browser.find_elements_by_css_selector('a[class="gs-title"]') if i.text]

    def check_links_block(self):
        for link_for_test in self.links_for_test:
            # Получаем сам url каждой ссылки поисковой выдачи
            adr_string = str(link_for_test.get_attribute('data-ctorig'))
            try:
                # TODO Проверить необходимость
                # Очищаем url от лишнего
                adr_string = adr_string.strip()
                adr_string = adr_string.replace(' ', '')
                adr_string = adr_string.replace('\n', '')
                adr_string = adr_string.replace('\r', '')
                # Заменяем в URL значок & между параметрами, добавляя перед ним одинарную кавычку
                # это нужно для тестирования GET параметров URL адреса на наличие SQL уязвимости
                # hacked_url = url.replace("&", "'&")
                # Очищаем URL от пробелов по обеим сторонам
                # ur = hacked_url.strip()
                # Если спереди нету http, то добавляем его
                adr_string = adr_string.replace("&", "'&")
                adr_string = adr_string.strip()
                if not adr_string.startswith('http'):
                    adr_string = 'http://' + adr_string
                # Проверяем очередной url
                self.check_link(url=adr_string)
            except Exception as exc:
                print(exc.args)

    def check_link(self, url):
        try:
            # Получаем HTML код по URL
            response = requests.get(url + "'")
            response_html = response.text
            # Проверяем на уязвимости
            is_vuln, db = self.check_vuln(html=response_html)
            print(f'Проверяю: {url}', end='')
            if not is_vuln:
                print()
            else:
                print(' ---Уязвим----')
                self.write_log(url=url, page_html=response_html)
        except Exception as exc:
            print(exc.args)

    def check_vuln(self, html):
        for db, errors in self.sql_errors.items():
            for error in errors:
                if re.compile(error).search(html):
                    return True, db
        return False, None

    def write_log(self, url, page_html):
        with open('sqls.txt', 'a', encoding='utf8') as logfile:
            try:
                soup = BeautifulSoup(page_html, "html.parser")
                # Пытаемся вытянуть со страницы заголовок Title
                title = soup.find('title').text
            except Exception as exc:
                title = 'NOTITLE'
            finally:
                print(url + "'" + '|' + title, file=logfile)

    def get_navigation_link(self,next_page):
        pages_links = self.browser.find_elements_by_xpath('//*[@class="gsc-cursor-page"]')
        next_page_link = [item for item in pages_links if item.text == str(next_page)][0]
        return next_page_link

    def run(self):
        self.get_dorks()
        for self.dork in self.dorks:
            self.dork = self.dork[:-1]
            self.get_dorked_page(dork_for_test=self.dork)
            self.viewed_page = 1
            while self.viewed_page <= 10:
                try:
                    self.get_links_for_test()
                    self.check_links_block()
                    self.viewed_page += 1
                    next_page_link = self.get_navigation_link(next_page=self.viewed_page)
                    next_page_link.click()
                    time.sleep(3)
                except Exception as exc:
                    print(exc.args)
                    break
            else:
                print(f'Проверка дорка {self.dork} закончена')

    # def __del__(self):
    #     self.browser.quit()


if __name__ == '__main__':
    sqldorker = SqlDorker()
    sqldorker.run()
