"""A source checkout must not require private receipts or imply qualification."""
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from backend import luna_real_ui


def test_checkout_without_history_starts_with_empty_archive(tmp_path, monkeypatch):
    monkeypatch.setattr(luna_real_ui, 'ROOT', tmp_path)
    service = luna_real_ui.RealService(SimpleNamespace(), root=tmp_path / 'service')
    assert service.archive == {}
    assert service.archived({'input': 'new request'}, 'responses') is None


def test_unqualified_checkout_cannot_prepare_evaluation(tmp_path, monkeypatch):
    monkeypatch.setattr(luna_real_ui, 'CERTIFICATES', tmp_path / 'missing.json')
    service = luna_real_ui.RealService(SimpleNamespace(), root=tmp_path / 'service', archive={})
    with pytest.raises(HTTPException) as caught:
        service.prepare([1])
    assert caught.value.status_code == 409
    assert not list((tmp_path / 'service').glob('plans/*'))
