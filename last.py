import logging
import os
import ssl
import json
import time
import traceback
import http.client
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import *
from selenium.webdriver.common.keys import Keys

logging.basicConfig(filename='event_execution_log.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def login_to_website(driver, selenium_url, username, password):
    driver.get(selenium_url)
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "username"))).send_keys(username)
    logging.info("Username entered.")
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "password"))).send_keys(password)
    logging.info("Password entered.")
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "Login"))).click()
    logging.info("Login button clicked.")
    time.sleep(20)

def navigate_to_cxp_app(driver):
    try:
        app_launcher_xpath = "//button[@title='App Launcher']"
        WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, app_launcher_xpath))).click()
        time.sleep(5)
        cxp_app_xpath = "//p[text()='CXP Lightning']"
        cxp_element = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, cxp_app_xpath)))
        cxp_element.click()
        time.sleep(10)
        print("CXP App khul gaya.")
        return True
    except Exception as e:
        print(f"Error navigating to CXP app: {e}")
        return False

def process_events(api_url, output_directory, selenium_url, driver):

    try: 
            
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
        for event in events_data:
            print(f"Processing event with task_id: {event.get('event_id', '')}")
            logging.info(f"Processing event: {event}")
            event_id = event.get('event_id', '')
            # desired_status = event.get('status', '')
            # comments = event.get('comments', '')
            subject_value = event.get('subject', '').strip()  # example: 'Test Subject'
            start_date_value = event.get('start_date', '').strip()  # example: '2025-06-10'
            start_time_value =  event.get('start_time', '').strip()  # example: '2025-06-10 10:00 AM'
            end_date_value = event.get('end_date', '').strip()  # example: '11-06-2025
            end_time_value = event.get("end_time", "").strip()  # e.g., "19:00"
            test_drive_status = event.get("status", "").strip()  # e.g., "In Progress"
            comment_text = event.get("description", "").strip()
            task_id = event.get('task_id', '')
            lead_url=event.get('lead_url','')
            url = event.get('url', '')


            if not url :
                    print("missint the url proceeding with the next data")
                    noturladata.add(event_id)
                    continue
                    
                    

            print('Yaha tak pahocha')
            logging.warning(f"No URL in event. Using fallback for task_id: {event_id}")
                    
            driver.switch_to.window(driver.window_handles[0])
            driver.get(url)
            print(f"{event_id}: Opened test event page.")
            print(f"URL: {url}")
            time.sleep(8)

            driver.execute_script("window.scrollBy(0, 100);")
            print(f"{event_id}: Page scrolled down.")
            time.sleep(5)

        
            try:
                # STEP 1: Click pencil icon near "Subject"
                subject_edit_icon_xpath = (
                    "//span[text()='Subject']/ancestor::div[contains(@class,'slds-form-element')]"
                    "/following-sibling::div//button[contains(@title,'Edit Subject')]"
                )

                edit_button = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, subject_edit_icon_xpath))
                )
                edit_button.click()
                print("✅ Pencil icon (Edit Subject) clicked.")
                time.sleep(2)

                subject_input = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//label[contains(text(), 'Subject')]/following::input[@role='combobox'][1]")
                    )
                )
                # Re-fetch input after click
                subject_input.click()
                time.sleep(1)

                

                subject_input.send_keys(Keys.CONTROL + "a", Keys.DELETE)
                subject_input.send_keys(subject_value)

                option_xpath = f"//span[@title='{subject_value}']"
                try:
                    dropdown_option = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, option_xpath))
                    )
                    dropdown_option.click()
                    print(f"✅ Dropdown option '{subject_value}' clicked.")
                except Exception as e:
                    print(f"⚠️ Dropdown click threw exception, but ignoring: {e}")

            
            except Exception as e:
                print(f"❌ Error editing Subject: {e}")
                traceback.print_exc()
                return False      

            try:
                start_date_value = event.get("start_date", "").strip()

                # Wait for and scroll to input
                start_date_input = WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//legend[text()='Start']/following::label[text()='Date']/following::input[1]")
                    )
                )
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", start_date_input)
                time.sleep(1)

                # Focus and clear properly using event triggers
                driver.execute_script("""
                    arguments[0].focus();
                    arguments[0].value = '';
                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                """, start_date_input)
                print("✅ Start Date cleared via JS with events.")

                start_date_input.send_keys(start_date_value)
                print(f"✅ Start Date entered: {start_date_value}")
                time.sleep(2)

            except Exception as e:
                print(f"❌ Error updating Start Date: {e}")
                traceback.print_exc()

            try:
                # start_time_value = event.get("start_time", "").strip()  # e.g., "10:00 AM"

                # Wait for Start Time input
                start_time_input = WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//legend[text()='Start']/following::label[text()='Time']/following::input[1]")
                    )
                )

                # Scroll into view
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", start_time_input)
                time.sleep(1)

                # Clear and trigger events properly
                driver.execute_script("""
                    arguments[0].focus();
                    arguments[0].value = '';
                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                """, start_time_input)
                print("✅ Start Time cleared via JS with events.")

                # Send new time value
                start_time_input.send_keys(start_time_value)
                print(f"✅ Start Time entered: {start_time_value}")
                time.sleep(2)

            except Exception as e:
                print(f"❌ Error updating Start Time: {e}")
                traceback.print_exc()
            
            try:
                

                # Wait for End Date input
                end_date_input = WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//legend[text()='End']/following::label[text()='Date']/following::input[1]")
                    )
                )

                # Scroll into view
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", end_date_input)
                time.sleep(1)

                # Clear the field using both key and JS fallback
                end_date_input.click()
                time.sleep(0.5)
                end_date_input.send_keys(Keys.CONTROL, 'a')
                end_date_input.send_keys(Keys.BACKSPACE)
                time.sleep(0.5)

                driver.execute_script("""
                    arguments[0].value = '';
                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                """, end_date_input)
                print("✅ End Date cleared via JS and keyboard.")

                # Set new value
                end_date_input.send_keys(end_date_value)
                print(f"✅ End Date entered: {end_date_value}")
                time.sleep(2)

            except Exception as e:
                print(f"❌ Error updating End Date: {e}")
                traceback.print_exc()

            




            try:
                end_time_value = event.get("end_time", "").strip()  # e.g., "19:00"

                # Wait for End Time input
                end_time_input = WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//legend[text()='End']/following::label[text()='Time']/following::input[@role='combobox'][1]")
                    )
                )

                # Scroll into view
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", end_time_input)
                time.sleep(1)

                # Click + clear with keyboard
                end_time_input.click()
                time.sleep(0.5)
                end_time_input.send_keys(Keys.CONTROL, 'a')
                end_time_input.send_keys(Keys.BACKSPACE)

                # JS clear + event fire
                driver.execute_script("""
                    arguments[0].value = '';
                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                """, end_time_input)
                print("✅ End Time cleared via JS and keyboard.")

                # Send new End Time
                end_time_input.send_keys(end_time_value)
                print(f"✅ End Time entered: {end_time_value}")
                time.sleep(2)

            except Exception as e:
                print(f"❌ Error updating End Time: {e}")
                traceback.print_exc()

            try:
                

                # Click the Test Drive Status dropdown
                dropdown_button = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//span[text()='Test Drive Status']/following::a[@role='combobox'][1]")
                    )
                )
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", dropdown_button)
                time.sleep(1)
                dropdown_button.click()
                print("✅ Test Drive Status dropdown opened.")

                # Wait and click the desired status
                status_option_xpath = f"//a[@role='option' and text()='{test_drive_status}']"
                option_element = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, status_option_xpath))
                )
                option_element.click()
                print(f"✅ Test Drive Status selected: {test_drive_status}")
                time.sleep(2)

            except Exception as e:
                print(f"❌ Error setting Test Drive Status: {e}")
                traceback.print_exc()

            try:
                
                # Wait and locate Description (comments) textarea
                description_box = WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//span[text()='Description']/following::textarea[1]")
                    )
                )

                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});",description_box)
                time.sleep(1)

                # Clear the textarea using JS + Keyboard
                description_box.click()
                time.sleep(0.5)
                description_box.send_keys(Keys.CONTROL, 'a')
                description_box.send_keys(Keys.BACKSPACE)
                time.sleep(0.5)

                # Optional JS clear (safe side)
                driver.execute_script("""
                    arguments[0].value = '';
                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                """, description_box)

                # Type comment
                description_box.send_keys(comment_text)
                print(f"✅ Comment/Description entered: {comment_text}")
                time.sleep(2)

            except Exception as e:
                print(f"❌ Error entering comment/description: {e}")
                traceback.print_exc()

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

                file_name = "EventUpdate.json"
                event_data = {"event_id": event_id, "url": current_url}

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

                    conn.request("PUT", "https://api.smartassistapp.in/api/RPA/events/updated/flag-inactive", body=payload_json, headers=headers)
                    response = conn.getresponse()

                    if response.status == 200:
                        print("Successfully updated the event data!")
                        data = response.read().decode()
                        logging.info(f"PUT Response: {data}")
                    else:
                        print(f"Failed to update lead data. HTTP {response.status}")
                        logging.error(f"PUT Error Response: {response.read().decode()}")
                except Exception as e:
                    logging.error(f"PUT request error: {e}")
                    print(f"PUT request error: {e}")

    except Exception as e:
        logging.error(f"Error processing events: {e}")
        print(f"Error processing events: {e}")
        traceback.print_exc()

            


            

                

if __name__ == "__main__":
    # Configuration
    api_url = "https://api.smartassistapp.in/api/RPA/events-data/updated"
    output_directory = "C:\\Users\\User\\Desktop\\SaleLead\\alljsonfile"
    selenium_url =  "https://cxp--preprod.sandbox.lightning.force.com/lightning/o/Campaign/list?filterName=__Recent" # Login page URL
    username = "preprod@ariantechsolutions.com"
    password = "SmartAssist@ATS07"

    # Initialize Chrome options
    options = webdriver.ChromeOptions()
    # options.add_argument(r'--user-data-dir=C:\Users\User\ChromeProfile')
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

    
        



        

        
            

