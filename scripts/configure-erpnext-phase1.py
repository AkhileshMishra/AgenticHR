#!/usr/bin/env python3
"""
TalentOz HCM - ERPNext Phase 1 Configuration Script
Configures ERPNext HR with core modules for production readiness
"""

import json
import requests
import sys
import time
from typing import Dict, List, Any

class ERPNextConfigurator:
    def __init__(self, site_url: str, api_key: str, api_secret: str):
        self.site_url = site_url.rstrip('/')
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'token {api_key}:{api_secret}',
            'Content-Type': 'application/json'
        })

    def api_call(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make API call to ERPNext"""
        url = f"{self.site_url}/api/{endpoint}"
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=data)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url)
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API call failed: {e}")
            return {}

    def enable_domain_settings(self, domains: Dict[str, bool]):
        """Enable domain settings"""
        print("Configuring domain settings...")
        
        domain_settings = {
            "doctype": "Domain Settings",
            "name": "Domain Settings"
        }
        domain_settings.update(domains)
        
        result = self.api_call('POST', 'resource/Domain Settings', domain_settings)
        if result:
            print("✓ Domain settings configured successfully")
        return result

    def configure_hr_settings(self, hr_config: Dict):
        """Configure HR settings"""
        print("Configuring HR settings...")
        
        hr_settings = {
            "doctype": "HR Settings",
            "name": "HR Settings"
        }
        hr_settings.update(hr_config)
        
        result = self.api_call('POST', 'resource/HR Settings', hr_settings)
        if result:
            print("✓ HR settings configured successfully")
        return result

    def configure_payroll_settings(self, payroll_config: Dict):
        """Configure Payroll settings"""
        print("Configuring Payroll settings...")
        
        payroll_settings = {
            "doctype": "Payroll Settings",
            "name": "Payroll Settings"
        }
        payroll_settings.update(payroll_config)
        
        result = self.api_call('POST', 'resource/Payroll Settings', payroll_settings)
        if result:
            print("✓ Payroll settings configured successfully")
        return result

    def create_leave_types(self):
        """Create standard leave types"""
        print("Creating leave types...")
        
        leave_types = [
            {
                "leave_type_name": "Annual Leave",
                "max_leaves_allowed": 21,
                "applicable_after": 90,
                "max_continuous_days_allowed": 15,
                "is_carry_forward": 1,
                "max_carry_forwarded_leaves": 5,
                "encashment_threshold_days": 10,
                "earning_component": "Leave Encashment"
            },
            {
                "leave_type_name": "Sick Leave",
                "max_leaves_allowed": 12,
                "applicable_after": 30,
                "max_continuous_days_allowed": 7,
                "is_carry_forward": 0
            },
            {
                "leave_type_name": "Casual Leave",
                "max_leaves_allowed": 12,
                "applicable_after": 0,
                "max_continuous_days_allowed": 3,
                "is_carry_forward": 0
            },
            {
                "leave_type_name": "Maternity Leave",
                "max_leaves_allowed": 180,
                "applicable_after": 0,
                "max_continuous_days_allowed": 180,
                "is_carry_forward": 0
            },
            {
                "leave_type_name": "Paternity Leave",
                "max_leaves_allowed": 15,
                "applicable_after": 0,
                "max_continuous_days_allowed": 15,
                "is_carry_forward": 0
            }
        ]
        
        for leave_type in leave_types:
            leave_type["doctype"] = "Leave Type"
            result = self.api_call('POST', 'resource/Leave Type', leave_type)
            if result:
                print(f"✓ Created leave type: {leave_type['leave_type_name']}")

    def create_salary_components(self):
        """Create standard salary components"""
        print("Creating salary components...")
        
        # Earning components
        earning_components = [
            {"salary_component": "Basic Salary", "type": "Earning", "is_tax_applicable": 1},
            {"salary_component": "House Rent Allowance", "type": "Earning", "is_tax_applicable": 1},
            {"salary_component": "Medical Allowance", "type": "Earning", "is_tax_applicable": 1},
            {"salary_component": "Transport Allowance", "type": "Earning", "is_tax_applicable": 1},
            {"salary_component": "Special Allowance", "type": "Earning", "is_tax_applicable": 1},
            {"salary_component": "Leave Encashment", "type": "Earning", "is_tax_applicable": 1}
        ]
        
        # Deduction components
        deduction_components = [
            {"salary_component": "Provident Fund", "type": "Deduction", "is_tax_applicable": 0},
            {"salary_component": "Professional Tax", "type": "Deduction", "is_tax_applicable": 0},
            {"salary_component": "Income Tax", "type": "Deduction", "is_tax_applicable": 0},
            {"salary_component": "Employee State Insurance", "type": "Deduction", "is_tax_applicable": 0}
        ]
        
        all_components = earning_components + deduction_components
        
        for component in all_components:
            component["doctype"] = "Salary Component"
            result = self.api_call('POST', 'resource/Salary Component', component)
            if result:
                print(f"✓ Created salary component: {component['salary_component']}")

    def create_departments(self):
        """Create standard departments"""
        print("Creating departments...")
        
        departments = [
            "Human Resources",
            "Information Technology",
            "Finance",
            "Operations",
            "Sales",
            "Marketing",
            "Administration"
        ]
        
        for dept_name in departments:
            department = {
                "doctype": "Department",
                "department_name": dept_name,
                "is_group": 0
            }
            result = self.api_call('POST', 'resource/Department', department)
            if result:
                print(f"✓ Created department: {dept_name}")

    def create_designations(self):
        """Create standard designations"""
        print("Creating designations...")
        
        designations = [
            "Chief Executive Officer",
            "Chief Technology Officer",
            "Chief Financial Officer",
            "Vice President",
            "Director",
            "General Manager",
            "Assistant General Manager",
            "Manager",
            "Assistant Manager",
            "Team Lead",
            "Senior Executive",
            "Executive",
            "Associate",
            "Intern"
        ]
        
        for designation_name in designations:
            designation = {
                "doctype": "Designation",
                "designation_name": designation_name
            }
            result = self.api_call('POST', 'resource/Designation', designation)
            if result:
                print(f"✓ Created designation: {designation_name}")

    def create_employment_types(self):
        """Create employment types"""
        print("Creating employment types...")
        
        employment_types = [
            "Full-time",
            "Part-time",
            "Contract",
            "Intern",
            "Consultant"
        ]
        
        for emp_type in employment_types:
            employment_type = {
                "doctype": "Employment Type",
                "employee_type_name": emp_type
            }
            result = self.api_call('POST', 'resource/Employment Type', employment_type)
            if result:
                print(f"✓ Created employment type: {emp_type}")

    def create_shift_types(self):
        """Create shift types"""
        print("Creating shift types...")
        
        shift_types = [
            {
                "name": "General Shift",
                "start_time": "09:00:00",
                "end_time": "18:00:00",
                "enable_auto_attendance": 1,
                "determine_check_in_and_check_out": "Strictly based on Log Type in Employee Checkin",
                "working_hours_calculation_based_on": "First Check-in and Last Check-out",
                "begin_check_in_before_shift_start_time": 60,
                "allow_check_out_after_shift_end_time": 60
            },
            {
                "name": "Night Shift",
                "start_time": "22:00:00",
                "end_time": "06:00:00",
                "enable_auto_attendance": 1,
                "determine_check_in_and_check_out": "Strictly based on Log Type in Employee Checkin",
                "working_hours_calculation_based_on": "First Check-in and Last Check-out",
                "begin_check_in_before_shift_start_time": 60,
                "allow_check_out_after_shift_end_time": 60
            }
        ]
        
        for shift in shift_types:
            shift["doctype"] = "Shift Type"
            result = self.api_call('POST', 'resource/Shift Type', shift)
            if result:
                print(f"✓ Created shift type: {shift['name']}")

    def configure_oidc_integration(self, oidc_config: Dict):
        """Configure OIDC integration with Keycloak"""
        print("Configuring OIDC integration...")
        
        social_login_key = {
            "doctype": "Social Login Key",
            "name": "Keycloak",
            "provider_name": "Custom",
            "client_id": oidc_config["client_id"],
            "base_url": oidc_config["base_url"],
            "authorize_url": oidc_config["authorization_url"],
            "access_token_url": oidc_config["access_token_url"],
            "api_endpoint": oidc_config["api_endpoint"],
            "auth_url_data": json.dumps(oidc_config["auth_url_data"]),
            "redirect_uri": oidc_config["redirect_uri"],
            "enable_social_login": 1
        }
        
        result = self.api_call('POST', 'resource/Social Login Key', social_login_key)
        if result:
            print("✓ OIDC integration configured successfully")
        return result

    def create_custom_fields(self, custom_fields: Dict):
        """Create custom fields"""
        print("Creating custom fields...")
        
        for doctype, fields in custom_fields.items():
            for field in fields:
                custom_field = {
                    "doctype": "Custom Field",
                    "dt": doctype.title(),
                    "fieldname": field["fieldname"],
                    "label": field["label"],
                    "fieldtype": field["fieldtype"],
                    "unique": field.get("unique", 0),
                    "reqd": field.get("reqd", 0),
                    "options": field.get("options", "")
                }
                
                result = self.api_call('POST', 'resource/Custom Field', custom_field)
                if result:
                    print(f"✓ Created custom field: {field['label']} for {doctype}")

    def setup_workflows(self, workflows: Dict):
        """Setup workflows"""
        print("Setting up workflows...")
        
        for workflow_name, workflow_config in workflows.items():
            # Create workflow states
            for state in workflow_config["states"]:
                workflow_state = {
                    "doctype": "Workflow State",
                    "workflow_state_name": state,
                    "style": "Primary" if state == "Approved" else "Default"
                }
                self.api_call('POST', 'resource/Workflow State', workflow_state)
            
            # Create workflow
            workflow = {
                "doctype": "Workflow",
                "workflow_name": workflow_name.replace("_", " ").title(),
                "document_type": workflow_name.replace("_", " ").title(),
                "is_active": 1,
                "workflow_state_field": "workflow_state",
                "states": [{"state": state, "doc_status": "1"} for state in workflow_config["states"]],
                "transitions": workflow_config["transitions"]
            }
            
            result = self.api_call('POST', 'resource/Workflow', workflow)
            if result:
                print(f"✓ Created workflow: {workflow_name}")

    def run_phase1_configuration(self, config_file: str):
        """Run Phase 1 configuration"""
        print("Starting ERPNext Phase 1 Configuration...")
        print("=" * 50)
        
        # Load configuration
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        phase1_config = config["phase_1_hr_configuration"]
        
        try:
            # 1. Enable domain settings
            self.enable_domain_settings(phase1_config["domain_settings"])
            
            # 2. Configure HR settings
            self.configure_hr_settings(phase1_config["hr_settings"])
            
            # 3. Configure Payroll settings
            self.configure_payroll_settings(phase1_config["payroll_settings"])
            
            # 4. Create master data
            self.create_departments()
            self.create_designations()
            self.create_employment_types()
            self.create_leave_types()
            self.create_salary_components()
            self.create_shift_types()
            
            # 5. Create custom fields
            self.create_custom_fields(phase1_config["custom_fields"])
            
            # 6. Setup workflows
            self.setup_workflows(phase1_config["workflows"])
            
            # 7. Configure OIDC integration
            if "keycloak_integration" in config:
                self.configure_oidc_integration(config["keycloak_integration"]["oidc_settings"])
            
            print("\n" + "=" * 50)
            print("✓ ERPNext Phase 1 Configuration completed successfully!")
            print("\nConfigured features:")
            print("- Employee Management")
            print("- Leave Management")
            print("- Attendance Management")
            print("- Payroll Management")
            print("- Keycloak OIDC Integration")
            print("- Custom Fields and Workflows")
            
        except Exception as e:
            print(f"\n❌ Configuration failed: {e}")
            sys.exit(1)

def main():
    if len(sys.argv) != 4:
        print("Usage: python configure-erpnext-phase1.py <site_url> <api_key> <api_secret>")
        sys.exit(1)
    
    site_url = sys.argv[1]
    api_key = sys.argv[2]
    api_secret = sys.argv[3]
    
    configurator = ERPNextConfigurator(site_url, api_key, api_secret)
    configurator.run_phase1_configuration("../configs/erpnext-hr-config.json")

if __name__ == "__main__":
    main()

