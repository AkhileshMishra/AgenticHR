import pytest
import httpx
from unittest.mock import patch

# Mock the auth dependency for testing
@pytest.fixture
def mock_auth():
    with patch('py_hrms_auth.jwt_dep.verify_bearer') as mock:
        mock.return_value = {
            'user_id': 'test-user',
            'username': 'testuser',
            'email': 'test@example.com',
            'roles': ['employee']
        }
        yield mock

@pytest.fixture
def client():
    from app.main import app
    return httpx.AsyncClient(app=app, base_url="http://test")

@pytest.mark.asyncio
async def test_create_employee_success(client, mock_auth):
    """Test successful employee creation"""
    employee_data = {
        "full_name": "John Doe",
        "email": "john.doe@test.com",
        "department": "Engineering",
        "position": "Software Engineer",
        "phone": "+1-555-0123"
    }
    
    with patch('app.db.SessionLocal') as mock_session:
        mock_session.return_value.__aenter__.return_value.add = lambda x: None
        mock_session.return_value.__aenter__.return_value.commit = lambda: None
        mock_session.return_value.__aenter__.return_value.refresh = lambda x: setattr(x, 'id', 1)
        
        response = await client.post("/v1/employees", json=employee_data)
        
        assert response.status_code == 200 or response.status_code == 201

@pytest.mark.asyncio
async def test_create_employee_duplicate_email(client, mock_auth):
    """Test employee creation with duplicate email returns 409"""
    employee_data = {
        "full_name": "Jane Doe",
        "email": "duplicate@test.com",
        "department": "Engineering"
    }
    
    from sqlalchemy.exc import IntegrityError
    
    with patch('app.db.SessionLocal') as mock_session:
        mock_session.return_value.__aenter__.return_value.add = lambda x: None
        mock_session.return_value.__aenter__.return_value.commit.side_effect = IntegrityError("", "", "")
        mock_session.return_value.__aenter__.return_value.rollback = lambda: None
        
        response = await client.post("/v1/employees", json=employee_data)
        
        assert response.status_code == 409

@pytest.mark.asyncio
async def test_get_employee_not_found(client, mock_auth):
    """Test getting non-existent employee returns 404"""
    with patch('app.db.SessionLocal') as mock_session:
        mock_session.return_value.__aenter__.return_value.execute.return_value.scalar_one_or_none.return_value = None
        
        response = await client.get("/v1/employees/999")
        
        assert response.status_code == 404

@pytest.mark.asyncio
async def test_update_employee_not_found(client, mock_auth):
    """Test updating non-existent employee returns 404"""
    update_data = {"full_name": "Updated Name"}
    
    with patch('app.db.SessionLocal') as mock_session:
        mock_session.return_value.__aenter__.return_value.execute.return_value.scalar_one_or_none.return_value = None
        
        response = await client.put("/v1/employees/999", json=update_data)
        
        assert response.status_code == 404

@pytest.mark.asyncio
async def test_delete_employee_not_found(client, mock_auth):
    """Test deleting non-existent employee returns 404"""
    with patch('app.db.SessionLocal') as mock_session:
        mock_session.return_value.__aenter__.return_value.execute.return_value.scalar_one_or_none.return_value = None
        
        response = await client.delete("/v1/employees/999")
        
        assert response.status_code == 404

@pytest.mark.asyncio
async def test_list_employees_pagination(client, mock_auth):
    """Test employee listing with pagination"""
    with patch('app.db.SessionLocal') as mock_session:
        # Mock the count query
        mock_session.return_value.__aenter__.return_value.execute.return_value.scalar.return_value = 25
        # Mock the employees query
        mock_session.return_value.__aenter__.return_value.execute.return_value.scalars.return_value.all.return_value = []
        
        response = await client.get("/v1/employees?page=1&per_page=10")
        
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_unauthorized_access():
    """Test that endpoints require authentication"""
    from app.main import app
    client = httpx.AsyncClient(app=app, base_url="http://test")
    
    # This should fail without proper auth mock
    response = await client.get("/v1/employees")
    
    # The exact status code depends on the auth implementation
    # but it should not be 200
    assert response.status_code != 200

def test_health_endpoint_no_auth():
    """Test that health endpoint doesn't require auth"""
    from app.main import app
    client = httpx.Client(app=app, base_url="http://test")
    
    response = client.get("/health")
    
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
