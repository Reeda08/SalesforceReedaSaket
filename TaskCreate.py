import logging
import os
import ssl
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import time
import requests
import http.client
from datetime import datetime, timedelta
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
import threading
import subprocess
import socket
import traceback
import urllib3

logging.basicConfig(
    filename='Tasks.log',
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
        EC.element_to_be_clickable((By.XPATH,"//*[@id='password']"))
    ).send_keys(password)
    logging.info("Entered password.")

    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//*[@id='Login']"))
    ).click()
    logging.info("Clicked login button.")

    WebDriverWait(driver, 20).until(EC.url_to_be(selenium_url))
    time.sleep(5)
    logging.info("Successfully logged in.")
    time.sleep(10)
def fetch_data_from_api(api_url):
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
        # Try to find app launcher
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
        # Retry fetching API until non-empty data is received
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
        json_file_path = os.path.join(output_directory, "Tasks.json")
        with open(json_file_path, 'w') as json_file:
            json.dump(followups_data, json_file, indent=4)
        print(f"api data saved{json_file_path}")
        logging.info(f"API data saved to {json_file_path}")

        failed_followups = set()

        for entry in followups_data:
            try:
                lead_id_followup = entry.get('task_id', '')
                subject = entry.get('subject', '') 
                comments = entry.get('comments','')
                # comments=("saket tu paggal mota bhais sab hai")
                status_data = entry.get('status', '')
                
                
                print(f"Processing task for: {lead_id_followup}")

                # Navigate to CXP app (with retry logic)
                navigation_success = navigate_to_cxp_app(driver)
                if not navigation_success:
                    print("Failed to navigate to CXP app, refreshing and retrying...")
                    driver.refresh()
                    time.sleep(5)
                    navigation_success = navigate_to_cxp_app(driver)
                    if not navigation_success:
                        print("Still failed to navigate, skipping this task")
                        failed_followups.add(lead_id_followup)
                        continue

                time.sleep(5)
                print("code yaha tak pahucha ")

                try:
                    driver.switch_to.window(driver.window_handles[0])
                    url = "https://cxp--preprod.sandbox.my.site.com/CXP/s/lead/00QVc00000BwyEOMAZ/avadhesh-s-mishra"
                    driver.get(url)
                    print(f"Opened URL: {url}")
                    time.sleep(10)
                except Exception as e:
                    print("Error opening URL:", e)
                    failed_followups.add(lead_id_followup)
                    continue

                driver.execute_script("window.scrollBy(0, 800);")

                # Click New Task
                WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[@title='New Task' and contains(@class, 'forceActionLink')]"))
                ).click()
                time.sleep(5)

                # Click Next
                element = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='Next'] and contains(@class, 'slds-button_brand')]"))
                )
                element.click()
                time.sleep(5)

                # Enter Subject
                try:
                    subject_btn = WebDriverWait(driver, 15).until(
                        EC.element_to_be_clickable((By.XPATH, "//label[normalize-space(text())='Subject']/following::input[1]"))
                    )
                    subject_btn.clear()
                    subject_btn.send_keys(subject)
                    logging.info(f"Entered subject: {subject}")
                    time.sleep(2)
                except Exception as e:
                    print("Error entering subject:", e)
                    failed_followups.add(lead_id_followup)
                    continue

                driver.execute_script("window.scrollBy(0, 200);")

                # Enter Comments
                comments_xpath = "//span[normalize-space(text())='Comments']/following::textarea[1]"
                try:
                    comments_btn = WebDriverWait(driver, 20).until(
                        EC.element_to_be_clickable((By.XPATH, comments_xpath))
                    )
                    if comments_btn.is_displayed():
                        print("comments button is displayed")
                        comments_btn.clear()
                        comments_btn.send_keys(comments)
                        logging.info(f"Entered comment: {comments}")
                        print("comments entered")
                        time.sleep(3)
                    else:
                        print("comments button is not displayed")
                        failed_followups.add(lead_id_followup)
                        continue
                except Exception as e:
                    print("Error entering comments:", e)
                    failed_followups.add(lead_id_followup)
                    continue

                # Optimized Status Selection
                try:
                    print(f"Trying to select status: {status_data}")
                    driver.execute_script("window.scrollBy(0, 200);")
                    time.sleep(2)
                    
                    # Simplified status dropdown selection
                    status_btn = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//span[normalize-space(text())='Status']/following::a[@role='combobox'][1]"))
                    )
                    
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", status_btn)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", status_btn)
                    print("Status dropdown clicked")
                    time.sleep(3)
                    
                    # Select status option - using the working xpath
                    status_option = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, f"//span[contains(text(),'{status_data}')]"))
                    )
                    driver.execute_script("arguments[0].click();", status_option)
                    print(f"Successfully selected status: {status_data}")
                    logging.info(f"Selected status: {status_data}")
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"Status selection error: {str(e)}")
                    logging.error(f"Status selection error: {str(e)}")
                    failed_followups.add(lead_id_followup)
                    continue

                try:
                    # Step 1: Click on the Priority input box (anchor element acting like a dropdown)
                    priority_input = WebDriverWait(driver, 20).until(
                        EC.element_to_be_clickable((By.XPATH, "//span[normalize-space(text())='Priority']/following::a[@role='combobox' and contains(@class,'select')][1]"))
                    )
                    priority_input.click()
                    logging.info("Clicked on Priority input box")

                    time.sleep(2)  # Optional wait in case dropdown animation takes a moment

                    # Step 2: Click on the "High" option
                    high_option = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//a[@role='option' and normalize-space(text())='High']"))
                    )
                    high_option.click()
                    logging.info("Selected 'High' as priority")

                except Exception as e:
                    logging.warning(f"Failed to set priority to High: {e}")


                # Save Button Click - Using correct XPath from HTML structure
                try:
                    
                    print("yaha tak pahocha di pr atak q gaya")
                    # Correct XPath based on your HTML structure
                    save_btn = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "(//button[@title='Save' and contains(@class, 'uiButton--brand') and .//span[text()='Save']])[last()]"))
                    )
                    
                    if save_btn.is_displayed():
                        print("Save button is displayed")
                        save_btn.click()
                        
                except Exception as e:
                    print("Save button error:", str(e))
                    failed_followups.add(lead_id_followup)
                time.sleep(5)   
        
                # Handle toast message
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
                
                file_name = "TASKS.json"
                lead_data = {"task_id": lead_id_followup, "url": current_url}

                with open(file_name, 'w') as json_file:
                    json.dump(lead_data, json_file, indent=4)

                with open(file_name, 'r') as json_file:
                    payload = json.load(json_file)

                # Send PUT request
                try:
                    context = ssl._create_unverified_context()
                    conn = http.client.HTTPSConnection("api.smartassistapp.in", context=context)

                    payload_json = json.dumps(payload)
                    headers = {
                        "Content-Type": "application/json",
                        "Content-Length": str(len(payload_json))
                    }

                    conn.request("PUT", "/api/RPA/tasks/new/flag-inactive", body=payload_json, headers=headers)
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
                logging.error(f"Error processing task ID {entry.get('task_id')}: {e}")
                print(f"Error processing task ID {entry.get('task_id')}: {e}")
                failed_followups.add(lead_id_followup)
                continue

        print(f"Processing complete. Failed tasks: {failed_followups}")

    except Exception as e:
        logging.error(f"Critical error in process_emails: {e}")
        print(f"Critical error: {e}")

if __name__ == "__main__":
    api_url = "https://api.smartassistapp.in/api/RPA/tasks-data/new"
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