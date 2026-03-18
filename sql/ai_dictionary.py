# -*- coding: UTF-8 -*-
import simplejson as json
from django.contrib.auth.decorators import permission_required
from django.http import JsonResponse
from django.db.models import Q
from django.template import Context, Template

from common.utils.openai import OpenaiClient, check_openai_config
from sql.engines import get_engine
from sql.models import AiDict, AiTemplate, Users
from sql.utils.resource_group import user_instances


@permission_required("sql.menu_ai_dict", raise_exception=True)
def table_meta(request):
    instance_name = request.GET.get("instance_name", "")
    db_name = request.GET.get("db_name", "")
    tb_name = request.GET.get("tb_name", "")
    if not all([instance_name, db_name, tb_name]):
        return JsonResponse({"status": 1, "msg": "参数不完整", "data": {}})

    try:
        instance = user_instances(request.user, db_type=["mysql"]).get(
            instance_name=instance_name
        )
    except Exception:
        return JsonResponse({"status": 1, "msg": "你所在组未关联该实例", "data": {}})

    query_engine = None
    try:
        query_engine = get_engine(instance=instance)
        escaped_db_name = query_engine.escape_string(db_name)
        escaped_tb_name = query_engine.escape_string(tb_name)
        ddl_result = query_engine.query(
            escaped_db_name, f"show create table `{escaped_tb_name}`;"
        )
        if ddl_result.error:
            return JsonResponse({"status": 1, "msg": ddl_result.error, "data": {}})
        table_comment_result = query_engine.query(
            escaped_db_name,
            """SELECT TABLE_COMMENT
               FROM information_schema.TABLES
               WHERE TABLE_SCHEMA=%(db_name)s AND TABLE_NAME=%(tb_name)s""",
            parameters={"db_name": escaped_db_name, "tb_name": escaped_tb_name},
        )
        desc_data = query_engine.get_table_desc_data(
            db_name=escaped_db_name, tb_name=escaped_tb_name
        )
    except Exception as e:
        return JsonResponse({"status": 1, "msg": str(e), "data": {}})
    finally:
        if query_engine:
            query_engine.close()

    ddl = ""
    if ddl_result.rows:
        ddl = ddl_result.rows[0][-1]
    origin_table_comment = ""
    if table_comment_result.rows:
        origin_table_comment = str(table_comment_result.rows[0][0] or "")

    dict_obj = AiDict.objects.filter(
        instance=instance_name, db=db_name, table=tb_name
    ).first()
    saved_columns = {}
    saved_table_comment = ""
    if dict_obj:
        try:
            properties = json.loads(dict_obj.properties)
            if isinstance(properties, dict):
                saved_table_comment = str(properties.get("table_comment", "") or "")
                properties = properties.get("columns", [])
            for item in properties or []:
                column_name = item.get("column_name", "")
                if "selected" in item and not bool(item.get("selected", False)):
                    continue
                if column_name:
                    saved_columns[column_name] = item
        except Exception:
            saved_columns = {}
    table_comment = saved_table_comment if saved_table_comment else origin_table_comment

    columns = []
    for row in desc_data.get("rows", []):
        column_name = row[0]
        column_type = row[1]
        origin_comment = row[7] if len(row) > 7 else ""
        saved = saved_columns.get(column_name, {})
        comment = saved.get("comment")
        if comment is None:
            comment = origin_comment
        columns.append(
            {
                "column_name": column_name,
                "column_type": column_type,
                "origin_comment": origin_comment,
                "comment": comment,
                "selected": bool(saved),
            }
        )
    return JsonResponse(
        {
            "status": 0,
            "msg": "ok",
            "data": {
                "id": dict_obj.id if dict_obj else None,
                "ddl": ddl,
                "table_comment": table_comment,
                "origin_table_comment": origin_table_comment,
                "columns": columns,
            },
        }
    )


