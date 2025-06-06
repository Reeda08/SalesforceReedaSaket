import logging
import time
import json
import os
import glob
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from Base import SalesforceBase  


class LeadCreate(SalesforceBase):
    def __init__(self, **kwargs):
        # Initialize base class first
        username = kwargs.get("username")
        password = kwargs.get("password")
        
        if not username or not password:
            raise ValueError("Username and password required")
        
        # Call parent constructor with all necessary parameters
        super().__init__(
            username=username,
            password=password,
            timeout=kwargs.get("timeout", 20),
            api_base=kwargs.get("api_base", "api.smartassistapp.in"),
            output_dir=kwargs.get("output_dir", "C:\\SAKET\\RPA\\Salesforce\\data")
        )
        
        # LeadCreate specific attributes
        self.prefix = kwargs.get("prefix", "default_tab1")
        self.api_url = kwargs.get("api_url", "https://api.smartassistapp.in/api/salesforce-dump/leads-data/new")
        self.failed_leads = set()
        
        logging.info("LeadCreate initialized successfully")

    def fetch_leads_from_api(self):
        """Fetch leads using inherited API method"""
        try:
            data = self.api_request("GET", "/api/RPA/leads-data/new")
            return data if data else None
        except Exception as e:
            logging.error(f"API fetch failed: {e}")
            return None

    def update_lead_status(self, lead_id, url):
        """Update lead status using inherited API method"""
        try:
            payload = {"lead_id": lead_id, "url": url}
            return self.api_request("PUT", "/api/salesforce-dump/leads/new/flag-inactive", payload)
        except Exception as e:
            logging.error(f"API update failed: {e}")
            return False

    def save_leads_data(self, data):
        """Save data using inherited method"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
        filename = f"{self.prefix}_{timestamp}"
        return self.save_to_file(data, filename)

    def get_latest_saved_data(self):
        """Get latest saved data from files"""
        try:
            files = glob.glob(os.path.join(self.output_dir, f'{self.prefix}_*.json'))
            if not files:
                return []

            latest = max(files, key=os.path.getmtime)
            with open(latest, 'r') as f:
                data = json.load(f)

            return [item for item in data if isinstance(data, list) and 'lead_id' in item] if isinstance(data, list) else []
        except Exception:
            return []

    def navigate_to_leads(self):
        """Navigate to Leads object using inherited method"""
        return self.navigate_to_object("Lead")

    def fill_mandatory_fields(self, data):
        """Fill mandatory fields for lead creation"""
        try:
            # Last Name (Required)
            lname = data.get('lname', '').strip() or 'Required'
            if not self.send_text((By.XPATH, "//label[text()='Last Name']/following-sibling::div//input"), lname):
                logging.error(f"Failed to fill Last Name for lead {data.get('lead_id')}")
                return False

            # First Name (Optional)
            fname = data.get('fname', '').strip()
            if fname:
                self.send_text((By.XPATH, "//label[text()='First Name']/following-sibling::div//input"), fname)

            # Email (Required)
            email = data.get('email', '').strip() or f"lead_{data.get('lead_id', 'unknown')}@example.com"
            if not self.send_text((By.XPATH, "//input[@name='Email' and @type='text']"), email):
                logging.error(f"Failed to fill Email for lead {data.get('lead_id')}")
                return False

            return True
        except Exception as e:
            logging.error(f"Error filling mandatory fields: {e}")
            return False

    def set_lead_status(self, status):
        """Set lead status using inherited dropdown method"""
        if status == 'Lost':
            return True
        
        status_map = {"Follow Up": "Follow Up", "New": "New", "Qualified": "Qualified", "Lost": "Lost"}
        if status not in status_map:
            return False
            
        dropdown_locator = (By.XPATH, "//button[@aria-label='Lead Status' and contains(@class, 'slds-combobox__input')]")
        return self.select_dropdown_option(dropdown_locator, status_map[status])

    def set_lead_source(self, source):
        """Set lead source using inherited dropdown method"""
        dropdown_locator = (By.XPATH, "//button[@aria-label='Lead Source' and contains(@class, 'slds-combobox__input')]")
        return self.select_dropdown_option(dropdown_locator, source)

    def set_enquiry_type(self, enquiry_type):
        """Set enquiry type using inherited dropdown method"""
        dropdown_locator = (By.XPATH, "//button[@aria-label='Enquiry Type' and contains(@class, 'slds-combobox__input')]")
        
        if enquiry_type == "(Generic) Purchase intent within 90 days":
            return self.select_dropdown_option(dropdown_locator, "Generic")
        elif enquiry_type == "KMI":
            return self.select_dropdown_option(dropdown_locator, "KMI")
        return True

    def set_purchase_type(self, purchase_type):
        """Set purchase type using inherited dropdown method"""
        if purchase_type in ['New Vehicle', 'Used Vehicle']:
            dropdown_locator = (By.XPATH, "//button[contains(@class, 'slds-combobox__input') and contains(@aria-label, 'Purchase Type')]")
            return self.select_dropdown_option(dropdown_locator, purchase_type)
        return True

    def set_brand_and_pmi(self, brand, pmi):
        """Set brand and PMI with complex interaction"""
        try:
            # Click on vehicle specification search
            brand_input_locator = (By.XPATH, "//input[@placeholder='Search Vehicle Specifications...']")
            if not self.click_element(brand_input_locator):
                return False

            # Enter brand text
            brand_text = "Land" if brand == "Land Rover" else ("Jag" if brand == "Jaguar" else "")
            if brand_text:
                self.send_text(brand_input_locator, brand_text, clear=False)

            # Click on custom icon
            if not self.click_element((By.XPATH, "//lightning-icon[@icon-name='custom:custom67']")):
                return False

            time.sleep(2)
            
            # Handle PMI selection
            pmi_locators = [
                (By.XPATH, '//lightning-base-combobox//input[@placeholder="Search Vehicle Specifications..."]'),
                (By.XPATH, "//input[@placeholder='Search Vehicle Specifications...']")
            ]

            for locator in pmi_locators:
                try:
                    if self.click_element(locator, 5):
                        if self.send_text(locator, pmi[:4], clear=False):
                            time.sleep(1)
                            option_locator = (By.XPATH, f"//lightning-base-combobox-item[normalize-space(.//span[contains(@class,'slds-listbox__option-text')])='{pmi}']")
                            return self.click_element(option_locator)
                except:
                    continue
            return False
        except Exception as e:
            logging.error(f"Error setting brand/PMI: {e}")
            return False

    def process_single_lead(self, data):
        """Process a single lead with all validations and steps"""
        lead_id = data.get('lead_id', '')
        
        try:
            # Validate required fields
            required_fields = ['lname', 'status', 'lead_source', 'enquiry_type', 'brand', 'PMI', 'lead_id']
            missing_fields = [field for field in required_fields if not data.get(field)]
            
            if missing_fields:
                logging.error(f"Missing required fields for lead {lead_id}: {missing_fields}")
                return False

            # Skip Jaguar brand as per business logic
            if data.get('brand') == 'Jaguar':
                logging.info(f"Skipping Jaguar lead {lead_id}")
                return True

            # Step 1: Navigate to Leads
            if not self.navigate_to_leads():
                logging.error(f"Failed to navigate to Leads for {lead_id}")
                return False

            # Step 2: Create new lead record
            if not self.create_new_record():
                logging.error(f"Failed to create new record for {lead_id}")
                return False

            # Step 3: Fill mandatory fields
            if not self.fill_mandatory_fields(data):
                logging.error(f"Failed to fill mandatory fields for {lead_id}")
                return False

            # Step 4: Set optional fields
            field_setters = [
                (self.set_lead_status, data.get('status')),
                (self.set_lead_source, data.get('lead_source')),
                (self.set_enquiry_type, data.get('enquiry_type')),
                (self.set_purchase_type, data.get('purchase_type'))
            ]

            for setter_method, value in field_setters:
                if value:
                    try:
                        setter_method(value)
                    except Exception as e:
                        logging.warning(f"Non-critical field setting failed for {lead_id}: {e}")

            # Step 5: Set Brand and PMI (Critical)
            if not self.set_brand_and_pmi(data.get('brand'), data.get('PMI')):
                logging.error(f"Failed to set brand/PMI for {lead_id}")
                return False

            # Step 6: Save the record
            if not self.save_record():
                logging.error(f"Failed to save record for {lead_id}")
                return False

            # Step 7: Update lead status via API
            current_url = self.get_current_url()
            self.update_lead_status(lead_id, current_url)
            
            logging.info(f"Successfully processed lead {lead_id}")
            return True

        except Exception as e:
            logging.error(f"Error processing lead {lead_id}: {e}")
            return False
        finally:
            # Cleanup - go back and refresh
            self.go_back()
            self.refresh_and_wait()

    def run_lead_creation_process(self):
        """Main process loop"""
        consecutive_failures = 0
        
        logging.info("Starting Lead Creation Process...")
        
        while True:
            try:
                # Fetch leads from API
                leads_data = self.fetch_leads_from_api()
                if not leads_data:
                    logging.info("No leads data received, waiting...")
                    time.sleep(30)
                    continue

                # Save data locally
                if self.save_leads_data(leads_data):
                    leads_list = self.get_latest_saved_data()
                else:
                    leads_list = [item for item in leads_data if 'lead_id' in item] if isinstance(leads_data, list) else []

                if not leads_list:
                    logging.info("No valid leads found, waiting...")
                    time.sleep(30)
                    continue

                # Process each lead
                success_count = 0
                
                for lead_data in leads_list:
                    lead_id = lead_data.get('lead_id', '')
                    
                    # Skip already failed leads
                    if lead_id in self.failed_leads:
                        continue

                    # Process the lead
                    if self.process_single_lead(lead_data):
                        success_count += 1
                        consecutive_failures = 0  # Reset failure counter on success
                    else:
                        self.failed_leads.add(lead_id)
                        consecutive_failures += 1
                        
                        # Handle too many consecutive failures
                        if consecutive_failures >= 5:
                            logging.error("Too many consecutive failures, pausing for recovery...")
                            time.sleep(60)
                            consecutive_failures = 0

                    # Small delay between leads
                    time.sleep(2)

                logging.info(f"Batch completed: {success_count}/{len(leads_list)} leads processed successfully")

            except KeyboardInterrupt:
                logging.info("Process interrupted by user")
                break
            except Exception as e:
                logging.error(f"Main loop error: {e}")
                consecutive_failures += 1
                time.sleep(10)

        # Cleanup
        self.close()
        logging.info("Lead Creation Process ended")


# Usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('lead_creation.log'),
            logging.StreamHandler()
        ]
    )
    
    try:
        # Initialize LeadCreate with SalesforceBase inheritance
        lead_creator = LeadCreate(
            username="preprod@ariantechsolutions.com",
            password="smartassist@ATS07",
            timeout=20,
            api_base="api.smartassistapp.in",
            output_dir="C:\\SAKET\\RPA\\Salesforce\\alljsonfile",
            prefix="default_tab1",
            api_url="https://api.smartassistapp.in/api/salesforce-dump/leads-data/new"
        )
        
        # Start the process
        lead_creator.run_lead_creation_process()
        
    except Exception as e:
        logging.error(f"Application error: {e}")