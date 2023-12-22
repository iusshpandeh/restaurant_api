import pytest
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)


def test_open_restaurants_endpoint():

    response = client.get("/open-restaurants/",
                          params={"datetime_param": "2023-01-01 12:00:00"})
    assert response.status_code == 200
    assert response.json() == {"open_restaurants": [
        "The Cowfish Sushi Burger Bar", "Morgan St Food Hall", "Beasley's Chicken + Honey"]}

    response_invalid_datetime = client.get(
        "/open-restaurants/", params={"datetime_param": "invalid_datetime"})
    assert response_invalid_datetime.status_code == 422


if __name__ == "__main__":
    pytest.main()
