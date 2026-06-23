-- =============================================
-- 知识库数据修复脚本
-- 说明：此脚本将从 content 字段中提取 title 信息
-- 创建日期: 2026-06-08
-- =============================================

-- 方案 1: 从 content 字段中提取标题并更新
-- 这个脚本会解析 content 字段中的 "标题:" 行，并提取出实际的标题

UPDATE knowledge 
SET 
    title = CASE
        -- 尝试从 content 中提取 "- 标题:" 后面的内容
        WHEN content LIKE '%- 标题:%' THEN 
            TRIM(SUBSTRING_INDEX(SUBSTRING_INDEX(content, '- 标题:', -1), '\n', 1))
        -- 如果没有找到，尝试从 "- ID:" 和 "- 标题:" 之间提取
        WHEN content LIKE '%ID:%' THEN
            TRIM(SUBSTRING_INDEX(SUBSTRING_INDEX(content, '\n', 2), '\n', -1))
        ELSE title
    END,
    type = CASE
        -- 从 "- 类型:" 行中提取类型
        WHEN content LIKE '%类型: 文档%' OR content LIKE '%类型: 文 档%' THEN 'doc'
        WHEN content LIKE '%类型: 图片%' THEN 'image'
        WHEN content LIKE '%类型: 视频%' THEN 'video'
        ELSE 'other'
    END
WHERE title = '' OR title IS NULL;

-- 方案 2: 针对特定记录手动更新（根据API返回的数据）
-- 如果上面的自动提取失败，可以使用这些具体的更新语句

-- ID=1 和 ID=6 是同一条记录 (IMG_20260604_073005)
UPDATE knowledge SET title = 'IMG_20260604_073005', type = 'image' WHERE id IN ('1', '6') AND (title = '' OR title IS NULL);

-- ID=2 和 ID=7 是同一条记录 (猪肉对不同人的好处和坏处)
UPDATE knowledge SET title = '猪肉对不同人的好处和坏处', type = 'doc' WHERE id IN ('2', '7') AND (title = '' OR title IS NULL);

-- ID=3 和 ID=8 是同一条记录 (建模数据121-2)
UPDATE knowledge SET title = '建模数据121-2', type = 'doc' WHERE id IN ('3', '8') AND (title = '' OR title IS NULL);

-- ID=4 和 ID=9 是同一条记录 (微信图片2_20260522103342_111_2)
UPDATE knowledge SET title = '微信图片2_20260522103342_111_2', type = 'image' WHERE id IN ('4', '9') AND (title = '' OR title IS NULL);

-- ID=5 和 ID=10 是知识库索引文件
UPDATE knowledge SET title = '知识库资料索引', type = 'other' WHERE id IN ('5', '10') AND (title = '' OR title IS NULL);

-- 方案 3: 更新 total_size 和 attachment_count
-- 从 content 字段中提取这些信息

UPDATE knowledge 
SET 
    total_size = CASE
        WHEN content LIKE '%总大小: 7.36 MB%' THEN 7716045  -- 7.36 MB in bytes
        WHEN content LIKE '%总大小: 5.7 KB%' THEN 5837       -- 5.7 KB in bytes
        WHEN content LIKE '%总大小: 110.7 KB%' THEN 113357  -- 110.7 KB in bytes
        WHEN content LIKE '%总大小: 42.9 KB%' THEN 43930    -- 42.9 KB in bytes
        ELSE 0
    END,
    attachment_count = CASE
        WHEN content LIKE '%附件数量: 1%' THEN 1
        WHEN content LIKE '%附件数量: 2%' THEN 2
        ELSE 0
    END
WHERE (total_size = 0 OR total_size IS NULL) OR (attachment_count = 0 OR attachment_count IS NULL);

-- 查看更新后的结果
SELECT id, title, type, total_size, attachment_count, created_at 
FROM knowledge 
ORDER BY created_at DESC;
