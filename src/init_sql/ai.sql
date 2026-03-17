CREATE TABLE `ai_dict` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `create_time` datetime(6) NOT NULL,
  `update_time` datetime(6) NOT NULL,
  `instance` varchar(255)  NOT NULL,
  `db` varchar(255) NOT NULL,
  `table` varchar(255) NOT NULL,
  `properties` longtext NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ai_dict_instance_db_table_be301858_uniq` (`instance`,`db`,`table`)
);

SET @content_type_id=(SELECT id FROM django_content_type WHERE app_label='sql' AND model='permission');
INSERT IGNORE INTO auth_permission (name, content_type_id, codename)
VALUES
  ('菜单 AI字典', @content_type_id, 'menu_ai_dict'),
  ('管理AI提示词模板', @content_type_id, 'ai_dict_manage_template');


--  1.4.6
CREATE TABLE `ai_template` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `create_time` datetime(6) NOT NULL,
  `update_time` datetime(6) NOT NULL,
  `name` varchar(64) NOT NULL DEFAULT '' COMMENT '名称',
  `template` text  NOT NULL COMMENT '提示词模板',
  `create_id` int NOT NULL DEFAULT '0' COMMENT '创建用户',
  `update_id` int NOT NULL DEFAULT '0' COMMENT '更新用户',
  PRIMARY KEY (`id`)
) ;

ALTER TABLE `ai_dict` 
ADD COLUMN `create_id` int NOT NULL DEFAULT 0 COMMENT '创建用户',
ADD COLUMN `update_id` int NOT NULL DEFAULT 0 COMMENT '更新用户'
;
