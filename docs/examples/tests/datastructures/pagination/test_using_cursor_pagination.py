from examples.datastructures.pagination.using_cursor_pagination import app
from starlite.testing import TestClient

from starlite.status_codes import HTTP_200_OK


def test_using_cursor_pagination() -> None:
    with TestClient(app) as client:
        response = client.get("/people", params={"results_per_page": 5})
        assert response.status_code == HTTP_200_OK
        response_data = response.json()
        assert len(response_data["items"]) == 5
        assert response_data["results_per_page"] == 5
        assert isinstance(response_data["cursor"], str)
