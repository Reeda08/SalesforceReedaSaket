import logging
import os
import ssl
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
import time
import requests
import http.client
from selenium.webdriver.common.action_chains import ActionChains
from datetime import datetime, timedelta
import threading
import socket
import subprocess
import urllib3


logging.basicConfig(
    filename='Event.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def login_to_website(driver, selenium_url, username, password):
    """Log in to the website."""
    driver.get(selenium_url)

    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//*[@id='username']"))
    ).send_keys(username)
    logging.info("Entered username.")

    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//*[@id='password']"))
    ).send_keys(password)
    logging.info("Entered password.")

    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//*[@id='Login']"))
    ).click()
    logging.info("Clicked login button.")

    WebDriverWait(driver, 20).until(EC.url_to_be(selenium_url))
    time.sleep(5)
    logging.info("Successfully logged in.")

def fetch_data_from_api(api_url):
    print("Fetching data from API... ye yaha tk aaya mote")
    """Fetch data from API with SSL verification disabled."""
    try:
        response = requests.get(api_url, verify=False)
        response.raise_for_status()
        data = response.json()
        logging.info(f"Fetched {len(data)} entries from API.")
        return data
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch data from API: {e}")
        return []

def send_put_request(api_url, payload):
    """Send a PUT request to the API with SSL verification disabled."""
    try:
        response = requests.put(api_url, json=payload, verify=False)
        response.raise_for_status()
        logging.info(f"PUT request successful for payload: {payload}. Response: {response.status_code}")
        return response
    except requests.exceptions.RequestException as e:
        logging.error(f"PUT request failed for payload {payload}: {e}")
        return None

def navigate_to_cxp_app(driver):
    """Navigate to CXP app - separate function for reusability"""
    try:
        app_launcher_xpath = "//button[@title='App Launcher']"
        app_launcher = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, app_launcher_xpath))
        )
        app_launcher.click()
        time.sleep(5)
        print("app launcher clicked")

        cxp_app_xpath = "//p[text()='CXP Lightning']"
        cxp_element = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, cxp_app_xpath))
        )

        if cxp_element.is_displayed():
            print("cxp app is displayed")
            cxp_element.click()
            time.sleep(5)
            return True
        else:
            print("cxp app is not displayed")
            return False

    except Exception as e:
        print(f"Error navigating to CXP app: {e}")
        return False

login_done = False

