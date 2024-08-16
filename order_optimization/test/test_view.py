import pytest
from django.urls import reverse
from django.core.cache import cache
from unittest.mock import patch
from ..views import file_selector_view

@pytest.mark.django_db
def test_file_selector_view_cache_hit(client):
    # Mocking the CSV file retrieval
    file_id = 1
    mock_data = [{'id': 1, 'name': 'Test File'}]
    
    # Set up cache
    cache_key = f"file_selector_{file_id}"
    cache.set(cache_key, mock_data, 60)

    # Make the request
    response = client.get(reverse('file_selector_view'), {'file_id': file_id})

    # Check the response
    assert response.status_code == 200
    assert response.json() == {'file_selector': mock_data}

@pytest.mark.django_db
def test_file_selector_view_cache_miss(client):
    file_id = 1
    mock_data = [{'id': 1, 'name': 'Test File'}]

    # Mock the get_csv_file function
    with patch('order_optimization.views.get_csv_file') as mock_get_csv_file:
        mock_get_csv_file.return_value.file.path = 'path/to/mock.csv'
        
        with patch('order_optimization.views.ORD') as mock_ord:
            mock_ord.return_value.get.return_value.to_dict.return_value = mock_data

            # Make the request
            response = client.get(reverse('file_selector_view'), {'file_id': file_id})

            # Check the response
            assert response.status_code == 200
            assert response.json() == {'file_selector': mock_data}

            # Verify caching
            assert cache.get(f"file_selector_{file_id}") == mock_data