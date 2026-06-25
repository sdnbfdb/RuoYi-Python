-- =============================================
-- 数据库初始化脚本
-- 创建日期: 2026-06-08
-- =============================================

-- ----------------------------
-- 表结构：organization（组织架构）
-- ----------------------------
DROP TABLE IF EXISTS `organization`;
CREATE TABLE `organization` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name` VARCHAR(255) NOT NULL COMMENT '部门名称',
  `superior_department` VARCHAR(255) DEFAULT NULL COMMENT '上级部门',
  `below_department` TEXT COMMENT '下级部门（逗号分隔）',
  `create_date` DATETIME COMMENT '创建日期',
  `functionary` VARCHAR(255) DEFAULT NULL COMMENT '负责人',
  `role` VARCHAR(50) DEFAULT NULL COMMENT '角色',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
  PRIMARY KEY (`id`),
  INDEX `idx_name` (`name`),
  INDEX `idx_superior` (`superior_department`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='组织架构表';

-- ----------------------------
-- 表结构：knowledge（知识库）
-- ----------------------------
DROP TABLE IF EXISTS `knowledge`;
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

-- ----------------------------
-- 表结构：chat_history（对话历史）
-- ----------------------------
DROP TABLE IF EXISTS `chat_history`;
CREATE TABLE `chat_history` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `conversation_id` VARCHAR(64) NOT NULL COMMENT '会话ID',
  `role` VARCHAR(20) NOT NULL COMMENT '角色（user/assistant/system）',
  `content` LONGTEXT NOT NULL COMMENT '消息内容',
  `robot_name` VARCHAR(50) DEFAULT NULL COMMENT '机器人名称',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
  PRIMARY KEY (`id`),
  INDEX `idx_conversation_id` (`conversation_id`),
  INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话历史表';

-- ----------------------------
-- 表结构：users（用户表）
-- ----------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `username` VARCHAR(100) NOT NULL COMMENT '用户名',
  `password` VARCHAR(255) NOT NULL COMMENT '密码（加密）',
  `email` VARCHAR(255) DEFAULT NULL COMMENT '邮箱',
  `department` VARCHAR(255) DEFAULT NULL COMMENT '所属部门',
  `role` VARCHAR(50) DEFAULT 'user' COMMENT '角色（admin/user）',
  `status` TINYINT DEFAULT 1 COMMENT '状态（1启用/0禁用）',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
  PRIMARY KEY (`id`),
  UNIQUE INDEX `idx_username` (`username`),
  INDEX `idx_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ----------------------------
-- 表结构：upload_files（上传文件）
-- ----------------------------
DROP TABLE IF EXISTS `upload_files`;
CREATE TABLE `upload_files` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `original_name` VARCHAR(255) NOT NULL COMMENT '原始文件名',
  `storage_name` VARCHAR(255) NOT NULL COMMENT '存储文件名',
  `file_path` VARCHAR(500) NOT NULL COMMENT '文件路径',
  `file_size` BIGINT DEFAULT 0 COMMENT '文件大小（字节）',
  `file_type` VARCHAR(50) DEFAULT NULL COMMENT '文件类型',
  `upload_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  PRIMARY KEY (`id`),
  INDEX `idx_storage_name` (`storage_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='上传文件表';

-- ----------------------------
-- 表结构：search_logs（搜索日志）
-- ----------------------------
DROP TABLE IF EXISTS `search_logs`;
CREATE TABLE `search_logs` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `query` TEXT NOT NULL COMMENT '搜索关键词',
  `result_count` INT DEFAULT 0 COMMENT '搜索结果数量',
  `search_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '搜索时间',
  PRIMARY KEY (`id`),
  INDEX `idx_search_time` (`search_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='搜索日志表';

-- ----------------------------
-- 插入初始用户数据
-- ----------------------------
INSERT INTO `users` (`username`, `password`, `email`, `department`, `role`, `status`) VALUES
('admin', 'admin123', 'admin@example.com', '总部', 'admin', 1),
('sanjin', '123456', 'sanjin@example.com', '部门1', 'user', 1);

