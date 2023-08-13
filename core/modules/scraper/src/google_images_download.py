import http.client
import http.client
import json
import logging
import os
import platform
import re
import sys
import time  # Importing the time library to check the time of code execution
import traceback
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from urllib.parse import quote
from urllib.request import Request, urlopen

import selenium.common.exceptions
from PIL import Image
from selenium.webdriver.chrome.service import Service as BraveService
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.ie.service import Service as IEService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from webdriver_manager.microsoft import IEDriverManager

from core.handlers.file import FileHandler
from core.handlers.status import StatusHandler
from core.modules.scraper.src.gid_tables import COLOR_TABLE, SIZE_TABLE, TYPE_TABLE, TIME_TABLE, ASPECT_RATIO_TABLE, \
    LICENSE_TABLE
from core.modules.scraper.src.scraper_config import ScraperConfig

http.client._MAXHEADERS = 1000

logger = logging.getLogger(__name__)

MAX_IMAGE_THREADS = 10


def clean_description(description, search):
    if "-" in description:
        description = description.split("-")[0].strip()
    if "|" in description:
        description = description.split("|")[0].strip()

    if "," in description:
        description = description.split(",")[0].strip()

    description = description.lower()
    search = search.lower()
    if search in description:
        description = description.replace(search, "")

    description = ", ".join([description, search])
    # A list of common punctuation marks
    punc_chars = [".", ";", ":", "!", "?"]
    for punc in punc_chars:
        description = description.replace(punc, ",")
    chars_to_strip = ["'", "\"", "\\", "/", "(", ")", "[", "]", "{", "}", "@", "#", "$"]
    for char in chars_to_strip:
        description = description.replace(char, "")
    description_parts = description.split(",")
    description = ", ".join([part.strip() for part in description_parts])
    return description


def download_chromedriver(target_dir):
    os_type = platform.system().lower()

    # This will automatically get the latest version of the chrome driver
    latest_version_url = "https://chromedriver.storage.googleapis.com/LATEST_RELEASE"
    latest_version = urlopen(latest_version_url).read().decode('utf-8')
    chrome_driver_url = None
    if os_type == 'windows':
        chrome_driver_url = f"https://chromedriver.storage.googleapis.com/{latest_version}/chromedriver_win32.zip"
    elif os_type == 'linux':
        if platform.architecture()[0] == '64bit':
            chrome_driver_url = f"https://chromedriver.storage.googleapis.com/{latest_version}/chromedriver_linux64.zip"
        else:
            chrome_driver_url = f"https://chromedriver.storage.googleapis.com/{latest_version}/chromedriver_linux32.zip"
    elif os_type == 'darwin':
        # In macOS we will need to distinguish between Intel and ARM architectures
        if platform.processor() == "arm":
            chrome_driver_url = f"https://chromedriver.storage.googleapis.com/{latest_version}/chromedriver_mac_arm64.zip"
        else:
            chrome_driver_url = f"https://chromedriver.storage.googleapis.com/{latest_version}/chromedriver_mac64.zip"

    if chrome_driver_url is None:
        logger.warning("Unable to determine chromedriver version to install.")
        return

    response = urllib.request.urlopen(chrome_driver_url)

    with open(f"{target_dir}/chromedriver.zip", "wb") as f:
        f.write(response.read())

    # Unzip the chromedriver.zip file
    with zipfile.ZipFile(f"{target_dir}/chromedriver.zip", 'r') as zip_ref:
        zip_ref.extractall(target_dir)

    # Add the executable permission to the chromedriver (Not necessary for Windows)
    if os_type in ['linux', 'darwin']:
        os.chmod(f"{target_dir}/chromedriver", 0o755)

        return f"{target_dir}/chromedriver"
    return f"{target_dir}\\chromedriver.exe"


