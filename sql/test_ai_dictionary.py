import json

import sql.ai_dictionary as ai_dictionary
from sql.models import AiDict, AiTemplate


def test_save_query_template_by_login_user(admin_client, admin_user):
    response = admin_client.post(
        "/ai_dict/save_query_template/",
        data={"template_name": "测试模板", "query_template": "my template"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == 0
    template_obj = AiTemplate.objects.filter(create_id=admin_user.id).first()
    assert template_obj is not None
    assert template_obj.name == "测试模板"
    assert template_obj.template == "my template"


def test_template_list(admin_client, admin_user):
    AiTemplate.objects.create(
        name="模板A",
        template="first line\nother line",
        create_id=admin_user.id,
        update_id=admin_user.id,
    )
    response = admin_client.get("/ai_dict/template_list/")
    assert response.status_code == 200
    assert response.json()["status"] == 0
    rows = response.json()["data"]
    assert len(rows) >= 1
    assert rows[0]["id"] > 0
    assert rows[0]["name"] == "模板A"


def test_template_list_with_chinese_keyword(admin_client, admin_user):
    AiTemplate.objects.create(
        name="夸夸我模板",
        template="line1",
        create_id=admin_user.id,
        update_id=admin_user.id,
    )
    response = admin_client.get("/ai_dict/template_list/", data={"keyword": "夸夸我"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == 0
    assert len(payload["data"]) == 1
    assert payload["data"][0]["name"] == "夸夸我模板"


def test_saved_list_db_name_fuzzy_match(admin_client, admin_user, monkeypatch):
    class DummyInstanceQuerySet(object):
        def values_list(self, *args, **kwargs):
            return ["test-instance"]

    monkeypatch.setattr(
        ai_dictionary, "user_instances", lambda user, db_type=None: DummyInstanceQuerySet()
    )
    AiDict.objects.create(
        instance="test-instance",
        db="analytics_prod",
        table="orders",
        properties=json.dumps({"columns": []}, ensure_ascii=False),
        create_id=admin_user.id,
        update_id=admin_user.id,
    )
    AiDict.objects.create(
        instance="test-instance",
        db="core",
        table="users",
        properties=json.dumps({"columns": []}, ensure_ascii=False),
        create_id=admin_user.id,
        update_id=admin_user.id,
    )
    response = admin_client.get("/ai_dict/list/", data={"db_name": "analytic"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == 0
    assert len(payload["data"]) == 1
    assert payload["data"][0]["db"] == "analytics_prod"
