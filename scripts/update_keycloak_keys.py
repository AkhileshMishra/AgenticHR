#!/usr/bin/env python3
"""
Script to update Keycloak realm configuration with RSA keys for JWT signing.
This ensures Kong can verify JWTs issued by Keycloak.
"""

import json
import base64
from pathlib import Path

def private_key_to_base64(private_key_pem: str) -> str:
    """Convert PEM private key to base64 for Keycloak."""
    # Remove PEM headers and whitespace
    key_content = private_key_pem.replace("-----BEGIN PRIVATE KEY-----", "")
    key_content = key_content.replace("-----END PRIVATE KEY-----", "")
    key_content = key_content.replace("\n", "").replace(" ", "")
    return key_content

def update_keycloak_realm():
    """Update the Keycloak realm export with proper RSA keys."""
    
    # Read the private key
    private_key_path = Path("temp_keys/private.pem")
    with open(private_key_path, 'r') as f:
        private_key_pem = f.read()
    
    # Read the current realm configuration
    realm_path = Path("docker/keycloak/realm-export.json")
    with open(realm_path, 'r') as f:
        realm_config = json.load(f)
    
    # Convert private key to base64
    private_key_b64 = private_key_to_base64(private_key_pem)
    
    # Update the realm with RSA key configuration
    realm_config["components"] = {
        "org.keycloak.keys.KeyProvider": [
            {
                "id": "rsa-generated",
                "name": "rsa-generated",
                "providerId": "rsa-generated",
                "subComponents": {},
                "config": {
                    "priority": ["100"],
                    "enabled": ["true"],
                    "active": ["true"],
                    "algorithm": ["RS256"],
                    "keySize": ["2048"],
                    "privateKey": [private_key_b64]
                }
            }
        ]
    }
    
    # Ensure the realm issuer matches what Kong expects
    realm_config["realm"] = "agentichr"
    
    # Write the updated configuration
    with open(realm_path, 'w') as f:
        json.dump(realm_config, f, indent=2)
    
    print("✅ Updated Keycloak realm configuration with RSA keys")
    print(f"   - Realm: {realm_config['realm']}")
    print(f"   - Issuer will be: http://keycloak:8080/realms/agentichr")
    print(f"   - Kong consumer key matches issuer URL")

if __name__ == "__main__":
    update_keycloak_realm()
