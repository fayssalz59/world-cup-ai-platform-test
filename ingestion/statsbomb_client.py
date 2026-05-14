from typing import Any

import requests


class StatsBombOpenDataClient:
    def __init__(self, base_url: str, timeout_seconds: int = 30) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def fetch_json(self, relative_path: str) -> Any:
        url = self.url_for(relative_path)
        response = requests.get(url, timeout=self._timeout_seconds)
        response.raise_for_status()
        return response.json()

    def url_for(self, relative_path: str) -> str:
        return f"{self._base_url}/{relative_path.lstrip('/')}"

    def get_competitions(self) -> Any:
        return self.fetch_json("competitions.json")

    def get_matches(self, competition_id: int, season_id: int) -> Any:
        return self.fetch_json(f"matches/{competition_id}/{season_id}.json")

    def get_events(self, match_id: int) -> Any:
        return self.fetch_json(f"events/{match_id}.json")

    def get_lineups(self, match_id: int) -> Any:
        return self.fetch_json(f"lineups/{match_id}.json")
