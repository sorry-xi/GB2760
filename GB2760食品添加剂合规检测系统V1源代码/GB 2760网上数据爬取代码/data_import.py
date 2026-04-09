#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GB 2760数据导入脚本
将final_gb2760_data.xlsx中的数据导入到MySQL数据库
"""

import pandas as pd
import pymysql
import logging
from typing import Dict, List, Any
import sys
import os
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_import.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GB2760DataImporter:
    """GB 2760数据导入器"""
    
    def __init__(self, db_config: Dict[str, Any]):
        """初始化数据库配置"""
        self.db_config = db_config
        self.connection = None
        self.excel_file = 'final_gb2760_data.xlsx'
        
        # 统计信息
        self.import_stats = {
            'additive': 0,
            'additive_usage': 0,
            'food_category': 0,
            'category_additive': 0,
            'processing_aid': 0,
            'enzyme': 0,
            'flavor': 0
        }
        
    def connect_database(self) -> bool:
        """连接数据库"""
        try:
            self.connection = pymysql.connect(**self.db_config)
            logger.info("✅ 数据库连接成功")
            return True
        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {e}")
            return False
    
    def close_database(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            logger.info("📝 数据库连接已关闭")
    
    def check_and_setup_database(self) -> bool:
        """检查和设置数据库，清空表数据"""
        try:
            # 不指定数据库的连接
            temp_config = self.db_config.copy()
            if 'database' in temp_config:
                del temp_config['database']
            
            temp_connection = pymysql.connect(**temp_config)
            cursor = temp_connection.cursor()
            
            # 检查数据库是否存在
            cursor.execute("SHOW DATABASES LIKE 'gb2760_db'")
            db_exists = cursor.fetchone() is not None
            
            if not db_exists:
                logger.info("🆕 数据库gb2760_db不存在，创建数据库...")
                cursor.execute("CREATE DATABASE gb2760_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                logger.info("✅ 数据库创建成功")
            else:
                logger.info("🔍 数据库gb2760_db已存在")
            
            # 使用数据库
            cursor.execute("USE gb2760_db")
            
            # 检查表是否存在
            cursor.execute("SHOW TABLES")
            tables = [table[0] for table in cursor.fetchall()]
            
            if tables:
                logger.info(f"📋 发现 {len(tables)} 个表，清空表数据...")
                
                # 关闭外键检查
                cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
                
                # 清空所有表数据（保留表结构）
                for table in tables:
                    try:
                        cursor.execute(f"TRUNCATE TABLE {table}")
                        logger.info(f"  ✅ 清空表数据: {table}")
                    except Exception as e:
                        # 如果是视图，则删除
                        try:
                            cursor.execute(f"DROP VIEW IF EXISTS {table}")
                            logger.info(f"  ✅ 删除视图: {table}")
                        except Exception as e2:
                            logger.warning(f"  ⚠️ 处理表失败 {table}: {e2}")
                
                # 重新启用外键检查
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
                
                logger.info("🧹 表数据清空完成")
            else:
                logger.info("📋 数据库为空，无需清理")
            
            temp_connection.commit()
            cursor.close()
            temp_connection.close()
            
            # 重新连接到指定数据库
            self.db_config['database'] = 'gb2760_db'
            if self.connection:
                self.connection.close()
            self.connection = pymysql.connect(**self.db_config)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 数据库设置失败: {e}")
            return False
    
    def execute_sql_file(self, sql_file: str) -> bool:
        """执行SQL文件"""
        try:
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # 分割SQL语句（简单分割，忽略注释中的分号）
            sql_statements = []
            current_statement = ""
            in_comment = False
            
            for line in sql_content.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith('--'):
                    continue
                    
                current_statement += line + " "
                
                if line.endswith(';'):
                    if current_statement.strip():
                        sql_statements.append(current_statement.strip())
                    current_statement = ""
            
            cursor = self.connection.cursor()
            
            for sql in sql_statements:
                if sql.strip() and not sql.strip().startswith('--'):
                    try:
                        cursor.execute(sql)
                    except Exception as e:
                        logger.warning(f"SQL执行警告: {str(e)[:100]}...")
                        continue
            
            self.connection.commit()
            cursor.close()
            logger.info(f"✅ SQL文件执行完成: {sql_file}")
            return True
            
        except Exception as e:
            logger.error(f"❌ SQL文件执行失败: {e}")
            return False
    
    def import_additives(self) -> bool:
        """导入添加剂基本信息"""
        try:
            logger.info("📊 开始导入添加剂基本信息...")
            
            df = pd.read_excel(self.excel_file, sheet_name='添加剂基本信息')
            logger.info(f"读取到 {len(df)} 条添加剂基本信息")
            
            cursor = self.connection.cursor()
            
            sql = """
            INSERT INTO additive (
                id, name_zh, name_en, cns_code, ins_code, 
                function_category, detail_url, quality_standard, 
                jecfa_spec, remarks
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            success_count = 0
            for _, row in df.iterrows():
                try:
                    values = (
                        row['id'],
                        row['name_zh'],
                        row['name_en'] if pd.notna(row['name_en']) else None,
                        row['cns_code'] if pd.notna(row['cns_code']) else None,
                        row['ins_code'] if pd.notna(row['ins_code']) else None,
                        row['function_category'] if pd.notna(row['function_category']) else None,
                        row['detail_url'] if pd.notna(row['detail_url']) else None,
                        row['quality_standard'] if pd.notna(row['quality_standard']) else None,
                        row['jecfa_spec'] if pd.notna(row['jecfa_spec']) else None,
                        row['remarks'] if pd.notna(row['remarks']) else None
                    )
                    
                    cursor.execute(sql, values)
                    success_count += 1
                    
                except Exception as e:
                    logger.warning(f"导入添加剂失败: {row['name_zh']} - {e}")
                    continue
            
            self.connection.commit()
            cursor.close()
            
            self.import_stats['additive'] = success_count
            logger.info(f"✅ 添加剂基本信息导入完成: {success_count}/{len(df)}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 导入添加剂基本信息失败: {e}")
            return False
    
    def import_additive_usage(self) -> bool:
        """导入添加剂使用限量"""
        try:
            logger.info("📊 开始导入添加剂使用限量...")
            
            df = pd.read_excel(self.excel_file, sheet_name='添加剂使用限量')
            logger.info(f"读取到 {len(df)} 条添加剂使用限量记录")
            
            cursor = self.connection.cursor()
            
            sql = """
            INSERT INTO additive_usage (
                additive_id, additive_name, category_code, 
                food_name, max_usage, usage_remarks
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            success_count = 0
            batch_size = 1000
            batch_data = []
            
            for _, row in df.iterrows():
                try:
                    values = (
                        row['additive_id'],
                        row['additive_name'],
                        row['category_code'] if pd.notna(row['category_code']) else None,
                        row['food_name'] if pd.notna(row['food_name']) else None,
                        row['max_usage'] if pd.notna(row['max_usage']) else None,
                        row['usage_remarks'] if pd.notna(row['usage_remarks']) else None
                    )
                    
                    batch_data.append(values)
                    
                    if len(batch_data) >= batch_size:
                        cursor.executemany(sql, batch_data)
                        success_count += len(batch_data)
                        batch_data = []
                        
                        if success_count % 5000 == 0:
                            logger.info(f"已导入 {success_count} 条使用限量记录")
                    
                except Exception as e:
                    logger.warning(f"导入使用限量失败: {row['additive_name']} - {e}")
                    continue
            
            # 导入剩余批次
            if batch_data:
                cursor.executemany(sql, batch_data)
                success_count += len(batch_data)
            
            self.connection.commit()
            cursor.close()
            
            self.import_stats['additive_usage'] = success_count
            logger.info(f"✅ 添加剂使用限量导入完成: {success_count}/{len(df)}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 导入添加剂使用限量失败: {e}")
            return False
    
    def import_food_categories(self) -> bool:
        """导入食品分类基本信息"""
        try:
            logger.info("📊 开始导入食品分类基本信息...")
            
            df = pd.read_excel(self.excel_file, sheet_name='分类基本信息')
            logger.info(f"读取到 {len(df)} 条分类基本信息")
            
            cursor = self.connection.cursor()
            
            sql = """
            INSERT INTO food_category (
                id, category_code, category_name, 
                detail_url, description, standards
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            success_count = 0
            for _, row in df.iterrows():
                try:
                    values = (
                        row['id'],
                        row['category_code'],
                        row['category_name'],
                        row['detail_url'] if pd.notna(row['detail_url']) else None,
                        row['description'] if pd.notna(row['description']) else None,
                        row['standards'] if pd.notna(row['standards']) else None
                    )
                    
                    cursor.execute(sql, values)
                    success_count += 1
                    
                except Exception as e:
                    logger.warning(f"导入分类失败: {row['category_name']} - {e}")
                    continue
            
            self.connection.commit()
            cursor.close()
            
            self.import_stats['food_category'] = success_count
            logger.info(f"✅ 食品分类基本信息导入完成: {success_count}/{len(df)}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 导入食品分类基本信息失败: {e}")
            return False
    
    def import_category_additives(self) -> bool:
        """导入分类-添加剂关联"""
        try:
            logger.info("📊 开始导入分类-添加剂关联...")
            
            df = pd.read_excel(self.excel_file, sheet_name='分类-添加剂关联')
            logger.info(f"读取到 {len(df)} 条分类-添加剂关联记录")
            
            cursor = self.connection.cursor()
            
            sql = """
            INSERT INTO category_additive (
                category_id, category_code, category_name, additive_name,
                `function`, max_usage, cns_code, ins_code, remarks
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            success_count = 0
            batch_size = 1000
            batch_data = []
            
            for _, row in df.iterrows():
                try:
                    values = (
                        row['category_id'],
                        row['category_code'],
                        row['category_name'] if pd.notna(row['category_name']) else None,
                        row['additive_name'],
                        row['function'] if pd.notna(row['function']) else None,
                        row['max_usage'] if pd.notna(row['max_usage']) else None,
                        row['cns_code'] if pd.notna(row['cns_code']) else None,
                        row['ins_code'] if pd.notna(row['ins_code']) else None,
                        row['remarks'] if pd.notna(row['remarks']) else None
                    )
                    
                    batch_data.append(values)
                    
                    if len(batch_data) >= batch_size:
                        cursor.executemany(sql, batch_data)
                        success_count += len(batch_data)
                        batch_data = []
                        
                        if success_count % 5000 == 0:
                            logger.info(f"已导入 {success_count} 条关联记录")
                    
                except Exception as e:
                    logger.warning(f"导入关联失败: {row['additive_name']} - {e}")
                    continue
            
            # 导入剩余批次
            if batch_data:
                cursor.executemany(sql, batch_data)
                success_count += len(batch_data)
            
            self.connection.commit()
            cursor.close()
            
            self.import_stats['category_additive'] = success_count
            logger.info(f"✅ 分类-添加剂关联导入完成: {success_count}/{len(df)}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 导入分类-添加剂关联失败: {e}")
            return False
    
    def import_other_data(self) -> bool:
        """导入其他数据（加工助剂、酶制剂、香精香料）"""
        
        # 导入加工助剂
        try:
            logger.info("📊 开始导入加工助剂...")
            df = pd.read_excel(self.excel_file, sheet_name='加工助剂')
            
            cursor = self.connection.cursor()
            sql = """
            INSERT INTO processing_aid (
                name_zh, name_en, `function`, usage_scope, 
                cas_number, remarks, raw_data
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            success_count = 0
            for _, row in df.iterrows():
                try:
                    values = (
                        row['name_zh'],
                        row['name_en'] if pd.notna(row['name_en']) else None,
                        row['function'] if pd.notna(row['function']) else None,
                        row['usage_scope'] if pd.notna(row['usage_scope']) else None,
                        row['cas_number'] if pd.notna(row['cas_number']) else None,
                        row['remarks'] if pd.notna(row['remarks']) else None,
                        row['raw_data'] if pd.notna(row['raw_data']) else None
                    )
                    cursor.execute(sql, values)
                    success_count += 1
                except Exception as e:
                    logger.warning(f"导入加工助剂失败: {row['name_zh']} - {e}")
            
            self.connection.commit()
            cursor.close()
            self.import_stats['processing_aid'] = success_count
            logger.info(f"✅ 加工助剂导入完成: {success_count}/{len(df)}")
            
        except Exception as e:
            logger.error(f"❌ 导入加工助剂失败: {e}")
        
        # 导入酶制剂
        try:
            logger.info("📊 开始导入酶制剂...")
            df = pd.read_excel(self.excel_file, sheet_name='酶制剂')
            
            cursor = self.connection.cursor()
            sql = """
            INSERT INTO enzyme (
                name_zh, name_en, enzyme_source, usage_scope,
                ec_number, cas_number, remarks, raw_data
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            success_count = 0
            for _, row in df.iterrows():
                try:
                    values = (
                        row['name_zh'],
                        row['name_en'] if pd.notna(row['name_en']) else None,
                        row['enzyme_source'] if pd.notna(row['enzyme_source']) else None,
                        row['usage_scope'] if pd.notna(row['usage_scope']) else None,
                        row['ec_number'] if pd.notna(row['ec_number']) else None,
                        row['cas_number'] if pd.notna(row['cas_number']) else None,
                        row['remarks'] if pd.notna(row['remarks']) else None,
                        row['raw_data'] if pd.notna(row['raw_data']) else None
                    )
                    cursor.execute(sql, values)
                    success_count += 1
                except Exception as e:
                    logger.warning(f"导入酶制剂失败: {row['name_zh']} - {e}")
            
            self.connection.commit()
            cursor.close()
            self.import_stats['enzyme'] = success_count
            logger.info(f"✅ 酶制剂导入完成: {success_count}/{len(df)}")
            
        except Exception as e:
            logger.error(f"❌ 导入酶制剂失败: {e}")
        
        # 导入香精香料
        try:
            logger.info("📊 开始导入香精香料...")
            df = pd.read_excel(self.excel_file, sheet_name='香精香料')
            
            cursor = self.connection.cursor()
            sql = """
            INSERT INTO flavor (
                category, name_zh, name_en, type, code,
                fema_no, classification_table, remarks, raw_data
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            success_count = 0
            batch_size = 500
            batch_data = []
            
            for _, row in df.iterrows():
                try:
                    values = (
                        row['category'],
                        row['name_zh'],
                        row['name_en'] if pd.notna(row['name_en']) else None,
                        row['type'] if pd.notna(row['type']) else None,
                        row['code'] if pd.notna(row['code']) else None,
                        row['fema_no'] if pd.notna(row['fema_no']) else None,
                        row['classification_table'] if pd.notna(row['classification_table']) else None,
                        row['remarks'] if pd.notna(row['remarks']) else None,
                        row['raw_data'] if pd.notna(row['raw_data']) else None
                    )
                    batch_data.append(values)
                    
                    if len(batch_data) >= batch_size:
                        cursor.executemany(sql, batch_data)
                        success_count += len(batch_data)
                        batch_data = []
                        
                except Exception as e:
                    logger.warning(f"导入香精香料失败: {row['name_zh']} - {e}")
            
            # 导入剩余批次
            if batch_data:
                cursor.executemany(sql, batch_data)
                success_count += len(batch_data)
            
            self.connection.commit()
            cursor.close()
            self.import_stats['flavor'] = success_count
            logger.info(f"✅ 香精香料导入完成: {success_count}/{len(df)}")
            
        except Exception as e:
            logger.error(f"❌ 导入香精香料失败: {e}")
        
        return True
    
    def print_import_summary(self):
        """打印导入总结"""
        print("\n" + "="*60)
        print("🎉 GB 2760数据导入完成！")
        print("="*60)
        
        total_records = sum(self.import_stats.values())
        
        for table_name, count in self.import_stats.items():
            table_display = {
                'additive': '添加剂基本信息',
                'additive_usage': '添加剂使用限量',
                'food_category': '食品分类基本信息',
                'category_additive': '分类-添加剂关联',
                'processing_aid': '加工助剂',
                'enzyme': '酶制剂',
                'flavor': '香精香料'
            }
            print(f"📊 {table_display[table_name]}: {count:,} 条")
        
        print(f"\n💾 总导入记录数: {total_records:,} 条")
        print(f"📅 导入时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📁 数据源: final_gb2760_data.xlsx")
        print(f"🗄️ 目标数据库: {self.db_config.get('database', 'gb2760_db')}")
        print("="*60)

def main():
    """主函数"""
    
    # 数据库配置（在这里设置您的MySQL密码）
    db_config = {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': '!a123456',  # 在这里填入您的MySQL密码，例如：'your_password'
        'charset': 'utf8mb4',
        'autocommit': False
    }
    
    print("🕷️ GB 2760-2024 数据导入工具")
    print("="*60)
    print("本工具将final_gb2760_data.xlsx中的数据导入到MySQL数据库")
    print("🔑 密码配置：如需修改MySQL密码，请在脚本中的db_config['password']处修改")
    print()
    
    # 检查密码是否已配置
    if not db_config['password']:
        password = input("请输入MySQL密码 (直接回车使用空密码): ")
        if password:
            db_config['password'] = password
    else:
        print(f"🔑 使用预设密码：{'*' * len(db_config['password'])}")
    
    print()
    
    # 创建导入器
    importer = GB2760DataImporter(db_config)
    
    # 连接数据库
    if not importer.connect_database():
        print("❌ 无法连接数据库，请检查配置")
        return
    
    try:
        # 0. 检查和设置数据库
        print("🔍 第零步：检查和设置数据库...")
        if importer.check_and_setup_database():
            print("✅ 数据库检查和设置成功")
        else:
            print("❌ 数据库设置失败")
            return
        
        print()
        
        # 1. 执行数据库结构脚本
        print("📋 第一步：创建数据库结构...")
        if importer.execute_sql_file('database_schema.sql'):
            print("✅ 数据库结构创建成功")
        else:
            print("❌ 数据库结构创建失败")
            return
        
        print()
        
        # 2. 导入数据
        print("📊 第二步：导入数据...")
        
        # 按依赖顺序导入
        steps = [
            ("添加剂基本信息", importer.import_additives),
            ("食品分类基本信息", importer.import_food_categories),
            ("添加剂使用限量", importer.import_additive_usage),
            ("分类-添加剂关联", importer.import_category_additives),
            ("其他数据", importer.import_other_data)
        ]
        
        for step_name, step_func in steps:
            print(f"\n🔄 正在导入: {step_name}")
            if not step_func():
                print(f"⚠️ {step_name}导入出现问题，但继续执行后续步骤")
        
        # 3. 打印总结
        importer.print_import_summary()
        
    finally:
        importer.close_database()

if __name__ == "__main__":
    main()