def process_emails(api_url, output_directory, selenium_url, driver):
    try:
        followups_data = []
        while not followups_data:
            logging.info("Fetching data from API.")
            context = ssl._create_unverified_context()
            conn = http.client.HTTPSConnection(api_url.replace("https://", "").split("/")[0], context=context)
            endpoint = "/" + "/".join(api_url.split("/")[3:])
            conn.request("GET", endpoint)
            response = conn.getresponse()

            if response.status == 200:
                followups_data = json.loads(response.read().decode())
                if not followups_data:
                    logging.warning("Empty API response. Retrying in 15 seconds...")
                    time.sleep(15)
            else:
                logging.error(f"Failed to fetch data. HTTP {response.status}. Retrying in 15 seconds...")
                time.sleep(5)

        logging.info(f"Fetched {len(followups_data)} entries from API.")

        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
        json_file_path = os.path.join(output_directory, "Event.json")
        with open(json_file_path, 'w') as json_file:
            json.dump(followups_data, json_file, indent=4)
        print(f"api data saved{json_file_path}")
        logging.info(f"API data saved to {json_file_path}")

        failed_followups = set()

        for entry in followups_data:
            try:
                event_id_followup = entry.get('event_id', '')
                subject_data = entry.get('subject', '')
                status_data = entry.get('status', '')
                start_date_data = entry.get('start_date', '')
                brand_data = entry.get('brand', '')
                model_data = entry.get('PMI', '')
                # end_date_data = entry.get('end_date', '')
                description_data = entry.get('description', '')
                # start_time_data = entry.get('start_time', '')
                # end_time_data = entry.get('end_time', '')
                # VIN_data = entry.get('VIN', '')
                assigned_to_data = entry.get('assigned_to', '')
                lead_id_followup = entry.get('lead_id', '')
                cxp_lead_code = entry.get('cxp_lead_code', '')
                lead_url = entry.get('lead_url', '')

                if not lead_url or not lead_id_followup or not subject_data or not start_date_data:
                    print("Skipping event due to missing critical data (lead_email, event_id, subject, or start_date).")
                    continue

                print(f"Processing task for: {event_id_followup}")

                navigation_success = navigate_to_cxp_app(driver)
                if not navigation_success:
                    print("Failed to navigate to CXP app, refreshing and retrying...")
                    driver.refresh()
                    time.sleep(5)
                    navigation_success = navigate_to_cxp_app(driver)
                    if not navigation_success:
                        print("Still failed to navigate, skipping this task")
                        failed_followups.add(event_id_followup)
                        continue

                time.sleep(5)
                print("code yaha tak pahucha ")

                try:
                    driver.switch_to.window(driver.window_handles[0])
                    url = lead_url
                    driver.get(url)
                    print(f"Opened URL: {url}")
                    time.sleep(10)
                except Exception as e:
                    print("Error opening URL:", e)
                    failed_followups.add(event_id_followup)
                    continue

            except Exception as e:
                print(f"Error processing entry {entry}: {e}")
                failed_followups.add(event_id_followup)

            driver.execute_script("window.scrollBy(0, 800);")

            new_event_xpaths = [
                "//a[@title='New Event' and contains(@class, 'forceActionLink')]",
                "//a[contains(., 'New Event') and @role='button']",
                "//a[.//div[text()='New Event']]",
                "//div[@title='New Event']/parent::a",
                "//a[contains(@href, 'javascript:void') and contains(., 'New Event')]"
            ]

            clicked = False
            for xpath in new_event_xpaths:
                try:
                    element = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    element.click()
                    print(f"Clicked using XPath: {xpath}")
                    clicked = True
                    break
                except Exception as e:
                    print(f"XPath failed: {xpath} -- {str(e)}")

            if not clicked:
                print("❌ Failed to click on 'New Event' button using all known XPaths.")

            subject_value = subject_data

            xpaths = [
                "//label[contains(text(), 'Subject')]/following::input[1]",
                "//input[contains(@class, 'slds-combobox__input') and @role='combobox']",
                "//input[@type='text' and contains(@aria-haspopup, 'listbox')]"
            ]

            for xpath in xpaths:
                try:
                    subject_input = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    subject_input.click()
                    print(f"Clicked subject input using xpath: {xpath}")
                    time.sleep(1)

                    dropdown_option_xpath = f"//lightning-base-combobox-item//span[contains(text(), '{subject_value}')]"
                    dropdown_option = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, dropdown_option_xpath))
                    )
                    dropdown_option.click()
                    print(f"Selected subject value: {subject_value}")
                    break
                except Exception as e:
                    print(f"Failed with xpath: {xpath} – trying next... Error: {e}")

            start_date_value = start_date_data  # JSON se value

            start_date_xpaths = [
                "//legend[contains(text(), 'Start')]/following::input[@type='text'][1]",
                "//label[contains(text(), 'Start')]/following::input[@type='text']",
                "//input[@aria-describedby and contains(@class, 'slds-input') and @type='text']",
            ]

            for xpath in start_date_xpaths:
                start_date_input = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                start_date_input.click()
                start_date_input.clear()
                start_date_input.send_keys(start_date_value)
                print(f"Filled start date using xpath: {xpath} with value: {start_date_value}")

               

                try:
                    print("🚀 Trying to click Brand combobox with multiple XPaths...")

                    xpaths = [
                        "//div[@data-target-selection-name='sfdc:RecordField.Event.Brand__c']//a[@role='combobox']",
                        "//span[text()='Brand']/ancestor::div[contains(@class, 'slds-form-element')]/descendant::a[@role='combobox']",
                        "//span[text()='Brand']/following::a[@role='combobox'][1]",
                        "(//a[@role='combobox' and contains(@class, 'select')])[last()]"
                    ]

                    brand_value = brand_data.strip()  # JSON se value

                    combobox_element = None
                    for i, xpath in enumerate(xpaths):
                        try:
                            print(f"🔍 Trying XPath {i+1}: {xpath}")
                            elem = WebDriverWait(driver, 5).until(
                                EC.element_to_be_clickable((By.XPATH, xpath))
                            )
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                            time.sleep(1.5)

                            if elem.is_displayed() and elem.is_enabled():
                                elem.click()
                                print(f"✅ Brand combobox clicked using XPath {i+1}")
                                logging.info(f"✅ Brand combobox clicked using XPath {i+1}: {xpath}")
                                combobox_element = elem
                                break
                        except Exception as e:
                            print(f"❌ XPath {i+1} failed: {e}")
                            driver.execute_script("window.scrollBy(0, 250);")
                            time.sleep(1.5)
                    else:
                        raise Exception("❌ Brand combobox not found/clicked after all XPaths.")

                    if combobox_element:
                        # Dropdown options ka xpath - ye depend karta hai UI pe, example de raha hu:
                        option_xpath = f"//a[@role='option' and @title='{brand_value}']"

                        # Wait for dropdown to appear and option to be clickable
                        option_element = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, option_xpath))
                        )
                        time.sleep(2)
                        option_element.click()
                        print(f"✅ Brand option '{brand_value}' selected.")

                except Exception as final_e:
                    logging.error(f"🔥 Brand selection failed: {final_e}")
                    print(f"🔥 Brand selection failed: {final_e}")

                try:
                    print("🚀 Trying to click Model combobox with multiple XPaths...")

                    xpaths = [
                        "//div[@data-target-selection-name='sfdc:RecordField.Event.Model__c']//a[@role='combobox']",
                        "//span[text()='Model']/ancestor::div[contains(@class, 'slds-form-element')]/descendant::a[@role='combobox']",
                        "//span[text()='Model']/following::a[@role='combobox'][1]",
                        "(//a[@role='combobox' and contains(@class, 'select')])[last()]"
                    ]

                    model_value = model_data.strip()  # JSON se value

                    combobox_element = None
                    for i, xpath in enumerate(xpaths):
                        try:
                            print(f"🔍 Trying XPath {i+1}: {xpath}")
                            elem = WebDriverWait(driver, 5).until(
                                EC.element_to_be_clickable((By.XPATH, xpath))
                            )
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                            time.sleep(1.5)

                            if elem.is_displayed() and elem.is_enabled():
                                elem.click()
                                print(f"✅ Model combobox clicked using XPath {i+1}")
                                logging.info(f"✅ Model combobox clicked using XPath {i+1}: {xpath}")
                                combobox_element = elem
                                break
                        except Exception as e:
                            print(f"❌ XPath {i+1} failed: {e}")
                            driver.execute_script("window.scrollBy(0, 250);")
                            time.sleep(1.5)
                    else:
                        raise Exception("❌ Model combobox not found/clicked after all XPaths.")

                    if combobox_element:
                        # Dropdown option XPath for model, assuming 'title' attribute has model name
                        option_xpath = f"//a[@role='option' and @title='{model_value}']"

                        print(f"🔍 Waiting for dropdown option: {option_xpath}")
                        option_element = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, option_xpath))
                        )
                        driver.execute_script("arguments[0].scrollIntoView(true);", option_element)
                        time.sleep(0.5)
                        option_element.click()
                        print(f"✅ Model option '{model_value}' selected.")

                except Exception as final_e:
                    logging.error(f"🔥 Model selection failed: {final_e}")
                    print(f"🔥 Model selection failed: {final_e}")
                try:
                    print("🚀 Trying to scroll to and fill Description field...")

                    # Scroll karne ke liye description label element ka xpath (jo label hai uske basis pe scroll karna)
                    description_label_xpath = "//span[text()='Description']"

                    # Description textarea ka xpath
                    description_textarea_xpath = "//textarea[@role='textbox' and contains(@class, 'uiInputTextArea')]"

                    # Scroll to Description label tak
                    description_label_elem = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, description_label_xpath))
                    )
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", description_label_elem)
                    time.sleep(1)  # thoda wait kare page scroll hone ke liye

                    # Textarea element locate karo
                    description_textarea_elem = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, description_textarea_xpath))
                    )

                    # Click karo textarea pe taaki focus mile
                    description_textarea_elem.click()
                    time.sleep(0.5)

                    # JSON ya dict se jo comment aayega usko yahan dalna hai
                    description_comment = description_data.strip()  # assume description_data me tumhara comment hai

                    # Textarea clear karo agar pehle se kuch ho to
                    description_textarea_elem.clear()
                    time.sleep(0.3)

                    # Naya comment bhejo
                    description_textarea_elem.send_keys(description_comment)
                    print(f"✅ Description field filled with comment: {description_comment}")

                except Exception as e:
                    print(f"🔥 Failed to fill Description field: {e}")
                    logging.error(f"Failed to fill Description field: {e}")
                
                try:
                    
                    
                    # Correct XPath based on your HTML structure
                    save_btn = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "(//button[@title='Save' and contains(@class, 'uiButton--brand') and .//span[text()='Save']])[last()]"))
                    )
                    
                    if save_btn.is_displayed():
                        print("Save button is displayed")
                        save_btn.click()
                        
                except Exception as e:
                    print("Save button error:", str(e))
                    
                time.sleep(5)   
                       
                try:
                    toast_element = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//div[contains(@class,'forceToastMessage')]//a[contains(@class, 'forceActionLink')]"))
                    )
                    if toast_element.is_displayed():
                        print("Toast element is displayed")
                        toast_element.click()
                    else:
                        print("Toast element not found")
                except Exception as e:
                    print("Toast message handling:", e)
                    time.sleep(5)

                # Capture URL and send PUT request
                current_url = driver.current_url
                print(f"Captured URL: {current_url}")

                file_name = "EventUpdate.json"
                event_data = {"event_id": event_id_followup, "url": current_url}

                with open(file_name, 'w') as json_file:
                    json.dump(event_data, json_file, indent=4)

                with open(file_name, 'r') as json_file:
                    payload = json.load(json_file)

                try:
                    context = ssl._create_unverified_context()
                    conn = http.client.HTTPSConnection("api.smartassistapp.in", context=context)

                    payload_json = json.dumps(payload)
                    headers = {
                        "Content-Type": "application/json",
                        "Content-Length": str(len(payload_json))
                    }

                    conn.request("PUT", "/api/RPA/events/new/flag-inactive", body=payload_json, headers=headers)
                    response = conn.getresponse()

                    if response.status == 200:
                        print("Successfully updated the lead data!")
                        data = response.read().decode()
                        logging.info(f"PUT Response: {data}")
                    else:
                        print(f"Failed to update lead data. HTTP {response.status}")
                        logging.error(f"PUT Error Response: {response.read().decode()}")
                except Exception as e:
                    logging.error(f"PUT request error: {e}")
                    print(f"PUT request error: {e}")

                # Return to main page for next iteration
                try:
                    driver.get(selenium_url)  # Go back to main page instead of using back()
                    time.sleep(5)
                    print("Returned to main page for next task")
                except Exception as e:
                    print(f"Error returning to main page: {e}")

                except Exception as e:
                    logging.error(f"Error processing task ID {entry.get('event_id')}: {e}")
                    print(f"Error processing task ID {entry.get('event_id')}: {e}")
                    failed_followups.add(event_id_followup)
                    continue

        print(f"Processing complete. Failed tasks: {failed_followups}")
               

                       

                        


                

                        
                
    except Exception as e:
        logging.error(f"Error in process_emails: {e}")
        print(f"Error in process_emails: {e}")
                
             

if __name__ == "__main__":
    api_url = "https://api.smartassistapp.in/api/RPA/events-data/new"
    output_directory = "C:\\Users\\User\\Desktop\\SaleLead\\alljsonfile"
    selenium_url = "https://cxp--preprod.sandbox.lightning.force.com/lightning/o/Campaign/list?filterName=__Recent"
    username = "preprod@ariantechsolutions.com"
    password = "smartassist@ATS07"

    options = webdriver.ChromeOptions()
    options.add_argument('--disable-gpu')
    options.add_argument('--start-maximized')

    driver = webdriver.Chrome(options=options)

    login_to_website(driver, selenium_url, username, password)
    process_emails(api_url, output_directory, selenium_url, driver)
                

                    



            

            

               


            
                        

