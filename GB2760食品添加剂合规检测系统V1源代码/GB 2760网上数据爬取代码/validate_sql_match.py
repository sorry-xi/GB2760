#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQL脚本与数据文件匹配性验证工具
"""

import pandas as pd
import re
import logging
from typing import Dict, List, Set

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SQLDataMatcher:
    """SQL脚本与数据文件匹配性验证器"""
    
    def __init__(self):
        self.excel_file = 'final_gb2760_data.xlsx'
        self.sql_file = 'database_schema.sql'
        
        # 预期的表与工作表映射
        self.table_sheet_mapping = {
            'additive': '添加剂基本信息',
            'additive_usage': '添加剂使用限量',  
            'food_category': '分类基本信息',
            'category_additive': '分类-添加剂关联',
            'processing_aid': '加工助剂',
            'enzyme': '酶制剂',
            'flavor': '香精香料'
        }
        
    def load_excel_structure(self) -> Dict[str, List[str]]:
        """加载Excel文件的结构信息"""
        structure = {}
        
        try:
            with pd.ExcelFile(self.excel_file) as xls:
                for sheet_name in xls.sheet_names:
                    if sheet_name != '数据统计':  # 跳过统计表
                        df = pd.read_excel(self.excel_file, sheet_name=sheet_name)
                        structure[sheet_name] = list(df.columns)
                        
            logger.info(f"成功加载Excel结构，包含 {len(structure)} 个工作表")
            return structure
            
        except Exception as e:
            logger.error(f"加载Excel文件失败: {e}")
            return {}
    
    def parse_sql_structure(self) -> Dict[str, List[str]]:
        """解析SQL文件中的表结构"""
        structure = {}
        
        try:
            with open(self.sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # 简化的表结构解析
            lines = sql_content.split('\n')
            current_table = None
            current_columns = []
            in_table_def = False
            
            for line in lines:
                line = line.strip()
                
                # 检测 CREATE TABLE 语句
                if line.upper().startswith('CREATE TABLE'):
                    # 保存上一个表
                    if current_table and current_columns:
                        structure[current_table] = current_columns.copy()
                    
                    # 提取表名
                    table_match = re.search(r'CREATE TABLE\s+(\w+)\s*\(', line, re.IGNORECASE)
                    if table_match:
                        current_table = table_match.group(1)
                        current_columns = []
                        in_table_def = True
                        continue
                
                if in_table_def:
                    # 检测表定义结束
                    if line.startswith(');') or line == ')':
                        if current_table and current_columns:
                            structure[current_table] = current_columns.copy()
                        in_table_def = False
                        current_table = None
                        current_columns = []
                        continue
                    
                    # 跳过注释和空行
                    if line.startswith('--') or not line or line.startswith('/*'):
                        continue
                    
                    # 跳过索引和约束
                    skip_keywords = ['INDEX', 'KEY', 'CONSTRAINT', 'FOREIGN', 'PRIMARY KEY', 
                                   'UNIQUE KEY', 'FULLTEXT', 'ENGINE', 'COMMENT=', 'AUTO_INCREMENT']
                    if any(keyword in line.upper() for keyword in skip_keywords):
                        continue
                    
                    # 提取字段名
                    field_match = re.match(r'\s*(\w+)\s+', line)
                    if field_match:
                        field_name = field_match.group(1)
                        # 过滤保留字
                        if field_name.upper() not in ['PRIMARY', 'UNIQUE', 'INDEX', 'KEY', 'CONSTRAINT']:
                            current_columns.append(field_name)
            
            # 处理最后一个表
            if current_table and current_columns:
                structure[current_table] = current_columns
                
            logger.info(f"成功解析SQL结构，包含 {len(structure)} 个表")
            for table, columns in structure.items():
                logger.info(f"  {table}: {len(columns)}个字段 - {columns[:3]}{'...' if len(columns) > 3 else ''}")
            
            return structure
            
        except Exception as e:
            logger.error(f"解析SQL文件失败: {e}")
            return {}
    
    def validate_matching(self) -> bool:
        """验证SQL表结构与Excel数据结构的匹配性"""
        print("🔍 SQL脚本与数据文件匹配性验证")
        print("=" * 60)
        
        # 加载结构
        excel_structure = self.load_excel_structure()
        sql_structure = self.parse_sql_structure()
        
        if not excel_structure or not sql_structure:
            print("❌ 无法加载数据结构")
            return False
        
        overall_match = True
        
        # 验证每个表的匹配性
        for table_name, sheet_name in self.table_sheet_mapping.items():
            print(f"\n📋 验证表: {table_name} ↔ 工作表: {sheet_name}")
            
            if table_name not in sql_structure:
                print(f"❌ SQL中缺少表: {table_name}")
                overall_match = False
                continue
                
            if sheet_name not in excel_structure:
                print(f"❌ Excel中缺少工作表: {sheet_name}")
                overall_match = False
                continue
            
            sql_columns = set(sql_structure[table_name])
            excel_columns = set(excel_structure[sheet_name])
            
            # 检查字段匹配
            missing_in_sql = excel_columns - sql_columns
            missing_in_excel = sql_columns - excel_columns
            common_fields = sql_columns & excel_columns
            
            if missing_in_sql:
                print(f"⚠️  SQL表中缺少字段: {', '.join(missing_in_sql)}")
                overall_match = False
                
            if missing_in_excel:
                print(f"⚠️  Excel中缺少字段: {', '.join(missing_in_excel)}")
                overall_match = False
            
            match_rate = len(common_fields) / max(len(sql_columns), len(excel_columns)) * 100
            
            if match_rate >= 95:
                print(f"✅ 字段匹配率: {match_rate:.1f}% ({len(common_fields)}/{max(len(sql_columns), len(excel_columns))})")
            elif match_rate >= 80:
                print(f"⚠️  字段匹配率: {match_rate:.1f}% ({len(common_fields)}/{max(len(sql_columns), len(excel_columns))})")
            else:
                print(f"❌ 字段匹配率: {match_rate:.1f}% ({len(common_fields)}/{max(len(sql_columns), len(excel_columns))})")
                overall_match = False
        
        # 输出总结
        print("\n" + "=" * 60)
        if overall_match:
            print("🎉 验证结果: SQL脚本与数据文件结构完全匹配!")
            print("✅ 可以直接使用data_import.py进行数据导入")
        else:
            print("⚠️  验证结果: 发现结构不匹配问题")
            print("🔧 需要调整SQL脚本或数据文件结构")
        
        print("=" * 60)
        return overall_match
    
    def generate_import_summary(self):
        """生成导入准备情况总结"""
        excel_structure = self.load_excel_structure()
        
        print("\n📊 数据导入准备情况:")
        print("-" * 40)
        
        total_records = 0
        for sheet_name in excel_structure:
            if sheet_name != '数据统计':
                df = pd.read_excel(self.excel_file, sheet_name=sheet_name)
                record_count = len(df)
                total_records += record_count
                
                # 匹配表名
                table_name = None
                for t_name, s_name in self.table_sheet_mapping.items():
                    if s_name == sheet_name:
                        table_name = t_name
                        break
                
                print(f"📋 {sheet_name} → {table_name}: {record_count:,} 条记录")
        
        print(f"\n💾 总记录数: {total_records:,} 条")
        print(f"📁 数据文件: final_gb2760_data.xlsx")
        print(f"🗄️ 目标数据库: gb2760_db")
        print(f"🔧 导入工具: data_import.py")

def main():
    """主函数"""
    print("🔍 GB 2760数据库导入准备验证工具")
    print("=" * 60)
    
    matcher = SQLDataMatcher()
    
    # 验证匹配性
    is_matched = matcher.validate_matching()
    
    # 生成导入总结
    matcher.generate_import_summary()
    
    if is_matched:
        print("\n✅ 准备就绪，可以开始数据导入:")
        print("   python data_import.py")
    else:
        print("\n⚠️  需要先解决结构匹配问题")
    
    return is_matched

if __name__ == "__main__":
    main()