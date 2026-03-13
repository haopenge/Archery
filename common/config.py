# -*- coding: UTF-8 -*-
import logging
import traceback

import simplejson as json
from django.http import HttpResponse
from django_redis import get_redis_connection

from common.utils.permission import superuser_required
from sql.models import Config
from django.db import transaction

logger = logging.getLogger("default")
DEFAULT_QUERY_TEMPLATE_KEY = "default_query_template"
DEFAULT_QUERY_TEMPLATE_CACHE_KEY = "sys_config:default_query_template"


class SysConfig(object):
    def __init__(self):
        self.sys_config = {}

    def get_all_config(self):
        try:
            # 获取系统配置信息
            all_config = Config.objects.all().values("item", "value")
            sys_config = {}
            for items in all_config:
                if items["value"] in ("true", "True"):
                    items["value"] = True
                elif items["value"] in ("false", "False"):
                    items["value"] = False
                sys_config[items["item"]] = items["value"]
            self.sys_config = sys_config
        except Exception as m:
            logger.error(f"获取系统配置信息失败:{m}{traceback.format_exc()}")
            self.sys_config = {}

    def get(self, key, default_value=None):
        if key == DEFAULT_QUERY_TEMPLATE_KEY:
            redis_value = self._get_redis_value(DEFAULT_QUERY_TEMPLATE_CACHE_KEY)
            if redis_value is not None:
                if isinstance(redis_value, str) and redis_value.strip() == "":
                    return default_value
                self.sys_config[key] = redis_value
                return redis_value
        value = self.sys_config.get(key)
        if value:
            return value
        # 尝试去数据库里取
        config_entry = Config.objects.filter(item=key).last()
        if config_entry:
            # 清洗成 python 的 bool
            value = self.filter_bool(config_entry.value)
            if key == DEFAULT_QUERY_TEMPLATE_KEY:
                self._set_redis_value(
                    DEFAULT_QUERY_TEMPLATE_CACHE_KEY, str(config_entry.value)
                )
        # 是字符串的话, 如果是空, 或者全是空格, 返回默认值
        if isinstance(value, str) and value.strip() == "":
            return default_value
        if value is not None:
            self.sys_config[key] = value
            return value
        return default_value

    @staticmethod
    def filter_bool(value: str):
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False
        return value

    def set(self, key, value):
        if value is True:
            db_value = "true"
        elif value is False:
            db_value = "false"
        else:
            db_value = value
        obj, created = Config.objects.update_or_create(
            item=key, defaults={"value": db_value}
        )
        self.sys_config.update({key: value})

    def replace(self, configs):
        result = {"status": 0, "msg": "ok", "data": []}
        # 清空并替换
        try:
            config_list = json.loads(configs)
            default_query_template_value = None
            db_configs = []
            for items in config_list:
                config_key = items["key"].strip()
                config_value = str(items["value"]).strip()
                if config_key == DEFAULT_QUERY_TEMPLATE_KEY:
                    default_query_template_value = config_value
                    continue
                db_configs.append(Config(item=config_key, value=config_value))
            if default_query_template_value is not None:
                self._set_redis_value(
                    DEFAULT_QUERY_TEMPLATE_CACHE_KEY, default_query_template_value
                )
            with transaction.atomic():
                self.purge()
                Config.objects.bulk_create(db_configs)
        except Exception as e:
            logger.error(traceback.format_exc())
            result["status"] = 1
            result["msg"] = str(e)
        finally:
            self.get_all_config()
        return result

    def purge(self):
        """清除所有配置, 供测试以及replace方法使用"""
        try:
            with transaction.atomic():
                Config.objects.all().delete()
                self.sys_config = {}
        except Exception as m:
            logger.error(f"删除缓存失败:{m}{traceback.format_exc()}")

    @staticmethod
    def _get_redis_connection():
        try:
            return get_redis_connection("default")
        except Exception as e:
            logger.error(f"获取redis连接失败:{e}")
            return None

    def _get_redis_value(self, key):
        redis_conn = self._get_redis_connection()
        if not redis_conn:
            return None
        try:
            value = redis_conn.get(key)
            if isinstance(value, bytes):
                return value.decode("utf8")
            return value
        except Exception as e:
            logger.error(f"读取redis缓存失败:{e}")
            return None

    def _set_redis_value(self, key, value):
        redis_conn = self._get_redis_connection()
        if not redis_conn:
            return
        try:
            redis_conn.set(key, value)
            self.sys_config[DEFAULT_QUERY_TEMPLATE_KEY] = value
        except Exception as e:
            logger.error(f"写入redis缓存失败:{e}")


# 修改系统配置
@superuser_required
def change_config(request):
    configs = request.POST.get("configs")
    archer_config = SysConfig()
    result = archer_config.replace(configs)
    # 返回结果
    return HttpResponse(json.dumps(result), content_type="application/json")
