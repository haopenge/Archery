from sql.models import AiTemplate


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
