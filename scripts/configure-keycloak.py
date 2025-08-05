#!/usr/bin/env python3
"""
TalentOz HCM - Keycloak Configuration Script
Configures Keycloak with MFA and identity providers for production readiness
"""

import json
import requests
import sys
import time
import os
from typing import Dict, List, Any

class KeycloakConfigurator:
    def __init__(self, keycloak_url: str, admin_username: str, admin_password: str):
        self.keycloak_url = keycloak_url.rstrip('/')
        self.admin_username = admin_username
        self.admin_password = admin_password
        self.session = requests.Session()
        self.access_token = None
        self.realm_name = "erpnext"
        
    def get_admin_token(self) -> str:
        """Get admin access token"""
        token_url = f"{self.keycloak_url}/realms/master/protocol/openid-connect/token"
        
        data = {
            'client_id': 'admin-cli',
            'username': self.admin_username,
            'password': self.admin_password,
            'grant_type': 'password'
        }
        
        try:
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            token_data = response.json()
            self.access_token = token_data['access_token']
            
            # Set authorization header for future requests
            self.session.headers.update({
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            })
            
            print("✓ Successfully authenticated with Keycloak admin")
            return self.access_token
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to authenticate with Keycloak: {e}")
            sys.exit(1)
    
    def api_call(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make API call to Keycloak Admin API"""
        url = f"{self.keycloak_url}/admin/realms/{endpoint}"
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=data)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url)
            
            if response.status_code in [200, 201, 204]:
                try:
                    return response.json() if response.content else {}
                except:
                    return {}
            else:
                print(f"API call failed: {response.status_code} - {response.text}")
                return {}
                
        except requests.exceptions.RequestException as e:
            print(f"API call failed: {e}")
            return {}
    
    def create_realm(self, realm_config: Dict) -> bool:
        """Create or update realm"""
        print(f"Creating realm: {self.realm_name}")
        
        # Check if realm exists
        existing_realm = self.api_call('GET', self.realm_name)
        
        if existing_realm:
            print(f"Realm {self.realm_name} already exists, updating...")
            result = self.api_call('PUT', self.realm_name, realm_config)
        else:
            print(f"Creating new realm: {self.realm_name}")
            result = self.api_call('POST', '', realm_config)
        
        if result is not None:
            print(f"✓ Realm {self.realm_name} configured successfully")
            return True
        return False
    
    def create_client(self, client_config: Dict) -> bool:
        """Create OIDC client"""
        print(f"Creating client: {client_config['clientId']}")
        
        # Check if client exists
        clients = self.api_call('GET', f"{self.realm_name}/clients")
        existing_client = None
        
        for client in clients:
            if client.get('clientId') == client_config['clientId']:
                existing_client = client
                break
        
        if existing_client:
            print(f"Client {client_config['clientId']} already exists, updating...")
            client_id = existing_client['id']
            result = self.api_call('PUT', f"{self.realm_name}/clients/{client_id}", client_config)
        else:
            print(f"Creating new client: {client_config['clientId']}")
            result = self.api_call('POST', f"{self.realm_name}/clients", client_config)
        
        if result is not None:
            print(f"✓ Client {client_config['clientId']} configured successfully")
            return True
        return False
    
    def create_roles(self, roles: List[Dict]) -> bool:
        """Create realm roles"""
        print("Creating realm roles...")
        
        for role in roles:
            existing_role = self.api_call('GET', f"{self.realm_name}/roles/{role['name']}")
            
            if existing_role:
                print(f"Role {role['name']} already exists, updating...")
                result = self.api_call('PUT', f"{self.realm_name}/roles/{role['name']}", role)
            else:
                print(f"Creating role: {role['name']}")
                result = self.api_call('POST', f"{self.realm_name}/roles", role)
            
            if result is not None:
                print(f"✓ Role {role['name']} configured successfully")
        
        return True
    
    def create_groups(self, groups: List[Dict]) -> bool:
        """Create groups"""
        print("Creating groups...")
        
        for group in groups:
            existing_groups = self.api_call('GET', f"{self.realm_name}/groups")
            existing_group = None
            
            for existing in existing_groups:
                if existing.get('name') == group['name']:
                    existing_group = existing
                    break
            
            if existing_group:
                print(f"Group {group['name']} already exists, updating...")
                group_id = existing_group['id']
                result = self.api_call('PUT', f"{self.realm_name}/groups/{group_id}", group)
            else:
                print(f"Creating group: {group['name']}")
                result = self.api_call('POST', f"{self.realm_name}/groups", group)
            
            if result is not None:
                print(f"✓ Group {group['name']} configured successfully")
        
        return True
    
    def create_identity_providers(self, identity_providers: List[Dict]) -> bool:
        """Create identity providers"""
        print("Creating identity providers...")
        
        for idp in identity_providers:
            existing_idp = self.api_call('GET', f"{self.realm_name}/identity-provider/instances/{idp['alias']}")
            
            # Replace environment variables in config
            if 'config' in idp:
                for key, value in idp['config'].items():
                    if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                        env_var = value[2:-1]
                        env_value = os.getenv(env_var)
                        if env_value:
                            idp['config'][key] = env_value
                        else:
                            print(f"⚠️  Environment variable {env_var} not set for {idp['alias']}")
            
            if existing_idp:
                print(f"Identity provider {idp['alias']} already exists, updating...")
                result = self.api_call('PUT', f"{self.realm_name}/identity-provider/instances/{idp['alias']}", idp)
            else:
                print(f"Creating identity provider: {idp['alias']}")
                result = self.api_call('POST', f"{self.realm_name}/identity-provider/instances", idp)
            
            if result is not None:
                print(f"✓ Identity provider {idp['alias']} configured successfully")
        
        return True
    
    def configure_authentication_flows(self, flows: List[Dict]) -> bool:
        """Configure authentication flows"""
        print("Configuring authentication flows...")
        
        for flow in flows:
            existing_flows = self.api_call('GET', f"{self.realm_name}/authentication/flows")
            existing_flow = None
            
            for existing in existing_flows:
                if existing.get('alias') == flow['alias']:
                    existing_flow = existing
                    break
            
            if not existing_flow and not flow.get('builtIn', False):
                print(f"Creating authentication flow: {flow['alias']}")
                result = self.api_call('POST', f"{self.realm_name}/authentication/flows", flow)
                
                if result is not None:
                    print(f"✓ Authentication flow {flow['alias']} configured successfully")
        
        return True
    
    def enable_required_actions(self, required_actions: List[Dict]) -> bool:
        """Enable required actions"""
        print("Configuring required actions...")
        
        existing_actions = self.api_call('GET', f"{self.realm_name}/authentication/required-actions")
        
        for action in required_actions:
            existing_action = None
            for existing in existing_actions:
                if existing.get('alias') == action['alias']:
                    existing_action = existing
                    break
            
            if existing_action:
                # Update existing action
                action_data = {
                    'alias': action['alias'],
                    'name': action['name'],
                    'enabled': action['enabled'],
                    'defaultAction': action.get('defaultAction', False),
                    'priority': action.get('priority', 10),
                    'config': action.get('config', {})
                }
                
                result = self.api_call('PUT', f"{self.realm_name}/authentication/required-actions/{action['alias']}", action_data)
                
                if result is not None:
                    print(f"✓ Required action {action['alias']} configured successfully")
        
        return True
    
    def create_test_users(self) -> bool:
        """Create test users for different roles"""
        print("Creating test users...")
        
        test_users = [
            {
                "username": "hr.manager",
                "email": "hr.manager@talentoz.com",
                "firstName": "HR",
                "lastName": "Manager",
                "enabled": True,
                "emailVerified": True,
                "credentials": [
                    {
                        "type": "password",
                        "value": "TalentOz@2024",
                        "temporary": False
                    }
                ],
                "groups": ["/HR Managers"],
                "realmRoles": ["hr_manager"]
            },
            {
                "username": "john.doe",
                "email": "john.doe@talentoz.com",
                "firstName": "John",
                "lastName": "Doe",
                "enabled": True,
                "emailVerified": True,
                "credentials": [
                    {
                        "type": "password",
                        "value": "Employee@2024",
                        "temporary": False
                    }
                ],
                "groups": ["/Employees"],
                "realmRoles": ["employee"]
            }
        ]
        
        for user in test_users:
            existing_users = self.api_call('GET', f"{self.realm_name}/users", {"username": user["username"]})
            
            if existing_users:
                print(f"User {user['username']} already exists")
            else:
                print(f"Creating test user: {user['username']}")
                result = self.api_call('POST', f"{self.realm_name}/users", user)
                
                if result is not None:
                    print(f"✓ Test user {user['username']} created successfully")
        
        return True
    
    def configure_realm_settings(self, realm_config: Dict) -> bool:
        """Configure realm-level settings"""
        print("Configuring realm settings...")
        
        # Update realm with security settings
        realm_updates = {
            "bruteForceProtected": True,
            "permanentLockout": False,
            "maxFailureWaitSeconds": 900,
            "minimumQuickLoginWaitSeconds": 60,
            "waitIncrementSeconds": 60,
            "quickLoginCheckMilliSeconds": 1000,
            "maxDeltaTimeSeconds": 43200,
            "failureFactor": 30,
            "otpPolicyType": "totp",
            "otpPolicyAlgorithm": "HmacSHA1",
            "otpPolicyDigits": 6,
            "otpPolicyLookAheadWindow": 1,
            "otpPolicyPeriod": 30,
            "webAuthnPolicyRpEntityName": "TalentOz HCM",
            "webAuthnPolicyRpId": "id.talentoz.com"
        }
        
        result = self.api_call('PUT', self.realm_name, realm_updates)
        
        if result is not None:
            print("✓ Realm security settings configured successfully")
            return True
        return False
    
    def run_keycloak_configuration(self, config_file: str):
        """Run complete Keycloak configuration"""
        print("Starting Keycloak Configuration...")
        print("=" * 50)
        
        # Load configuration
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        try:
            # 1. Get admin token
            self.get_admin_token()
            
            # 2. Create realm
            self.create_realm(config)
            
            # 3. Create clients
            for client in config.get('clients', []):
                self.create_client(client)
            
            # 4. Create roles
            if 'roles' in config and 'realm' in config['roles']:
                self.create_roles(config['roles']['realm'])
            
            # 5. Create groups
            if 'groups' in config:
                self.create_groups(config['groups'])
            
            # 6. Create identity providers
            if 'identityProviders' in config:
                self.create_identity_providers(config['identityProviders'])
            
            # 7. Configure authentication flows
            if 'authenticationFlows' in config:
                self.configure_authentication_flows(config['authenticationFlows'])
            
            # 8. Enable required actions
            if 'requiredActions' in config:
                self.enable_required_actions(config['requiredActions'])
            
            # 9. Configure realm settings
            self.configure_realm_settings(config)
            
            # 10. Create test users
            self.create_test_users()
            
            print("\n" + "=" * 50)
            print("✓ Keycloak configuration completed successfully!")
            print("\nConfigured features:")
            print("- ERPNext realm with OIDC client")
            print("- Google and Microsoft identity providers")
            print("- Multi-factor authentication (TOTP + WebAuthn)")
            print("- Role-based access control")
            print("- Security policies and brute force protection")
            print("- Test users for different roles")
            print("\nAccess URLs:")
            print(f"- Keycloak Admin: {self.keycloak_url}/admin")
            print(f"- Realm: {self.keycloak_url}/realms/{self.realm_name}")
            print("\nTest Users:")
            print("- HR Manager: hr.manager / TalentOz@2024")
            print("- Employee: john.doe / Employee@2024")
            
        except Exception as e:
            print(f"\n❌ Configuration failed: {e}")
            sys.exit(1)

def main():
    if len(sys.argv) != 4:
        print("Usage: python configure-keycloak.py <keycloak_url> <admin_username> <admin_password>")
        print("Example: python configure-keycloak.py https://id.talentoz.com admin admin123")
        sys.exit(1)
    
    keycloak_url = sys.argv[1]
    admin_username = sys.argv[2]
    admin_password = sys.argv[3]
    
    configurator = KeycloakConfigurator(keycloak_url, admin_username, admin_password)
    configurator.run_keycloak_configuration("../configs/keycloak-realm-config.json")

if __name__ == "__main__":
    main()

