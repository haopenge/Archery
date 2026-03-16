CREATE TABLE `ai_dict` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `create_time` datetime(6) NOT NULL,
  `update_time` datetime(6) NOT NULL,
  `instance` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `db` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `table` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `properties` longtext COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ai_dict_instance_db_table_be301858_uniq` (`instance`,`db`,`table`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET @content_type_id=(SELECT id FROM django_content_type WHERE app_label='sql' AND model='permission');
INSERT IGNORE INTO auth_permission (name, content_type_id, codename)
VALUES
  ('菜单 AI字典', @content_type_id, 'menu_ai_dict'),
  ('管理AI提示词模板', @content_type_id, 'ai_dict_manage_template');

