-- GB 2760-2024 食品添加剂数据库设计（完全匹配版）
-- 与 final_gb2760_data.xlsx 文件结构完全匹配
-- 支持清空旧数据重新导入
-- 更新日期：2024年

-- 创建数据库
CREATE DATABASE IF NOT EXISTS gb2760_db 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE gb2760_db;

-- 设置外键检查（导入数据时需要关闭）
SET FOREIGN_KEY_CHECKS = 0;

-- 清空旧数据（按依赖顺序删除表）
DROP TABLE IF EXISTS category_additive;
DROP TABLE IF EXISTS additive_usage;
DROP TABLE IF EXISTS flavor;
DROP TABLE IF EXISTS enzyme;
DROP TABLE IF EXISTS processing_aid;
DROP TABLE IF EXISTS additive;
DROP TABLE IF EXISTS food_category;

-- =====================================
-- 1. 食品添加剂表 (additive)
-- 匹配 "添加剂基本信息" 工作表结构
-- =====================================
CREATE TABLE additive (
    id INT NOT NULL COMMENT '添加剂ID（来自数据文件）',
    name_zh VARCHAR(255) NOT NULL COMMENT '添加剂中文名称',
    name_en VARCHAR(1200) COMMENT '添加剂英文名称',
    cns_code VARCHAR(300) COMMENT 'CNS编码，中国食品添加剂编号',
    ins_code VARCHAR(300) COMMENT 'INS编码，国际食品添加剂编号', 
    function_category TEXT COMMENT '功能类别',
    detail_url TEXT COMMENT '详情页URL',
    quality_standard TEXT COMMENT '质量规格标准',
    jecfa_spec TEXT COMMENT 'JECFA规格资料',
    remarks TEXT COMMENT '备注信息',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    PRIMARY KEY (id),
    UNIQUE KEY uk_name_zh (name_zh),
    
    -- 索引设计
    INDEX idx_name_zh (name_zh),
    INDEX idx_name_en (name_en(255)),
    INDEX idx_cns_code (cns_code(255)),
    INDEX idx_ins_code (ins_code(255)),
    
    -- 全文检索索引
    FULLTEXT idx_ft_names (name_zh, name_en) WITH PARSER ngram
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='食品添加剂表';

-- =====================================
-- 2. 添加剂使用限量表 (additive_usage)
-- 匹配 "添加剂使用限量" 工作表结构
-- =====================================
CREATE TABLE additive_usage (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    additive_id INT NOT NULL COMMENT '添加剂ID',
    additive_name VARCHAR(300) NOT NULL COMMENT '添加剂名称', 
    category_code VARCHAR(100) COMMENT '食品分类编码',
    food_name VARCHAR(600) COMMENT '食品名称',
    max_usage VARCHAR(200) COMMENT '最大使用量（包含单位）',
    usage_remarks TEXT COMMENT '使用备注',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 索引设计
    INDEX idx_additive_id (additive_id),
    INDEX idx_additive_name (additive_name(255)),
    INDEX idx_category_code (category_code),
    INDEX idx_food_name (food_name(255)),
    
    -- 全文检索索引  
    FULLTEXT idx_ft_food_name (food_name) WITH PARSER ngram
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='添加剂使用限量表';

-- =====================================
-- 3. 食品分类表 (food_category)
-- 匹配 "分类基本信息" 工作表结构
-- =====================================
CREATE TABLE food_category (
    id INT NOT NULL COMMENT '分类 ID（来自数据文件）',
    category_code VARCHAR(100) NOT NULL COMMENT '食品分类编码，如"01.01.01"',
    category_name VARCHAR(300) NOT NULL COMMENT '食品名称',
    detail_url TEXT COMMENT '详情页URL',
    description TEXT COMMENT '食品名称描述',
    standards TEXT COMMENT '相关食品标准',
    parent_code VARCHAR(50) COMMENT '父分类编码，实现层级结构',
    level TINYINT DEFAULT 1 COMMENT '分类层级，1为一级分类',
    sort_order INT DEFAULT 0 COMMENT '排序顺序', 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    PRIMARY KEY (id),
    UNIQUE KEY uk_category_code (category_code),
    
    -- 索引设计
    INDEX idx_category_code (category_code),
    INDEX idx_category_name (category_name(255)),
    INDEX idx_parent_code (parent_code),
    INDEX idx_level (level),
    INDEX idx_sort_order (sort_order),
    
    -- 全文检索索引
    FULLTEXT idx_ft_name_desc (category_name, description) WITH PARSER ngram
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='食品分类表，支持层级结构';

-- =====================================
-- 4. 分类-添加剂关联表 (category_additive)
-- 匹配 "分类-添加剂关联" 工作表结构
-- =====================================
CREATE TABLE category_additive (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    category_id INT NOT NULL COMMENT '分类ID',
    category_code VARCHAR(100) NOT NULL COMMENT '分类编码',
    category_name VARCHAR(300) COMMENT '分类名称',
    additive_name VARCHAR(300) NOT NULL COMMENT '添加剂名称',
    `function` VARCHAR(100) COMMENT '功能',
    max_usage VARCHAR(200) COMMENT '最大使用量',
    cns_code VARCHAR(300) COMMENT 'CNS编码',
    ins_code VARCHAR(300) COMMENT 'INS编码',
    remarks TEXT COMMENT '备注',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 索引设计
    INDEX idx_category_id (category_id),
    INDEX idx_category_code (category_code),
    INDEX idx_additive_name (additive_name(255)),
    INDEX idx_cns_code (cns_code(255)),
    INDEX idx_ins_code (ins_code(255)),
    
    -- 全文检索索引
    FULLTEXT idx_ft_additive_name (additive_name) WITH PARSER ngram
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='分类-添加剂关联表，记录使用限制';

-- =====================================
-- 5. 加工助剂表 (processing_aid)
-- 匹配 "加工助剂" 工作表结构
-- =====================================
CREATE TABLE processing_aid (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    name_zh VARCHAR(300) NOT NULL COMMENT '中文名称',
    name_en VARCHAR(300) COMMENT '英文名称',
    `function` VARCHAR(100) COMMENT '功能描述',
    usage_scope TEXT COMMENT '使用范围描述',
    cas_number VARCHAR(50) COMMENT 'CAS号',
    remarks TEXT COMMENT '备注信息',
    raw_data TEXT COMMENT '原始数据',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 索引设计
    INDEX idx_name_zh (name_zh(255)),
    INDEX idx_name_en (name_en(255)),
    INDEX idx_cas_number (cas_number),
    INDEX idx_function (`function`),
    
    -- 全文检索索引
    FULLTEXT idx_ft_names (name_zh, name_en) WITH PARSER ngram,
    FULLTEXT idx_ft_function_scope (`function`, usage_scope) WITH PARSER ngram
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='加工助剂表';

-- =====================================
-- 6. 酶制剂表 (enzyme)
-- 匹配 "酶制剂" 工作表结构
-- =====================================
CREATE TABLE enzyme (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    name_zh VARCHAR(100) NOT NULL COMMENT '中文名称',
    name_en VARCHAR(200) COMMENT '英文名称',
    enzyme_source TEXT COMMENT '来源，生产该酶的微生物或组织',
    usage_scope TEXT COMMENT '使用范围',
    ec_number VARCHAR(50) COMMENT 'EC编号',
    cas_number VARCHAR(50) COMMENT 'CAS号',
    remarks TEXT COMMENT '备注信息，如批准公告编号',
    raw_data TEXT COMMENT '原始数据',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 索引设计
    INDEX idx_name_zh (name_zh),
    INDEX idx_name_en (name_en),
    INDEX idx_cas_number (cas_number),
    INDEX idx_ec_number (ec_number),
    INDEX idx_enzyme_source (enzyme_source(255)),
    
    -- 全文检索索引
    FULLTEXT idx_ft_names (name_zh, name_en) WITH PARSER ngram,
    FULLTEXT idx_ft_source (enzyme_source) WITH PARSER ngram
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='酶制剂表';

-- =====================================
-- 7. 香精香料表 (flavor)
-- 匹配 "香精香料" 工作表结构
-- =====================================
CREATE TABLE flavor (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    category VARCHAR(100) NOT NULL COMMENT '类别，如B.1、B.2、B.3',
    name_zh VARCHAR(200) NOT NULL COMMENT '中文名称',
    name_en VARCHAR(300) COMMENT '英文名称',
    type VARCHAR(50) COMMENT '类型',
    code VARCHAR(50) COMMENT '列表编号',
    fema_no VARCHAR(20) COMMENT 'FEMA编号',
    classification_table VARCHAR(20) COMMENT '分类表，B.1/B.2/B.3',
    remarks TEXT COMMENT '备注信息',
    raw_data TEXT COMMENT '原始数据',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 索引设计
    INDEX idx_name_zh (name_zh),
    INDEX idx_name_en (name_en),
    INDEX idx_code (code),
    INDEX idx_fema_no (fema_no),
    INDEX idx_category (category),
    INDEX idx_type (type),
    INDEX idx_classification_table (classification_table),
    
    -- 全文检索索引
    FULLTEXT idx_ft_names (name_zh, name_en) WITH PARSER ngram
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='香精香料表';

-- 重新启用外键检查
SET FOREIGN_KEY_CHECKS = 1;

-- =====================================
-- 数据导入辅助视图
-- =====================================

-- 添加剂完整信息视图
CREATE VIEW v_additive_full_info AS
SELECT 
    a.id as additive_id,
    a.name_zh,
    a.name_en,
    a.function_category,
    a.cns_code,
    a.ins_code,
    a.quality_standard,
    a.jecfa_spec,
    a.remarks,
    COUNT(DISTINCT au.id) as usage_records,
    COUNT(DISTINCT ca.id) as category_associations,
    a.created_at,
    a.updated_at
FROM additive a
LEFT JOIN additive_usage au ON a.id = au.additive_id
LEFT JOIN category_additive ca ON a.name_zh = ca.additive_name
GROUP BY a.id;

-- 使用限量详细信息视图
CREATE VIEW v_usage_limit_details AS
SELECT 
    au.id,
    au.additive_id,
    au.additive_name,
    au.category_code,
    au.food_name,
    au.max_usage,
    au.usage_remarks,
    fc.category_name,
    fc.description as food_category_description,
    a.cns_code,
    a.ins_code,
    a.function_category
FROM additive_usage au
LEFT JOIN food_category fc ON au.category_code = fc.category_code
LEFT JOIN additive a ON au.additive_id = a.id;

-- 多对多关系验证视图
CREATE VIEW v_relationship_validation AS
SELECT 
    '添加剂→分类' as relationship_type,
    au.additive_name,
    au.category_code,
    au.food_name,
    au.max_usage,
    'additive_usage' as source_table
FROM additive_usage au
UNION ALL
SELECT 
    '分类→添加剂' as relationship_type,
    ca.additive_name,
    ca.category_code,
    ca.category_name,
    ca.max_usage,
    'category_additive' as source_table
FROM category_additive ca;

-- SQL脚本更新完成，与 final_gb2760_data.xlsx 文件结构完全匹配
-- 支持清空旧数据功能，可直接用于数据导入