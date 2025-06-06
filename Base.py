import logging
import time
import json
import os
import ssl
import http.client
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class SalesforceBase:
    def __init__(self, username, password, **kwargs):
        self.username = username
        self.password = password
        self.timeout = kwargs.get("timeout", 20)
        self.api_base = kwargs.get("api_base", "api.smartassistapp.in")
        self.output_dir = kwargs.get("output_dir", "C:\\SAKET\\RPA\\Salesforce\\data")
        
        self._init_driver()
        self._login()
        
    def _init_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, self.timeout)
        
    def _login(self):
        self.driver.get("https://cxp--preprod.sandbox.lightning.force.com")
        self.wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(self.username)
        self.driver.find_element(By.ID, "password").send_keys(self.password)
        self.driver.find_element(By.ID, "Login").click()
        self.wait.until(EC.url_contains("lightning.force.com"))
        time.sleep(3)
        
    def click_element(self, locator, timeout=None):
        timeout = timeout or self.timeout
        for attempt in range(3):
            try:
                self._wait_page_ready()
                elem = self.wait.until(EC.element_to_be_clickable(locator))
                self._scroll_center(elem)
                
                for method in [self._standard_click, self._js_click, self._action_click]:
                    if method(elem):
                        return True
            except Exception:
                time.sleep(1)
        return False
        
    def send_text(self, locator, text, clear=True, timeout=None):
        timeout = timeout or self.timeout
        try:
            elem = WebDriverWait(self.driver, timeout).until(EC.visibility_of_element_located(locator))
            if clear: elem.clear()
            elem.send_keys(text)
            return True
        except:
            return False
            
    def select_dropdown_option(self, dropdown_locator, option_value, timeout=None):
        if not self.click_element(dropdown_locator, timeout):
            return False
        time.sleep(1)
        option_loc = (By.XPATH, f"//lightning-base-combobox-item[@data-value='{option_value}']")
        return self.click_element(option_loc, timeout)
        
    def navigate_to_object(self, obj_name):
        strategies = [
            self._nav_direct_link,
            self._nav_app_launcher, 
            self._nav_direct_url
        ]
        
        for strategy in strategies:
            if strategy(obj_name):
                return True
        return False
        
    def create_new_record(self):
        new_selectors = [
            "//a[@title='New' and contains(@class, 'forceActionLink')]/div[@title='New']",
            "//button[@title='New']",
            "//a[contains(@class, 'forceActionLink') and @title='New']"
        ]
        
        for selector in new_selectors:
            if self.click_element((By.XPATH, selector), 5):
                time.sleep(3)
                return True
        return False
        
    def save_record(self):
        save_selectors = [
            "//button[@name='SaveEdit']",
            "//li[@data-target-selection-name='sfdc:StandardButton.Lead.SaveEdit']//button[@name='SaveEdit']",
            "//button[text()='Save']"
        ]
        
        current_url = self.driver.current_url
        for selector in save_selectors:
            if self.click_element((By.XPATH, selector), 15):
                try:
                    self.wait.until(EC.url_changes(current_url))
                    time.sleep(2)
                    return True
                except:
                    continue
        return False
        
    def api_request(self, method, endpoint, data=None):
        try:
            context = ssl._create_unverified_context()
            conn = http.client.HTTPSConnection(self.api_base, context=context)
            
            headers = {"Content-Type": "application/json"} if data else {}
            body = json.dumps(data) if data else None
            
            conn.request(method, endpoint, body=body, headers=headers)
            response = conn.getresponse()
            
            if response.status == 200:
                return json.loads(response.read().decode()) if method == "GET" else True
            return None
        except Exception as e:
            logging.error(f"API error: {e}")
            return None
            
    def save_to_file(self, data, filename_prefix):
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(self.output_dir, f"{filename_prefix}_{timestamp}.json")
            
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            return True
        except:
            return False
            
    def get_current_url(self):
        return self.driver.current_url
        
    def refresh_and_wait(self):
        self.driver.refresh()
        time.sleep(3)
        
    def go_back(self):
        self.driver.back()
        time.sleep(2)
        
    def close(self):
        try:
            self.driver.quit()
        except:
            pass
            
    # Internal helper methods
    def _wait_page_ready(self):
        try:
            self.wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
            time.sleep(0.5)
        except:
            pass
            
    def _scroll_center(self, elem):
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
        time.sleep(0.3)
        
    def _standard_click(self, elem):
        try:
            elem.click()
            return True
        except:
            return False
            
    def _js_click(self, elem):
        try:
            self.driver.execute_script("arguments[0].click();", elem)
            return True
        except:
            return False
            
    def _action_click(self, elem):
        try:
            ActionChains(self.driver).move_to_element(elem).click().perform()
            return True
        except:
            return False
            
    def _nav_direct_link(self, obj_name):
        selectors = [
            f"//one-app-nav-bar-item-root[.//span[text()='{obj_name}']]//a",
            f"//a[@title='{obj_name}' and contains(@href, '/lightning/o/{obj_name}/home')]",
            f"//span[text()='{obj_name}']/ancestor::a[contains(@href, '/lightning/o/{obj_name}/home')]"
        ]
        
        for selector in selectors:
            if self.click_element((By.XPATH, selector)):
                return self._verify_object_page(obj_name)
        return False
        
    def _nav_app_launcher(self, obj_name):
        launcher_selectors = ["//button[@title='App Launcher']", "//div[@class='slds-icon-waffle']"]
        
        for launcher in launcher_selectors:
            if self.click_element((By.XPATH, launcher)):
                time.sleep(2)
                obj_selectors = [f"//a[@data-label='{obj_name}']", f"//span[text()='{obj_name}']/ancestor::a"]
                for selector in obj_selectors:
                    if self.click_element((By.XPATH, selector)):
                        return self._verify_object_page(obj_name)
        return False
        
    def _nav_direct_url(self, obj_name):
        try:
            current = self.driver.current_url
            base = current.split('/lightning')[0] if '/lightning' in current else current.split('.com')[0] + '.com'
            self.driver.get(f"{base}/lightning/o/{obj_name}/home")
            return self._verify_object_page(obj_name)
        except:
            return False
            
    def _verify_object_page(self, obj_name):
        verifiers = [f"//span[text()='{obj_name}']", f"//h1[contains(text(), '{obj_name}')]"]
        
        for verifier in verifiers:
            try:
                WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, verifier)))
                time.sleep(2)
                return True
            except:
                continue
        return obj_name in self.driver.current_url