@permission_required("sql.menu_ai_dict", raise_exception=True)
def save(request):
    if request.method != "POST":
        return JsonResponse({"status": 1, "msg": "非法调用", "data": []})

    instance_name = request.POST.get("instance_name", "")
    db_name = request.POST.get("db_name", "")
    tb_name = request.POST.get("tb_name", "")
    table_comment = str(request.POST.get("table_comment", "")).strip()
    properties_str = request.POST.get("properties", "[]")

    if not all([instance_name, db_name, tb_name]):
        return JsonResponse({"status": 1, "msg": "参数不完整", "data": []})

    try:
        user_instances(request.user, db_type=["mysql"]).get(instance_name=instance_name)
    except Exception:
        return JsonResponse({"status": 1, "msg": "你所在组未关联该实例", "data": []})

    try:
        properties = json.loads(properties_str)
    except Exception:
        return JsonResponse({"status": 1, "msg": "properties参数格式错误", "data": []})
    if not isinstance(properties, list):
        return JsonResponse({"status": 1, "msg": "properties参数格式错误", "data": []})

    columns = []
    for item in properties:
        column_name = str(item.get("column_name", "")).strip()
        if not column_name:
            continue
        columns.append(
            {
                "column_name": column_name,
                "column_type": str(item.get("column_type", "")).strip(),
                "comment": str(item.get("comment", "")).strip(),
            }
        )
    if not columns:
        return JsonResponse({"status": 1, "msg": "请至少选择一列", "data": []})

    dict_obj = AiDict.objects.filter(
        instance=instance_name, db=db_name, table=tb_name
    ).first()
    properties_json = json.dumps(
        {"table_comment": table_comment, "columns": columns}, ensure_ascii=False
    )
    if dict_obj:
        dict_obj.properties = properties_json
        dict_obj.update_id = request.user.id
        dict_obj.save(update_fields=["properties", "update_id", "update_time"])
    else:
        dict_obj = AiDict.objects.create(
            instance=instance_name,
            db=db_name,
            table=tb_name,
            properties=properties_json,
            create_id=request.user.id,
            update_id=request.user.id,
        )
    return JsonResponse({"status": 0, "msg": "保存成功", "data": {"id": dict_obj.id}})


