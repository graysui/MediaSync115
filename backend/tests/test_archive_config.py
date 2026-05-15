import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from copy import deepcopy

from app.services.archive_service import archive_service


def make_svc(tmp_path):
    """创建一个使用临时目录的 RuntimeSettingsService 实例"""
    with patch("app.services.runtime_settings_service.hdhive_service"), \
         patch("app.services.runtime_settings_service.pansou_service"), \
         patch("app.services.runtime_settings_service.tg_service") as mock_tg, \
         patch("app.services.runtime_settings_service.emby_service"), \
         patch("app.services.runtime_settings_service.proxy_manager"):
        mock_tg._parse_channels.return_value = []
        from app.services.runtime_settings_service import RuntimeSettingsService
        svc = RuntimeSettingsService()
        svc._file_path = tmp_path / "settings.json"
        svc._data = deepcopy(svc._defaults)
        svc._loaded_keys = set()
        return svc


def test_get_archive_naming_returns_defaults(tmp_path):
    svc = make_svc(tmp_path)
    naming = svc.get_archive_naming()
    assert naming["movie_root_dir"] == "电影"
    assert naming["tv_root_dir"] == "剧集"
    assert "season" in naming["season_dir_template"]
    assert "title" in naming["movie_filename_template"]
    assert "title" in naming["tv_filename_template"]


def test_update_archive_naming_persists(tmp_path):
    svc = make_svc(tmp_path)
    svc.update_archive_naming({"movie_root_dir": "Movies"})
    assert svc.get_archive_naming()["movie_root_dir"] == "Movies"


def test_get_archive_classification_returns_defaults(tmp_path):
    svc = make_svc(tmp_path)
    cls = svc.get_archive_classification()
    assert "movie_rules" in cls
    assert "tv_rules" in cls
    assert len(cls["movie_rules"]) > 0
    assert len(cls["tv_rules"]) > 0


def test_update_archive_classification_persists(tmp_path):
    svc = make_svc(tmp_path)
    new_rules = {
        "movie_rules": [{"name": "全部电影", "match_type": "default", "values": []}],
        "tv_rules": [],
    }
    svc.update_archive_classification(new_rules)
    cls = svc.get_archive_classification()
    assert cls["movie_rules"][0]["name"] == "全部电影"


def test_archive_classification_defaults_are_deep_copied(tmp_path):
    svc = make_svc(tmp_path)
    first = svc.get_archive_classification()
    first["movie_rules"][0]["name"] = "污染默认值"

    second = svc.get_archive_classification()
    assert second["movie_rules"][0]["name"] == "动画电影"


def test_update_archive_classification_normalizes_rules(tmp_path):
    svc = make_svc(tmp_path)
    svc.update_archive_classification(
        {
            "movie_rules": [
                {"name": "", "match_type": "default", "values": ["CN"]},
                {"name": "类型", "match_type": "genre", "values": ["16", "bad"]},
                {"name": "地区", "match_type": "country", "values": ["cn", " jp "]},
                {"name": "兜底", "match_type": "default", "values": ["US"]},
            ],
            "tv_rules": [],
        }
    )

    rules = svc.get_archive_classification()["movie_rules"]
    assert rules == [
        {"name": "类型", "match_type": "genre", "values": [16]},
        {"name": "地区", "match_type": "country", "values": ["CN", "JP"]},
        {"name": "兜底", "match_type": "default", "values": []},
    ]


def test_archive_naming_api_get_put(client: TestClient):
    login = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "password"},
    )
    assert login.status_code == 200

    resp = client.get("/api/archive/naming")
    assert resp.status_code == 200
    assert resp.json()["movie_root_dir"]

    resp = client.put("/api/archive/naming", json={"movie_root_dir": "Movies"})
    assert resp.status_code == 200
    assert resp.json()["movie_root_dir"] == "Movies"


def test_archive_naming_api_rejects_invalid_template(client: TestClient):
    login = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "password"},
    )
    assert login.status_code == 200

    resp = client.put("/api/archive/naming", json={"movie_filename_template": "{{ title "})
    assert resp.status_code == 400


def test_archive_classification_api_get_put(client: TestClient):
    login = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "password"},
    )
    assert login.status_code == 200

    payload = {
        "movie_rules": [{"name": "全部电影", "match_type": "default", "values": []}],
        "tv_rules": [{"name": "全部剧集", "match_type": "default", "values": []}],
    }

    resp = client.put("/api/archive/classification", json=payload)
    assert resp.status_code == 200
    assert resp.json()["movie_rules"][0]["name"] == "全部电影"

    resp = client.get("/api/archive/classification")
    assert resp.status_code == 200
    assert resp.json()["tv_rules"][0]["name"] == "全部剧集"


def test_archive_classify_by_rules_order_and_default():
    detail = {
        "genres": [{"id": 16}],
        "origin_country": ["US"],
        "production_countries": [{"iso_3166_1": "JP"}],
    }
    rules = [
        {"name": "动画", "match_type": "genre", "values": [16]},
        {"name": "美国", "match_type": "country", "values": ["US"]},
        {"name": "其他", "match_type": "default", "values": []},
    ]

    assert archive_service._classify_by_rules(detail, rules) == "动画"
    assert archive_service._classify_by_rules(detail, rules[1:]) == "美国"
    assert archive_service._classify_by_rules({"genres": []}, rules) == "其他"
    assert archive_service._classify_by_rules(detail, []) == ""


def test_archive_build_target_filename_templates(monkeypatch):
    naming = {
        "movie_root_dir": "电影",
        "tv_root_dir": "剧集",
        "season_dir_template": "Season {{ season }}",
        "movie_filename_template": "{{ title }}.{{ year }}.{{ tmdb_id }}{{ ext }}",
        "tv_filename_template": "{{ title }} - {{ season }}x{{ episode }}{{ ext }}",
    }
    monkeypatch.setattr(
        "app.services.archive_service.runtime_settings_service.get_archive_naming",
        lambda: naming,
    )

    movie = archive_service._build_target_filename(
        {"media_type": "movie", "query_title": "Test", "year": "2026", "extension": ".mkv"},
        {"title": "测试", "year": "2026", "tmdb_id": 1},
        "old.mkv",
    )
    tv = archive_service._build_target_filename(
        {"media_type": "tv", "query_title": "Show", "season": 2, "episode": 3, "extension": ".mp4"},
        {"title": "剧集", "year": "2026", "tmdb_id": 2},
        "old.mp4",
    )

    assert movie == "测试.2026.1.mkv"
    assert tv == "剧集 - 2x3.mp4"


def test_archive_build_target_filename_fallback(monkeypatch):
    naming = {
        "movie_root_dir": "电影",
        "tv_root_dir": "剧集",
        "season_dir_template": "第{{ season }}季",
        "movie_filename_template": "{{ missing }}",
        "tv_filename_template": "{{ title }}",
    }
    monkeypatch.setattr(
        "app.services.archive_service.runtime_settings_service.get_archive_naming",
        lambda: naming,
    )

    filename = archive_service._build_target_filename(
        {"media_type": "movie", "query_title": "Test", "year": None, "extension": ".mkv"},
        {"title": "测试", "year": "", "tmdb_id": 1},
        "old.mkv",
    )
    assert filename == "测试.mkv"
