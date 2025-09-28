#!/usr/bin/env python3
"""
Convert OpenAPI specification to Postman collection
"""
import json
import sys
from pathlib import Path

def openapi_to_postman(openapi_file, output_file):
    """Convert OpenAPI spec to Postman collection"""
    
    with open(openapi_file, 'r') as f:
        openapi_spec = json.load(f)
    
    # Basic Postman collection structure
    collection = {
        "info": {
            "name": openapi_spec.get("info", {}).get("title", "API Collection"),
            "description": openapi_spec.get("info", {}).get("description", ""),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        },
        "item": [],
        "variable": [
            {
                "key": "baseUrl",
                "value": "http://localhost:8000",
                "type": "string"
            }
        ]
    }
    
    # Convert paths to Postman requests
    paths = openapi_spec.get("paths", {})
    
    for path, methods in paths.items():
        for method, operation in methods.items():
            if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                request_item = {
                    "name": operation.get("summary", f"{method.upper()} {path}"),
                    "request": {
                        "method": method.upper(),
                        "header": [
                            {
                                "key": "Content-Type",
                                "value": "application/json"
                            },
                            {
                                "key": "Authorization",
                                "value": "Bearer {{token}}"
                            }
                        ],
                        "url": {
                            "raw": "{{baseUrl}}" + path,
                            "host": ["{{baseUrl}}"],
                            "path": path.strip("/").split("/") if path != "/" else []
                        }
                    },
                    "response": []
                }
                
                # Add request body for POST/PUT/PATCH
                if method.upper() in ["POST", "PUT", "PATCH"]:
                    request_body = operation.get("requestBody", {})
                    if request_body:
                        content = request_body.get("content", {})
                        json_content = content.get("application/json", {})
                        schema = json_content.get("schema", {})
                        
                        # Create example body
                        example_body = create_example_from_schema(schema)
                        
                        request_item["request"]["body"] = {
                            "mode": "raw",
                            "raw": json.dumps(example_body, indent=2),
                            "options": {
                                "raw": {
                                    "language": "json"
                                }
                            }
                        }
                
                collection["item"].append(request_item)
    
    # Write Postman collection
    with open(output_file, 'w') as f:
        json.dump(collection, f, indent=2)
    
    print(f"✅ Generated Postman collection with {len(collection['item'])} requests")

def create_example_from_schema(schema):
    """Create example data from JSON schema"""
    if not schema:
        return {}
    
    schema_type = schema.get("type", "object")
    
    if schema_type == "object":
        example = {}
        properties = schema.get("properties", {})
        for prop_name, prop_schema in properties.items():
            example[prop_name] = create_example_from_schema(prop_schema)
        return example
    
    elif schema_type == "array":
        items_schema = schema.get("items", {})
        return [create_example_from_schema(items_schema)]
    
    elif schema_type == "string":
        if schema.get("format") == "email":
            return "user@example.com"
        elif schema.get("format") == "date-time":
            return "2024-01-01T00:00:00Z"
        else:
            return schema.get("example", "string")
    
    elif schema_type == "integer":
        return schema.get("example", 1)
    
    elif schema_type == "number":
        return schema.get("example", 1.0)
    
    elif schema_type == "boolean":
        return schema.get("example", True)
    
    else:
        return schema.get("example", "value")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python openapi_to_postman.py <openapi_file> <output_file>")
        sys.exit(1)
    
    openapi_file = sys.argv[1]
    output_file = sys.argv[2]
    
    if not Path(openapi_file).exists():
        print(f"Error: OpenAPI file {openapi_file} not found")
        sys.exit(1)
    
    openapi_to_postman(openapi_file, output_file)