-- ----------------------------
-- 插入初始组织架构数据（从 organization.txt 提取）
-- ----------------------------
INSERT INTO `organization` (`name`, `superior_department`, `below_department`, `create_date`, `functionary`, `role`) VALUES
('总部', '无', '部门1,部门2,部门3,部门4,部门5,部门6,部门7,部门8,部门9,部门10', '2026-01-01 00:00:00', 'sanjin', '0'),
('部门1', '总部', '部门1.1,部门1.2,部门1.3,部门1.4,部门1.5', '2026-01-02 00:00:00', '部门1经理', '1'),
('部门2', '总部', '部门2.1,部门2.2,部门2.3,部门2.4,部门2.5', '2026-01-03 00:00:00', '部门2经理', '2'),
('部门3', '总部', '部门3.1,部门3.2,部门3.3,部门3.4,部门3.5', '2026-01-04 00:00:00', '部门3经理', '3'),
('部门4', '总部', '部门4.1,部门4.2,部门4.3,部门4.4,部门4.5', '2026-01-05 00:00:00', '部门4经理', '4'),
('部门5', '总部', '部门5.1,部门5.2,部门5.3,部门5.4,部门5.5', '2026-01-06 00:00:00', '部门5经理', '5'),
('部门6', '总部', '部门6.1,部门6.2,部门6.3,部门6.4,部门6.5', '2026-01-07 00:00:00', '部门6经理', '6'),
('部门7', '总部', '部门7.1,部门7.2,部门7.3,部门7.4,部门7.5', '2026-01-08 00:00:00', '部门7经理', '7'),
('部门8', '总部', '部门8.1,部门8.2,部门8.3,部门8.4,部门8.5', '2026-01-09 00:00:00', '部门8经理', '8'),
('部门9', '总部', '部门9.1,部门9.2,部门9.3,部门9.4,部门9.5', '2026-01-10 00:00:00', '部门9经理', '9'),
('部门10', '总部', '', '2026-01-11 00:00:00', '部门10经理', '10'),
('部门1.1', '部门1', '部门1.1.1,部门1.1.2,部门1.1.3,部门1.1.4,部门1.1.5,部门1.1.6,部门1.1.7,部门1.1.8,部门1.1.9,部门1.1.10,部门1.1.11,部门1.1.12,部门1.1.13,部门1.1.14,部门1.1.15,部门1.1.16,部门1.1.17,部门1.1.18,部门1.1.19,部门1.1.20,部门1.1.21,部门1.1.22,部门1.1.23,部门1.1.24,部门1.1.25,部门1.1.26,部门1.1.27,部门1.1.28,部门1.1.29,部门1.1.30', '2026-01-12 00:00:00', '主管', '1.1'),
('部门1.2', '部门1', '部门1.2.1,部门1.2.2,部门1.2.3,部门1.2.4,部门1.2.5,部门1.2.6,部门1.2.7,部门1.2.8,部门1.2.9,部门1.2.10,部门1.2.11,部门1.2.12,部门1.2.13,部门1.2.14,部门1.2.15,部门1.2.16,部门1.2.17,部门1.2.18,部门1.2.19,部门1.2.20,部门1.2.21,部门1.2.22,部门1.2.23,部门1.2.24,部门1.2.25,部门1.2.26,部门1.2.27,部门1.2.28,部门1.2.29,部门1.2.30', '2026-01-13 00:00:00', '主管', '1.2'),
('部门1.3', '部门1', '部门1.3.1,部门1.3.2,部门1.3.3,部门1.3.4,部门1.3.5,部门1.3.6,部门1.3.7,部门1.3.8,部门1.3.9,部门1.3.10,部门1.3.11,部门1.3.12,部门1.3.13,部门1.3.14,部门1.3.15,部门1.3.16,部门1.3.17,部门1.3.18,部门1.3.19,部门1.3.20,部门1.3.21,部门1.3.22,部门1.3.23,部门1.3.24,部门1.3.25,部门1.3.26,部门1.3.27,部门1.3.28,部门1.3.29,部门1.3.30', '2026-01-14 00:00:00', '主管', '1.3'),
('部门1.4', '部门1', '部门1.4.1,部门1.4.2,部门1.4.3,部门1.4.4,部门1.4.5,部门1.4.6,部门1.4.7,部门1.4.8,部门1.4.9,部门1.4.10,部门1.4.11,部门1.4.12,部门1.4.13,部门1.4.14,部门1.4.15,部门1.4.16,部门1.4.17,部门1.4.18,部门1.4.19,部门1.4.20,部门1.4.21,部门1.4.22,部门1.4.23,部门1.4.24,部门1.4.25,部门1.4.26,部门1.4.27,部门1.4.28,部门1.4.29,部门1.4.30', '2026-01-15 00:00:00', '主管', '1.4'),
('部门1.5', '部门1', '部门1.5.1,部门1.5.2,部门1.5.3,部门1.5.4,部门1.5.5,部门1.5.6,部门1.5.7,部门1.5.8,部门1.5.9,部门1.5.10,部门1.5.11,部门1.5.12,部门1.5.13,部门1.5.14,部门1.5.15,部门1.5.16,部门1.5.17,部门1.5.18,部门1.5.19,部门1.5.20,部门1.5.21,部门1.5.22,部门1.5.23,部门1.5.24,部门1.5.25,部门1.5.26,部门1.5.27,部门1.5.28,部门1.5.29,部门1.5.30', '2026-01-16 00:00:00', '主管', '1.5');