@permission_required("sql.menu_ai_dict", raise_exception=True)
def lists(request):
    keyword = str(request.GET.get("keyword", "")).strip()
    instance_name = str(request.GET.get("instance_name", "")).strip()
    db_name = str(request.GET.get("db_name", "")).strip()
    ins_qs = user_instances(request.user, db_type=["mysql"]).values_list(
        "instance_name", flat=True
    )
    queryset = AiDict.objects.filter(instance__in=ins_qs)
    if instance_name:
        queryset = queryset.filter(instance=instance_name)
    if db_name:
        queryset = queryset.filter(db__icontains=db_name)
    if keyword:
        queryset = queryset.filter(
            Q(instance__icontains=keyword)
            | Q(db__icontains=keyword)
            | Q(table__icontains=keyword)
        )
    queryset = queryset.order_by("-update_time", "-id")
    user_ids = set()
    for obj in queryset:
        if obj.create_id > 0:
            user_ids.add(obj.create_id)
        if obj.update_id > 0:
            user_ids.add(obj.update_id)
    user_map = {}
    if user_ids:
        user_map = {
            i["id"]: i["display"] or i["username"]
            for i in Users.objects.filter(id__in=list(user_ids)).values(
                "id", "display", "username"
            )
        }

    rows = []
    for obj in queryset:
        selected_count = 0
        try:
            properties = json.loads(obj.properties)
            if isinstance(properties, dict):
                properties = properties.get("columns", [])
            selected_count = len(
                [
                    item
                    for item in properties
                    if "selected" not in item or bool(item.get("selected", False))
                ]
            )
        except Exception:
            selected_count = 0
        rows.append(
            {
                "id": obj.id,
                "instance": obj.instance,
                "db": obj.db,
                "table": obj.table,
                "selected_count": selected_count,
                "create_user": user_map.get(obj.create_id, str(obj.create_id or "")),
                "update_user": user_map.get(obj.update_id, str(obj.update_id or "")),
                "update_time": obj.update_time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    return JsonResponse({"status": 0, "msg": "ok", "data": rows})


def build_ai_dict_text(dict_obj, index=None):
    table_comment = ""
    business_logic = ""
    columns = []
    try:
        properties = json.loads(dict_obj.properties)
        if isinstance(properties, dict):
            table_comment = str(properties.get("table_comment", "") or "").strip()
            business_logic = str(
                properties.get("business_logic")
                or properties.get("business_rules")
                or properties.get("biz_logic")
                or properties.get("logic")
                or ""
            ).strip()
            columns = properties.get("columns", [])
        elif isinstance(properties, list):
            columns = properties
    except Exception:
        columns = []
    if not isinstance(columns, list):
        columns = []
    lines = []
    for item in columns:
        if not isinstance(item, dict):
            continue
        column_name = str(item.get("column_name", "")).strip()
        if not column_name:
            continue
        column_type = str(item.get("column_type", "")).strip()
        comment = str(item.get("comment", "")).strip()
        parts = [f"- {column_name}:"]
        if column_type:
            parts.append(column_type)
        if comment:
            parts.append(f"({comment})")
        lines.append(" ".join(parts))
    title = dict_obj.table
    if table_comment:
        title = f"{title} ({table_comment})"
    title_prefix = f"{index}. " if index else ""
    parts = [f"{title_prefix}{title}", "\n".join(lines)]
    if business_logic:
        parts.append(f"* 业务逻辑：{business_logic}")
    return "\n".join(parts)


@permission_required("sql.menu_ai_dict", raise_exception=True)
def template_preview(request):
    if request.method != "POST":
        return JsonResponse({"status": 1, "msg": "非法调用", "data": ""})
    instance_name = str(request.POST.get("instance_name", "")).strip()
    db_name = str(request.POST.get("db_name", "")).strip()
    table_names = str(request.POST.get("table_names", "")).strip()
    selected_tables = [i.strip() for i in table_names.split(",") if i.strip()]
    dict_id = str(request.POST.get("dict_id", "")).strip()
    user_input = str(request.POST.get("user_input", "")).strip()
    query_template = str(request.POST.get("query_template", "")).strip()
    if not user_input or not query_template:
        return JsonResponse({"status": 1, "msg": "参数不完整", "data": ""})
    ins_qs = user_instances(request.user, db_type=["mysql"]).values_list(
        "instance_name", flat=True
    )

    queryset = AiDict.objects.none()
    if instance_name and db_name and selected_tables:
        queryset = AiDict.objects.filter(
            instance__in=ins_qs,
            instance=instance_name,
            db=db_name,
            table__in=selected_tables,
        )
    elif dict_id:
        dict_obj = AiDict.objects.filter(id=dict_id, instance__in=ins_qs).first()
        if dict_obj:
            queryset = AiDict.objects.filter(id=dict_obj.id)
            instance_name = dict_obj.instance
    if not queryset.exists():
        return JsonResponse({"status": 1, "msg": "字典记录不存在或无权限", "data": ""})
    db_type = "mysql"
    instance_obj = user_instances(request.user, db_type=["mysql"]).filter(
        instance_name=instance_name
    ).first()
    if instance_obj and instance_obj.db_type:
        db_type = instance_obj.db_type
    ai_dict_text = "\n\n".join(
        [
            build_ai_dict_text(obj, index=i)
            for i, obj in enumerate(queryset.order_by("table"), start=1)
        ]
    )
    try:
        template = Template(query_template)
        content = template.render(
            Context(
                {
                    "db_type": db_type,
                    "ai_dict": ai_dict_text,
                    "table_schema": ai_dict_text,
                    "user_input": user_input,
                }
            )
        )
    except Exception as e:
        return JsonResponse({"status": 1, "msg": f"模板渲染失败: {e}", "data": ""})
    return JsonResponse({"status": 0, "msg": "ok", "data": content})


@permission_required("sql.menu_ai_dict", raise_exception=True)
def ai_execute(request):
    if request.method != "POST":
        return JsonResponse({"status": 1, "msg": "非法调用", "data": ""})
    instance_name = str(request.POST.get("instance_name", "")).strip()
    db_name = str(request.POST.get("db_name", "")).strip()
    table_names = str(request.POST.get("table_names", "")).strip()
    selected_tables = [i.strip() for i in table_names.split(",") if i.strip()]
    user_input = str(request.POST.get("user_input", "")).strip()
    query_template = str(request.POST.get("query_template", "")).strip()
    if not instance_name or not db_name or not selected_tables or not user_input:
        return JsonResponse({"status": 1, "msg": "参数不完整", "data": ""})
    if not check_openai_config():
        return JsonResponse({"status": 1, "msg": "AI配置未开启", "data": ""})
    ins_qs = user_instances(request.user, db_type=["mysql"]).values_list(
        "instance_name", flat=True
    )
    queryset = AiDict.objects.filter(
        instance__in=ins_qs,
        instance=instance_name,
        db=db_name,
        table__in=selected_tables,
    ).order_by("table")
    if not queryset.exists():
        return JsonResponse({"status": 1, "msg": "字典记录不存在或无权限", "data": ""})
    db_type = "mysql"
    instance_obj = user_instances(request.user, db_type=["mysql"]).filter(
        instance_name=instance_name
    ).first()
    if instance_obj and instance_obj.db_type:
        db_type = instance_obj.db_type
    ai_dict_text = "\n\n".join(
        [build_ai_dict_text(obj, index=i) for i, obj in enumerate(queryset, start=1)]
    )
    try:
        openai_client = OpenaiClient(user=request.user)
        if query_template:
            template = Template(query_template)
            content = template.render(
                Context(
                    {
                        "db_type": db_type,
                        "ai_dict": ai_dict_text,
                        "table_schema": ai_dict_text,
                        "user_input": user_input,
                    }
                )
            )
            messages = [dict(role="user", content=content)]
            res = openai_client.request_chat_completion(messages)
            result = str(res.choices[0].message.content or "").lstrip()
        else:
            result = openai_client.generate_sql_by_openai(
                db_type=db_type,
                table_schema=ai_dict_text,
                user_input=user_input,
                ai_dict=ai_dict_text,
            )
    except Exception as e:
        return JsonResponse({"status": 1, "msg": str(e), "data": ""})
    return JsonResponse({"status": 0, "msg": "ok", "data": result})


def _template_name(template_text, template_id):
    for line in str(template_text or "").split("\n"):
        name = str(line or "").strip().lstrip("#").strip()
        if name:
            return name[:64]
    return f"模板{template_id}"


@permission_required("sql.menu_ai_dict", raise_exception=True)
def template_list(request):
    keyword = str(request.GET.get("keyword", "")).strip()
    can_manage_all = request.user.is_superuser or request.user.has_perm(
        "sql.ai_dict_manage_template"
    )
    queryset = AiTemplate.objects.all()
    if not can_manage_all:
        queryset = queryset.filter(create_id=request.user.id)
    if keyword:
        keyword_filter = Q(name__icontains=keyword)
        if keyword.isdigit():
            keyword_filter = Q(id=int(keyword)) | keyword_filter
        queryset = queryset.filter(keyword_filter)
    queryset = queryset.order_by("-update_time", "-id")
    user_ids = set()
    for obj in queryset:
        if obj.create_id > 0:
            user_ids.add(obj.create_id)
        if obj.update_id > 0:
            user_ids.add(obj.update_id)
    user_map = {}
    if user_ids:
        user_map = {
            i["id"]: i["display"] or i["username"]
            for i in Users.objects.filter(id__in=list(user_ids)).values(
                "id", "display", "username"
            )
        }
    rows = []
    for obj in queryset:
        rows.append(
            {
                "id": obj.id,
                "name": obj.name or _template_name(obj.template, obj.id),
                "template": obj.template,
                "create_user": user_map.get(obj.create_id, str(obj.create_id or "")),
                "update_user": user_map.get(obj.update_id, str(obj.update_id or "")),
                "update_time": obj.update_time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    return JsonResponse({"status": 0, "msg": "ok", "data": rows})


@permission_required("sql.menu_ai_dict", raise_exception=True)
def save_query_template(request):
    if request.method != "POST":
        return JsonResponse({"status": 1, "msg": "非法调用", "data": []})
    query_template = str(request.POST.get("query_template", "")).strip()
    template_name = str(request.POST.get("template_name", "")).strip()
    template_id = str(request.POST.get("template_id", "")).strip()
    if not query_template:
        return JsonResponse({"status": 1, "msg": "模板不能为空", "data": []})
    if not template_name:
        return JsonResponse({"status": 1, "msg": "名称不能为空", "data": []})
    can_manage_all = request.user.is_superuser or request.user.has_perm(
        "sql.ai_dict_manage_template"
    )
    if template_id:
        queryset = AiTemplate.objects.filter(id=template_id)
        if not can_manage_all:
            queryset = queryset.filter(create_id=request.user.id)
        template_obj = queryset.first()
        if not template_obj:
            return JsonResponse({"status": 1, "msg": "模板不存在或无权限", "data": []})
        template_obj.name = template_name
        template_obj.template = query_template
        template_obj.update_id = request.user.id
        template_obj.save(update_fields=["name", "template", "update_id", "update_time"])
    else:
        template_obj = AiTemplate.objects.create(
            name=template_name,
            template=query_template,
            create_id=request.user.id,
            update_id=request.user.id,
        )
    return JsonResponse({"status": 0, "msg": "保存成功", "data": {"id": template_obj.id}})


@permission_required("sql.menu_ai_dict", raise_exception=True)
def delete_query_template(request):
    if request.method != "POST":
        return JsonResponse({"status": 1, "msg": "非法调用", "data": []})
    template_id = str(request.POST.get("id", "")).strip()
    if not template_id:
        return JsonResponse({"status": 1, "msg": "参数不完整", "data": []})
    can_manage_all = request.user.is_superuser or request.user.has_perm(
        "sql.ai_dict_manage_template"
    )
    queryset = AiTemplate.objects.filter(id=template_id)
    if not can_manage_all:
        queryset = queryset.filter(create_id=request.user.id)
    deleted, _ = queryset.delete()
    if deleted == 0:
        return JsonResponse({"status": 1, "msg": "模板不存在或无权限", "data": []})
    return JsonResponse({"status": 0, "msg": "删除成功", "data": []})


@permission_required("sql.menu_ai_dict", raise_exception=True)
def delete(request):
    if request.method != "POST":
        return JsonResponse({"status": 1, "msg": "非法调用", "data": []})

    dict_id = request.POST.get("id")
    if not dict_id:
        return JsonResponse({"status": 1, "msg": "参数不完整", "data": []})

    ins_qs = user_instances(request.user, db_type=["mysql"]).values_list(
        "instance_name", flat=True
    )
    deleted, _ = AiDict.objects.filter(id=dict_id, instance__in=ins_qs).delete()
    if deleted == 0:
        return JsonResponse({"status": 1, "msg": "记录不存在或无权限", "data": []})
    return JsonResponse({"status": 0, "msg": "删除成功", "data": []})