class GoogleImagesDownloader:
    def __init__(self):
        pass

    @staticmethod
    def _extract_data_pack(page):
        start_line = page.find("AF_initDataCallback({key: \\'ds:1\\'") - 10
        start_object = page.find('[', start_line + 1)
        end_object = page.rfind(']', 0, page.find('</script>', start_object + 1)) + 1
        object_raw = str(page[start_object:end_object])
        return bytes(object_raw, "utf-8").decode("unicode_escape")

    @staticmethod
    def _extract_data_pack_extended(page):
        start_line = page.find("AF_initDataCallback({key: 'ds:1'") - 10
        start_object = page.find('[', start_line + 1)
        end_object = page.rfind(']', 0, page.find('</script>', start_object + 1)) + 1
        return str(page[start_object:end_object])

    @staticmethod
    def _extract_data_pack_ajax(data):
        lines = data.split('\n')
        return json.loads(lines[3])[0][2]

    @staticmethod
    def _image_objects_from_pack(data):
        image_data = json.loads(data)
        # NOTE: google sometimes changes their format, breaking this. set a breakpoint here to find the correct index
        grid = image_data[56][-1][0][-1][-1][0]
        image_objects = []
        for item in grid:
            obj = list(item[0][0].values())[0]
            # ads and carousels will be empty
            if not obj or not obj[1]:
                continue
            image_objects.append(obj)
        return image_objects

    # Downloading entire Web Document (Raw Page Content)
    def download_page(self, url):
        headers = {
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.104 Safari/537.36"}
        try:
            req = urllib.request.Request(url, headers=headers)
            resp = urllib.request.urlopen(req)
            response_data = str(resp.read())
        except:
            print("Could not open URL. Please check your internet connection and/or ssl settings \n"
                  "If you are using proxy, make sure your proxy settings is configured correctly")
            sys.exit()

        try:
            return self._image_objects_from_pack(self._extract_data_pack(response_data)), self.get_all_tabs(
                response_data)
        except Exception as e:
            print(e)
            print(
                'Image objects data unpacking failed. Please leave a comment with the above error at https://github.com/Joeclinton1/google-images-download/pull/26')
            sys.exit()

    # Download Page for more than 100 images
    def download_extended_page(self, url, chromedriver, browser):
        from selenium import webdriver
        from selenium.webdriver.common.keys import Keys
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument("--headless")
        try:
            if browser == 'firefox':
                web_browser = webdriver.Firefox(options=options, service=FirefoxService(GeckoDriverManager().install()))
            elif browser == 'chrome':
                web_browser = webdriver.Chrome(options=options, service=ChromeService(chromedriver))
            elif browser == 'chromium':
                web_browser = webdriver.Chrome(options=options, service=ChromeService(chromedriver))
            elif browser == 'brave':
                web_browser = webdriver.Chrome(options=options, service=BraveService(chromedriver))
            elif browser == 'safari':
                web_browser = webdriver.Safari(options=options)
            elif browser == 'edge':
                web_browser = webdriver.Edge(options=options, service=EdgeService(EdgeChromiumDriverManager().install()))
            elif browser == 'ie':
                web_browser = webdriver.Ie(options=options, service=IEService(IEDriverManager().install()))
            else:
                logger.warning("The requested browser is not supported. Please choose one of the following: Firefox, "
                               "Chrome, Safari, Edge, ie")
                return None, None
        except Exception as e:
            logger.warning(f"Exception loading web browser: {e}")
            traceback.print_exc()
            return None, None

        web_browser.set_window_size(1024, 768)

        # Open the link
        web_browser.get(url)
        web_browser.execute_script("""
            (function(XHR){
                "use strict";
                var open = XHR.prototype.open;
                var send = XHR.prototype.send;
                var data = [];
                XHR.prototype.open = function(method, url, async, user, pass) {
                    this._url = url;
                    open.call(this, method, url, async, user, pass);
                }
                XHR.prototype.send = function(data) {
                    var self = this;
                    var url = this._url;
                    function stateChanged() {
                        if (self.readyState == 4) {
                            console.log("data available for: " + url)
                            XHR.prototype._data.push(self.response);
                        }
                    }
                    if (url.includes("/batchexecute?")) {
                        this.addEventListener("readystatechange", stateChanged, false);
                    }
                    send.call(this, data);
                };
                XHR.prototype._data = [];
            })(XMLHttpRequest);
        """)

        time.sleep(1)

        # Bypass "Before you continue" if it appears
        try:
            web_browser.find_element(By.CSS_SELECTOR, "[aria-label='Accept all']").click()
            time.sleep(1)
        except selenium.common.exceptions.NoSuchElementException:
            pass

        print("Getting you a lot of images. This may take a few moments...")
        element = web_browser.find_element(By.TAG_NAME, "body")
        # Scroll down
        for i in range(50):
            element.send_keys(Keys.PAGE_DOWN)
            time.sleep(0.3)

        try:
            web_browser.find_element(By.XPATH, '//input[@value="Show more results"]').click()
            for i in range(50):
                element.send_keys(Keys.PAGE_DOWN)
                time.sleep(0.3)  # bot id protection
        except:
            for i in range(10):
                element.send_keys(Keys.PAGE_DOWN)
                time.sleep(0.3)  # bot id protection

        print("Reached end of Page.")
        time.sleep(0.5)

        source = web_browser.page_source  # page source
        images = self._image_objects_from_pack(self._extract_data_pack_extended(source))

        ajax_data = web_browser.execute_script("return XMLHttpRequest.prototype._data")  # I think this is broken
        for chunk in ajax_data if ajax_data else []:
            images += self._image_objects_from_pack(self._extract_data_pack_ajax(chunk))

        # close the browser
        web_browser.close()

        return images, self.get_all_tabs(source)

    # Correcting the escape characters for python2
    @staticmethod
    def replace_with_byte(match):
        return chr(int(match.group(0)[1:], 8))

    def repair(self, broken_json):
        invalid_escape = re.compile(r'\\[0-7]{1,3}')  # up to 3 digits for byte values up to FF
        return invalid_escape.sub(self.replace_with_byte, broken_json)

    # Finding 'Next Image' from the given raw page
    @staticmethod
    def get_next_tab(s):
        start_line = s.find('class="dtviD"')
        if start_line == -1:  # If no links are found then give an error!
            end_quote = 0
            link = "no_tabs"
            return link, '', end_quote
        else:
            start_line = s.find('class="dtviD"')
            start_content = s.find('href="', start_line + 1)
            end_content = s.find('">', start_content + 1)
            url_item = "https://www.google.com" + str(s[start_content + 6:end_content])
            url_item = url_item.replace('&amp;', '&')

            start_line_2 = s.find('class="dtviD"')
            s = s.replace('&amp;', '&')
            start_content_2 = s.find(':', start_line_2 + 1)
            end_content_2 = s.find('&usg=', start_content_2 + 1)
            url_item_name = str(s[start_content_2 + 1:end_content_2])

            chars = url_item_name.find(',g_1:')
            chars_end = url_item_name.find(":", chars + 6)
            if chars_end == -1:
                updated_item_name = (url_item_name[chars + 5:]).replace("+", " ")
            else:
                updated_item_name = (url_item_name[chars + 5:chars_end]).replace("+", " ")

            return url_item, updated_item_name, end_content

    # Getting all links with the help of '_images_get_next_image'
    def get_all_tabs(self, page):
        tabs = {}
        while True:
            item, item_name, end_content = self.get_next_tab(page)
            if item == "no_tabs":
                break
            else:
                if len(item_name) > 100 or item_name == "background-color":
                    break
                else:
                    tabs[item_name] = item  # Append all the links in the list named 'Links'
                    time.sleep(0.1)  # Timer could be used to slow down the request for image downloads
                    page = page[end_content:]
        return tabs

    # Format the object in readable format
    @staticmethod
    def format_object(source_data, keyword):
        data = source_data[1]
        main_info = data[3]
        info = next((d for d in data if isinstance(d, dict) and "2003" in d.keys()), None)
        if not info:
            return None
        try:
            formatted_object = {
                'image_height': main_info[2],
                'image_width': main_info[1],
                'image_link': main_info[0],
                'image_format': os.path.splitext(main_info[0])[1],
                'image_description': info['2003'][3],
                'image_search_term': keyword,
                'image_host': info['2003'][17],
                'image_source': info['2003'][2],
                'image_thumbnail_url': data[2][0],
            }
            return formatted_object
        except Exception as e:
            print(f"Exception with parsing: {e}")
            return None

    @staticmethod
    def similar_images(similar_images):
        try:
            base_url = 'https://www.google.com/searchbyimage?site=search&sa=X&image_url=' + similar_images
            headers = {
                'User-Agent': "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36"}

            req1 = urllib.request.Request(base_url, headers=headers)
            resp1 = urllib.request.urlopen(req1)
            content = str(resp1.read())
            l3 = content.find('/search?sa=X&amp;q=')
            l4 = content.find(';', l3 + 19)
            url_2 = content[l3 + 19:l4]
            return url_2
        except:
            return "Could not connect to Google Images endpoint"

    @staticmethod
    def build_url_parameters(config: ScraperConfig):
        lang_url = ''

        built_url = "&tbs="
        params = {'color': [config.color, COLOR_TABLE],
                  'size': [config.size, SIZE_TABLE],
                  'type': [config.type, TYPE_TABLE],
                  'time': [config.time, TIME_TABLE],
                  'aspect_ratio': [config.aspect_ratio, ASPECT_RATIO_TABLE],
                  'usage': [config.usage, LICENSE_TABLE]
                  }

        initial_param = True
        for key, value in params.items():
            selection = value[0]
            options = value[1]
            if selection is not None:
                ext_param = options[selection] if selection in options else None
                # counter will tell if it is first param added or not
                if ext_param is not None:
                    if initial_param:
                        # add it to the built url
                        built_url += ext_param
                        initial_param = False
                    else:
                        built_url += ',' + ext_param
        return built_url

    # building main search URL
    def build_search_url(self, search_term, params, config: ScraperConfig, similar_images):
        # parse params
        exact_terms = ' '.join(f'"{word}"' for word in config.exact_words.split(","))
        or_terms = '+'.join(config.any_words.split(","))
        not_terms = ' -'.join(config.exclude_words.split(","))

        # check the args and choose the URL
        if similar_images:
            keywordem = self.similar_images(similar_images)
            url = 'https://www.google.com/search?q=' + keywordem + '&espv=2&biw=1366&bih=667&site=webhp&source=lnms&tbm=isch'
        else:
            url = 'https://www.google.com/search?q=' + quote(
                search_term.encode(
                    'utf-8')) + '&espv=2&biw=1366&bih=667&site=webhp&source=lnms&tbm=isch' + '&as_epq=' + quote(
                exact_terms) + '&as_oq=' + quote(or_terms) + '&as_eq=' + quote(
                not_terms) + params

        return url

    # keywords from file

    @staticmethod
    def download_image(image_url, main_directory, dir_name, count, description=None, search=None):
        try:
            req = Request(image_url, headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1312.27 Safari/537.17"})
            try:
                timeout = 10
                response = urlopen(req, None, timeout)
                data = response.read()
                info = response.info()
                response.close()

                qmark = image_url.rfind('?')
                if qmark == -1:
                    qmark = len(image_url)
                slash = image_url.rfind('/', 0, qmark) + 1
                image_name = str(image_url[slash:qmark]).lower()
                image_name = os.path.splitext(image_name)[0]

                path = os.path.join(main_directory, dir_name)
                # Append the count, padded to 4 digits (0001, 0002, etc)
                path = os.path.join(path, '%04d.png' % count)
                try:
                    img = Image.open(BytesIO(data))
                    img.save(path, format='PNG', optimize=True, quality=95)
                    absolute_path = os.path.abspath(path)
                    if description:
                        description = clean_description(description, search)
                        with open(os.path.splitext(absolute_path)[0] + '.txt', 'w', encoding='utf-8') as f:
                            f.write(description)
                except Exception as e:
                    logger.warning("Could not load/save image: " + str(e))
                    traceback.print_exc()
                    download_status = 'fail'
                    download_message = str(e)
                    return_image_name = ''
                    absolute_path = ''
                    return download_status, download_message, return_image_name, absolute_path

                # return image name back to calling method to use it for thumbnail downloads
                download_status = 'success'
                download_message = "Completed Image ====> " + str(count) + "." + image_name
                return_image_name = str(count) + "." + image_name

            except Exception as e:
                download_status = 'fail'
                download_message = "BadStatusLine on an image...trying next one..." + " Error: " + str(e)
                return_image_name = ''
                absolute_path = ''

        except Exception as e:
            download_status = 'fail'
            download_message = "Exception on an image...trying next one..." + " Error: " + str(e)
            return_image_name = ''
            absolute_path = ''

        return download_status, download_message, return_image_name, absolute_path

    def _get_all_items(self, keyword, image_objects, main_directory, dir_name, limit, status_handler, secondary=False):
        items = []
        abs_path = []
        prompts = []
        error_count = 0
        i = 0
        count = 1

        with ThreadPoolExecutor(max_workers=MAX_IMAGE_THREADS) as executor:
            futures = {}
            while count < limit + 1 and i < len(image_objects):
                if status_handler.status.canceled:
                    logger.debug("User canceled")
                    break
                if len(image_objects) == 0:
                    print("no_links")
                    break
                else:
                    # format the item for readability
                    formatted = self.format_object(image_objects[i], keyword)
                    print("\nImage Metadata: " + str(formatted))
                    if formatted is None:
                        print("Invalid object.")
                        continue

                    # download the images
                    description = formatted["image_description"] if "image_description" in formatted else None
                    search = formatted['image_search_term']

                    future = executor.submit(
                        self.download_image,
                        formatted['image_link'],
                        main_directory,
                        dir_name,
                        count,
                        description,
                        search
                    )
                    futures[future] = (i, formatted)
                    i += 1
                    count += 1

            for future in as_completed(futures):
                i, formatted = futures[future]
                try:
                    download_status, download_message, return_image_name, absolute_path = future.result()
                except Exception as e:
                    logger.warning("Failed to download an image due to error: " + str(e))
                    download_status = 'fail'
                    download_message = str(e)
                    return_image_name = ''
                    absolute_path = ''
                    error_count += 1

                logger.debug(f"Status: {download_message}")

                if download_status == "success":
                    formatted['image_filename'] = return_image_name
                    items.append(formatted)
                    abs_path.append(absolute_path)
                    prompts.append(description)
                    status_items = {"images": [absolute_path], "prompts": prompts}
                    status_handler.update(items=status_items, send=False)
                    status_handler.step(1, description=f"Downloaded image {i + 1}/{limit}", secondary_bar=secondary)
                    status_handler.send()
                else:
                    status_handler.step(1, description=f"Exception downloading image {i + 1}/{limit}",
                                        secondary_bar=secondary)

        if count < limit:
            print("\n\nUnfortunately all " + str(
                limit) + " could not be downloaded because some images were not downloadable. " + str(
                count - 1) + " is all we got for this search filter!")
        return items, error_count, abs_path

    # Bulk Download
    def download(self, config: ScraperConfig, user: str = None):
        fh = FileHandler(user_name=user)
        sh = StatusHandler(user_name=user, target="scraper")
        user_dir = fh.user_dir
        paths = {}
        search_keyword = [str(item) for item in config.keywords.split('\n')]
        limit = config.limit
        main_directory = os.path.join(user_dir, "downloads")

        total_errors = 0
        i = 0

        total_images = len(search_keyword) * limit
        sh.start(total_images, "Downloading images")
        for keyword in search_keyword:
            if sh.status.canceled:
                break
            iteration = "\n" + "Item no.: " + str(i + 1) + " -->" + " Item name = " + keyword
            i += 1
            logger.debug(f"Item: {i + 1} --> {keyword}")
            print(iteration.encode('raw_unicode_escape').decode('utf-8'))
            print("Evaluating...")
            search_term = keyword

            dir_name = search_term + ('-' + config.color if config.color else '')
            out_dir = os.path.join(main_directory, dir_name)
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)

            params = self.build_url_parameters(config)  # building URL with params

            url = self.build_search_url(search_term, params, config, [])  # building main search url
            logger.debug(f"URL: {url}")
            target_dir = os.path.join(fh.user_dir, "chromedriver")
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)

            chromedriver = None
            if config.browser == 'chrome':
                chromedriver = download_chromedriver(target_dir)
                logger.debug("Chrome driver path: " + chromedriver)
            if limit < 101:
                images, tabs = self.download_page(url)  # download page
            else:
                images, tabs = self.download_extended_page(url, chromedriver, config.browser)
            sh.update("status", f"Downloading images for prompt: {keyword}")
            items, err_count, abs_path = self._get_all_items(keyword, images, main_directory, dir_name, limit, sh)
            paths[keyword] = abs_path

            # dumps into a json file
            logger.debug(f"Metadata: {items}")

            # Related images
            if config.related_images:
                sh.update(items={"status_2": "Downloading related images", "progress_2_total": len(tabs),
                                 "progress_2_current": 0})
                for key, value in tabs.items():
                    if sh.status.canceled:
                        break
                    final_search_term = (search_term + " - " + key)
                    print("\nNow Downloading - " + final_search_term)
                    if limit < 101:
                        images, _ = self.download_page(value)  # download page
                    else:
                        images, _ = self.download_extended_page(value, chromedriver, config.browser)
                    out_dir = os.path.join(main_directory, final_search_term)
                    if images is None:
                        continue
                    if not os.path.exists(out_dir):
                        os.makedirs(out_dir)
                    self._get_all_items(keyword, images, main_directory, search_term + " - " + key, limit, sh, True)

            i += 1
            total_errors = total_errors + err_count
            if total_errors:
                logger.warning(f"Total errors: {total_errors}")
        out_images = []
        for key in paths:
            out_images.extend(paths[key])
        sh.update("images", out_images)
        sh.end(f"Scraping complete, downloaded {total_images - total_errors} images")
        return paths, total_errors


def scrape_images(config: ScraperConfig, user):
    downloader = GoogleImagesDownloader()
    paths, errors = downloader.download(config, user)
    return {"paths": paths, "errors": errors}
