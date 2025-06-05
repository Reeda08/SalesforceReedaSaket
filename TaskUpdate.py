import logging
import os
import ssl
import json
import time
import http.client
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    ElementClickInterceptedException
)

logging.basicConfig(filename='event_execution_log.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

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
    time.sleep(20)

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
            time.sleep(10)
            return True
        else:
            print("cxp app is not displayed")
            return False

    except Exception as e:
        print(f"Error navigating to CXP app: {e}")
        return False

def process_events(api_url, output_directory, selenium_url, driver):
    try:
        print("Starting to process events...")
        
        logging.info("Fetching data from API.")
        context = ssl._create_unverified_context()
        conn = http.client.HTTPSConnection(api_url.replace("https://", "").split("/")[0], context=context)
        endpoint = "/" + "/".join(api_url.split("/")[3:])

        conn.request("GET", endpoint)
        response = conn.getresponse()

        if response.status == 200:
            events_data = json.loads(response.read().decode())
            logging.info(f"Fetched {len(events_data)} entries from API.")
        else:
            logging.error(f"Failed to fetch data with status code: {response.status}")
            return

        if not os.path.exists(output_directory):
            os.makedirs(output_directory)

        json_file_path = os.path.join(output_directory, f"events_data_{int(time.time())}.json")
        with open(json_file_path, 'w') as json_file:
            json.dump(events_data, json_file, indent=4)

        logging.info(f"API data saved to {json_file_path}")
        print(f"API data saved to {json_file_path}")

        noturladata = set()
        

    

        

        # ✅ Loop through events after CXP app is loaded
        for event in events_data:
            print(f"Processing event with task_id: {event.get('task_id', '')}")
            logging.info(f"Processing event: {event}")
            task_id = event.get('task_id', '')
            lead_email = event.get('lead_email', '').lower()
            subject = event.get('subject', '')  
            desired_status = event.get('status', '')
            comments=event.get('comments','')
            url = event.get('url', '')

            if not url :
                    print("missint the url proceeding with the next data")
                    noturladata.add(task_id)
                    continue

            print('Yaha tak pahocha')
            logging.warning(f"No URL in event. Using fallback for task_id: {task_id}")

            driver.switch_to.window(driver.window_handles[0])
            driver.get(url)
            print(f"Opened URL: {url}")
            time.sleep(10)

            driver.execute_script("window.scrollBy(0, 400);")

            try:
                # Click pencil/edit icon for Comments
                WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[@title='Edit Comments']"))
                ).click()
                print("Clicked edit pencil for Comments.")
                time.sleep(2)

                # Edit the comment field
                comment_field = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, "//textarea[contains(@class, 'textarea')]"))
                )
                comment_field.clear()
                comment_field.send_keys(comments)
                print(f"Entered comment: {comments}")
                time.sleep(1)

            except Exception as e:
                logging.error(f"Failed to update comment for task_id {task_id}: {e}")
                print(f"Failed to update comment for task_id {task_id}: {e}")

            try:
                driver.execute_script("window.scrollBy(0, 100);")
                print("ab scroll kiya hai aur status update karne wale hain")
                status_box = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[@role='combobox' and contains(@class, 'select')]"))
                )
                status_box.click()
                time.sleep(2)

                # Fetch the desired status from the event data
                desired_status = event.get("status", "").strip()
                print(f"Selecting status: {desired_status}")

                # Wait and click on the desired status option from dropdown
                status_option = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, f"//a[@role='option']//div[text()='{desired_status}']"))
                )
                status_option.click()
                time.sleep(2)
                print(f"Selected status: {desired_status}")
                time.sleep(2)
    

                # Save after status update
                # WebDriverWait(driver, 10).until(
                #     EC.element_to_be_clickable((By.XPATH, "//button[@name='SaveEdit' or @title='Save' or text()='Save']"))
                # ).click()
                # print("Clicked Save after status update.")
                # time.sleep(5)

            except Exception as e:
                logging.error(f"Failed to update status for task_id {task_id}: {e}")
                print(f"Failed to update status for task_id {task_id}: {e}")

            try:
                save_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        "//button[@title='Save' and contains(@class, 'forceActionButton')] | " +
                        "//button[.//span[normalize-space(text())='Save']] | " +
                        "//button[normalize-space()='Save' or .//span[normalize-space()='Save']] | " +
                        "//button[contains(@class,'uiButton') and contains(@class,'forceActionButton') and .//span[contains(text(),'Save')]]"
                    ))
                )
                save_button.click()
                print("✅ Save button clicked successfully.")
            except Exception as e:
                logging.error(f"❌ Save button click failed: {e}")
                print(f"❌ Save button click failed: {e}")

            current_url = driver.current_url
            print(f"Captured URL: {current_url}")
            time.sleep(10)

            file_name = "TASKS.json"
            lead_data = {"task_id": task_id, "url": current_url}

            with open(file_name, 'w') as json_file:
                json.dump(lead_data, json_file, indent=4)

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

                conn.request("PUT", "https://api.smartassistapp.in/api/RPA/tasks/updated/flag-inactive", body=payload_json, headers=headers)
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

                

            

             

            
                




    except Exception as e:
        logging.error(f"Exception in process_events: {e}")
        print(f"Exception in process_events: {e}")

if __name__ == "__main__":
    # Configuration
    api_url = "https://api.smartassistapp.in/api/RPA/tasks-data/updated"
    output_directory = "C:\\Users\\User\\Desktop\\SaleLead\\alljsonfile"
    selenium_url =  "https://cxp--preprod.sandbox.lightning.force.com/lightning/o/Campaign/list?filterName=__Recent" # Login page URL
    username = "preprod@ariantechsolutions.com"
    password = "smartassist@ATS07"

    # Initialize Chrome options
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-gpu')
    options.add_argument('--start-maximized')

    # Launch the browser
    driver = webdriver.Chrome(options=options)

    try:
        # Step 1: Login to Salesforce
        login_to_website(driver, selenium_url, username, password)

        navigate_to_cxp_app(driver)

        # Step 2: Process events from API and navigate CXP URLs
        process_events(api_url, output_directory, selenium_url, driver)

    except Exception as e:
        logging.error(f"Script execution failed with error: {e}")
        print(f"Something went wrong: {e}")

    finally:
        driver.quit()
        print("Browser closed.")
        





            
         
            

            
                
           
                
                

        
                

            
