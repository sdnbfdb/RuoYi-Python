-- 知识库表结构迁移脚本
-- 执行此脚本前请备份数据！

-- 1. 备份旧表数据（如果有）
CREATE TABLE IF NOT EXISTS `knowledge_backup` AS SELECT * FROM `knowledge`;

-- 2. 删除旧表
DROP TABLE IF EXISTS `knowledge`;

-- 3. 创建新表结构
CREATE TABLE `knowledge` (
  `id` VARCHAR(32) NOT NULL COMMENT '主键ID',
  `title` VARCHAR(255) NOT NULL COMMENT '标题',
  `type` VARCHAR(50) DEFAULT 'other' COMMENT '类型（doc/video/image/other）',
  `tags` JSON DEFAULT NULL COMMENT '标签（JSON数组）',
  `description` TEXT COMMENT '描述',
  `content` LONGTEXT COMMENT '内容',
  `attachments` JSON DEFAULT NULL COMMENT '附件列表（JSON数组）',
  `qa_records` JSON DEFAULT NULL COMMENT '问答记录（JSON数组）',
  `created_by` VARCHAR(100) DEFAULT NULL COMMENT '创建人',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
  `total_size` BIGINT DEFAULT 0 COMMENT '总大小（字节）',
  `attachment_count` INT DEFAULT 0 COMMENT '附件数量',
  PRIMARY KEY (`id`),
  INDEX `idx_title` (`title`),
  INDEX `idx_type` (`type`),
  INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识库表';

-- 4. 迁移旧数据（如果需要）
-- 将旧的file_name映射为title，file_type映射为type等
-- INSERT INTO `knowledge` (id, title, type, description, content, created_at, updated_at, total_size)
-- SELECT 
--   CAST(id AS CHAR),
--   file_name,
--   CASE
--     WHEN file_type IN ('pdf', 'doc', 'docx', 'txt', 'md') THEN 'doc'
--     WHEN file_type IN ('jpg', 'jpeg', 'png', 'gif') THEN 'image'
--     WHEN file_type IN ('mp4', 'avi', 'mov') THEN 'video'
--     ELSE 'other'
--   END,
--   NULL,
--   content,
--   created_at,
--   updated_at,
--   file_size
-- FROM `knowledge_backup`;

-- 提示：取消上面INSERT语句的注释来迁移旧数据
