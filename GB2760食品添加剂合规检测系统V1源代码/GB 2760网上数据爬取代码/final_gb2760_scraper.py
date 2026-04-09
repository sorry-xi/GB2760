#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GB 2760-2024 最终完整数据爬虫
爬取所有真实数据，建立完整的多对多关系
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import urllib3
import time
import logging
from typing import List, Dict, Optional
import re

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(__import__('pathlib').Path(__file__).parent /'final_scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def __improt__(param):
    pass


class FinalGB2760Scraper:
    """GB 2760最终完整数据爬虫"""
    
    def __init__(self):
        self.base_url = "https://gb2760.cfsa.net.cn"
        self.session = self._create_session()
        
        # 数据存储
        self.additives_basic = []          # 添加剂基本信息
        self.additives_usage = []          # 添加剂使用限量
        self.categories_basic = []         # 分类基本信息
        self.category_additives = []       # 分类-添加剂关联
        self.food_categories = []          # 食品分类列表
        self.processing_aids = []          # 加工助剂
        self.enzymes = []                  # 酶制剂
        self.spices = []                   # 香精香料
        
    def _create_session(self):
        """创建请求会话"""
        session = requests.Session()
        session.verify = False
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        })
        return session
    
    # ================= 添加剂数据爬取 =================
    
    def get_additive_list(self) -> List[Dict]:
        """获取添加剂列表"""
        logger.info("开始获取添加剂列表...")
        
        try:
            url = self.base_url + "/addtives.html"
            response = self.session.get(url, timeout=15)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            additives_list = []
            tables = soup.find_all('table')
            
            if tables:
                table = tables[0]
                rows = table.find_all('tr')
                logger.info(f"找到 {len(rows)-1} 个添加剂")
                
                for i, row in enumerate(rows[1:], 1):
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 3:
                        name_zh = cells[0].get_text(strip=True)
                        name_en = cells[1].get_text(strip=True)
                        cns_code = cells[2].get_text(strip=True)
                        ins_code = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                        function_category = cells[4].get_text(strip=True) if len(cells) > 4 else ""
                        
                        link = cells[0].find('a')
                        if link:
                            detail_url = link.get('href', '')
                            if detail_url.startswith('/'):
                                detail_url = self.base_url + detail_url
                            
                            additive_id = None
                            if '/faid/' in detail_url:
                                try:
                                    additive_id = int(detail_url.split('/faid/')[1].split('.')[0])
                                except:
                                    additive_id = i
                            
                            additives_list.append({
                                'id': additive_id or i,
                                'name_zh': name_zh,
                                'name_en': name_en,
                                'cns_code': cns_code,
                                'ins_code': ins_code,
                                'function_category': function_category,
                                'detail_url': detail_url
                            })
            
            logger.info(f"成功获取 {len(additives_list)} 个添加剂列表")
            return additives_list
            
        except Exception as e:
            logger.error(f"获取添加剂列表失败: {e}")
            return []
    
    def scrape_additive_detail(self, additive_info: Dict) -> bool:
        """爬取单个添加剂的详情信息"""
        additive_id = additive_info['id']
        name_zh = additive_info['name_zh']
        detail_url = additive_info['detail_url']
        
        try:
            response = self.session.get(detail_url, timeout=15)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                logger.warning(f"详情页面访问失败: {name_zh} - 状态码: {response.status_code}")
                return False
            
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')
            
            if len(tables) < 1:
                logger.warning(f"详情页面无表格数据: {name_zh}")
                return False
            
            # 解析基本信息
            basic_info = additive_info.copy()
            
            if tables[0]:
                basic_table = tables[0]
                basic_rows = basic_table.find_all('tr')
                
                for row in basic_rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        field_name = cells[0].get_text(strip=True)
                        field_value = cells[1].get_text(strip=True)
                        
                        if field_name == '质量规格标准':
                            basic_info['quality_standard'] = field_value
                        elif field_name == 'JECFA规格资料':
                            basic_info['jecfa_spec'] = field_value
                        elif field_name == '备注':
                            basic_info['remarks'] = field_value
            
            # 确保字段完整
            for field in ['quality_standard', 'jecfa_spec', 'remarks']:
                if field not in basic_info:
                    basic_info[field] = ""
            
            self.additives_basic.append(basic_info)
            
            # 解析使用限量信息
            usage_count = 0
            for table_idx, table in enumerate(tables[1:], 1):
                usage_rows = table.find_all('tr')
                
                if len(usage_rows) < 2:
                    continue
                
                header_row = usage_rows[0]
                headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
                
                if not any(h in ['食品分类号', '食品名称', '最大使用量'] for h in headers):
                    continue
                
                for row in usage_rows[1:]:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 3:
                        category_code = cells[0].get_text(strip=True)
                        food_name = cells[1].get_text(strip=True)
                        max_usage = cells[2].get_text(strip=True)
                        usage_remarks = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                        
                        usage_info = {
                            'additive_id': additive_id,
                            'additive_name': name_zh,
                            'category_code': category_code,
                            'food_name': food_name,
                            'max_usage': max_usage,
                            'usage_remarks': usage_remarks
                        }
                        
                        self.additives_usage.append(usage_info)
                        usage_count += 1
            
            logger.info(f"成功爬取添加剂 {name_zh}: 基本信息 + {usage_count} 条使用限量")
            return True
            
        except Exception as e:
            logger.error(f"爬取添加剂详情失败 {name_zh}: {e}")
            return False
    
    # ================= 食品分类数据爬取 =================
    
    def get_category_list(self) -> List[Dict]:
        """获取食品分类列表"""
        logger.info("开始获取食品分类列表...")
        
        try:
            url = self.base_url + "/category.html"
            response = self.session.get(url, timeout=15)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            categories_list = []
            tables = soup.find_all('table')
            
            if tables:
                table = tables[0]
                rows = table.find_all('tr')
                logger.info(f"找到 {len(rows)-1} 个食品分类")
                
                for i, row in enumerate(rows[1:], 1):
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        category_code = cells[0].get_text(strip=True)
                        category_name = cells[1].get_text(strip=True)
                        
                        link = cells[1].find('a')
                        if link:
                            detail_url = link.get('href', '')
                            if detail_url.startswith('/'):
                                detail_url = self.base_url + detail_url
                            
                            category_id = None
                            if '/limit/' in detail_url:
                                try:
                                    category_id = int(detail_url.split('/limit/')[1].split('.')[0])
                                except:
                                    category_id = i
                            
                            categories_list.append({
                                'id': category_id or i,
                                'category_code': category_code,
                                'category_name': category_name,
                                'detail_url': detail_url
                            })
            
            logger.info(f"成功获取 {len(categories_list)} 个食品分类列表")
            return categories_list
            
        except Exception as e:
            logger.error(f"获取分类列表失败: {e}")
            return []
    
    def scrape_category_detail(self, category_info: Dict) -> bool:
        """爬取单个分类的详情信息"""
        category_id = category_info['id']
        category_code = category_info['category_code']
        category_name = category_info['category_name']
        detail_url = category_info['detail_url']
        
        try:
            response = self.session.get(detail_url, timeout=15)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                logger.warning(f"分类详情页面访问失败: {category_name} - 状态码: {response.status_code}")
                return False
            
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')
            
            if len(tables) < 1:
                logger.warning(f"分类详情页面无表格数据: {category_name}")
                return False
            
            # 解析分类基本信息
            basic_info = category_info.copy()
            
            if tables and len(tables) >= 1:
                basic_table = tables[0]
                basic_rows = basic_table.find_all('tr')
                
                for row in basic_rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        field_name = cells[0].get_text(strip=True)
                        field_value = cells[1].get_text(strip=True)
                        
                        if field_name in ['食品名称描述', '描述']:
                            basic_info['description'] = field_value
                        elif field_name in ['相关食品标准', '标准']:
                            basic_info['standards'] = field_value
            
            for field in ['description', 'standards']:
                if field not in basic_info:
                    basic_info[field] = ""
            
            self.categories_basic.append(basic_info)
            
            # 解析添加剂关联信息
            additive_count = 0
            for table_idx, table in enumerate(tables[1:], 1):
                additive_rows = table.find_all('tr')
                
                if len(additive_rows) < 2:
                    continue
                
                header_row = additive_rows[0]
                headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
                
                if not any(h in ['添加剂', 'CNS', 'INS', '最大使用量'] for h in headers):
                    continue
                
                for row in additive_rows[1:]:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 3:
                        additive_name = cells[0].get_text(strip=True)
                        function = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                        max_usage = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                        cns_code = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                        ins_code = cells[4].get_text(strip=True) if len(cells) > 4 else ""
                        remarks = cells[5].get_text(strip=True) if len(cells) > 5 else ""
                        
                        additive_usage = {
                            'category_id': category_id,
                            'category_code': category_code,
                            'category_name': category_name,
                            'additive_name': additive_name,
                            'function': function,
                            'max_usage': max_usage,
                            'cns_code': cns_code,
                            'ins_code': ins_code,
                            'remarks': remarks
                        }
                        
                        self.category_additives.append(additive_usage)
                        additive_count += 1
            
            logger.info(f"成功爬取分类 {category_name}: 基本信息 + {additive_count} 个添加剂")
            return True
            
        except Exception as e:
            logger.error(f"爬取分类详情失败 {category_name}: {e}")
            return False
    
    # ================= 其他数据爬取 =================
    
    def scrape_other_data(self) -> bool:
        """爬取其他数据（加工助剂、酶制剂、香精香料）"""
        logger.info("开始爬取其他数据...")
        
        # 爬取加工助剂
        try:
            url = self.base_url + "/processing.html"
            response = self.session.get(url, timeout=15)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                if len(rows) > 1:
                    for i, row in enumerate(rows[1:], 1):
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 1:
                            row_data = [cell.get_text(strip=True) for cell in cells]
                            
                            aid_info = {
                                'name_zh': row_data[0] if row_data[0] else f"加工助剂_{i}",
                                'name_en': row_data[1] if len(row_data) > 1 else "",
                                'function': row_data[2] if len(row_data) > 2 else "",
                                'usage_scope': ' | '.join(row_data[3:]) if len(row_data) > 3 else "",
                                'cas_number': '',
                                'remarks': '',
                                'raw_data': ' | '.join(row_data)
                            }
                            
                            self.processing_aids.append(aid_info)
            
            logger.info(f"成功爬取 {len(self.processing_aids)} 个加工助剂")
        except Exception as e:
            logger.error(f"爬取加工助剂失败: {e}")
        
        # 爬取酶制剂
        try:
            url = self.base_url + "/enzyme.html"
            response = self.session.get(url, timeout=15)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                if len(rows) > 1:
                    for i, row in enumerate(rows[1:], 1):
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 1:
                            row_data = [cell.get_text(strip=True) for cell in cells]
                            
                            enzyme_info = {
                                'name_zh': row_data[0] if row_data[0] else f"酶制剂_{i}",
                                'name_en': row_data[1] if len(row_data) > 1 else "",
                                'enzyme_source': row_data[2] if len(row_data) > 2 else "",
                                'usage_scope': ' | '.join(row_data[3:]) if len(row_data) > 3 else "",
                                'ec_number': '',
                                'cas_number': '',
                                'remarks': '',
                                'raw_data': ' | '.join(row_data)
                            }
                            
                            self.enzymes.append(enzyme_info)
            
            logger.info(f"成功爬取 {len(self.enzymes)} 个酶制剂")
        except Exception as e:
            logger.error(f"爬取酶制剂失败: {e}")
        
        # 爬取香精香料（完整三个表格）
        try:
            # 1. 爬取表B.1 - 不得添加食品用香料、香精的食品名单
            url = self.base_url + "/spices.html"
            response = self.session.get(url, timeout=15)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                if len(rows) > 1:
                    for i, row in enumerate(rows[1:], 1):
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 2:
                            row_data = [cell.get_text(strip=True) for cell in cells]
                            
                            spice_info = {
                                'category': 'B.1-禁用食品名单',
                                'name_zh': row_data[1] if len(row_data) > 1 else row_data[0],
                                'name_en': '',
                                'type': '不得添加香精香料',
                                'code': row_data[0] if len(row_data) > 1 else '',
                                'fema_no': '',
                                'classification_table': 'B.1',
                                'remarks': '不得添加食品用香料、香精',
                                'raw_data': ' | '.join(row_data)
                            }
                            
                            self.spices.append(spice_info)
            
            # 2. 爬取表B.2 - 食品用天然香料
            url_b2 = self.base_url + "/spices/type/b2.html"
            response = self.session.get(url_b2, timeout=15)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                if len(rows) > 1:
                    for i, row in enumerate(rows[1:], 1):
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 3:
                            row_data = [cell.get_text(strip=True) for cell in cells]
                            
                            spice_info = {
                                'category': row_data[0] if row_data[0] else 'B.2-天然香料',
                                'name_zh': row_data[1] if len(row_data) > 1 else '',
                                'name_en': row_data[2] if len(row_data) > 2 else '',
                                'type': '天然香料',
                                'code': row_data[3] if len(row_data) > 3 else '',
                                'fema_no': row_data[4] if len(row_data) > 4 else '',
                                'classification_table': row_data[5] if len(row_data) > 5 else 'B.2',
                                'remarks': row_data[6] if len(row_data) > 6 else '',
                                'raw_data': ' | '.join(row_data)
                            }
                            
                            self.spices.append(spice_info)
            
            # 3. 爬取表B.3 - 食品用合成香料
            url_b3 = self.base_url + "/spices/type/b3.html"
            response = self.session.get(url_b3, timeout=15)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                if len(rows) > 1:
                    for i, row in enumerate(rows[1:], 1):
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 3:
                            row_data = [cell.get_text(strip=True) for cell in cells]
                            
                            spice_info = {
                                'category': row_data[0] if row_data[0] else 'B.3-合成香料',
                                'name_zh': row_data[1] if len(row_data) > 1 else '',
                                'name_en': row_data[2] if len(row_data) > 2 else '',
                                'type': '合成香料',
                                'code': row_data[3] if len(row_data) > 3 else '',
                                'fema_no': row_data[4] if len(row_data) > 4 else '',
                                'classification_table': row_data[5] if len(row_data) > 5 else 'B.3',
                                'remarks': row_data[6] if len(row_data) > 6 else '',
                                'raw_data': ' | '.join(row_data)
                            }
                            
                            
                            self.spices.append(spice_info)
            
            logger.info(f"成功爬取香精香料: B.1表+B.2表(天然)+B.3表(合成) = {len(self.spices)} 个")
        except Exception as e:
            logger.error(f"爬取香精香料失败: {e}")
        
        return True
    
    # ================= 主要爬取流程 =================
    
    def scrape_all_data(self) -> bool:
        """爬取所有数据"""
        logger.info("开始完整数据爬取...")
        
        print("🕷️ GB 2760-2024 最终完整数据爬虫")
        print("=" * 60)
        print("100% 真实数据爬取，建立完整多对多关系")
        print()
        
        # 1. 爬取添加剂详情
        print("📊 第一阶段：爬取添加剂详情数据")
        additives_list = self.get_additive_list()
        if not additives_list:
            logger.error("无法获取添加剂列表")
            return False
        
        success_count = 0
        for i, additive_info in enumerate(additives_list, 1):
            if self.scrape_additive_detail(additive_info):
                success_count += 1
            
            if i % 10 == 0:
                logger.info(f"添加剂进度: {i}/{len(additives_list)} 完成，成功 {success_count} 个")
            
            time.sleep(1)
        
        print(f"✅ 添加剂数据爬取完成: {success_count}/{len(additives_list)}")
        
        # 2. 爬取分类详情
        print("\n📊 第二阶段：爬取食品分类详情数据")
        categories_list = self.get_category_list()
        if not categories_list:
            logger.error("无法获取分类列表")
            return False
        
        success_count = 0
        for i, category_info in enumerate(categories_list, 1):
            if self.scrape_category_detail(category_info):
                success_count += 1
            
            if i % 10 == 0:
                logger.info(f"分类进度: {i}/{len(categories_list)} 完成，成功 {success_count} 个")
            
            time.sleep(1)
        
        print(f"✅ 分类数据爬取完成: {success_count}/{len(categories_list)}")
        
        # 3. 爬取其他数据
        print("\n📊 第三阶段：爬取其他数据")
        self.scrape_other_data()
        print("✅ 其他数据爬取完成")
        
        return True
    
    def save_to_excel(self, filename: str = 'final_gb2760_data.xlsx') -> bool:
        """保存完整数据到Excel"""
        try:
            filepath  = __import__('pathlib').Path(__file__).parent /filename
            #filepath = f"d:/html+css/GB 2760-2024/{filename}"
            
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                
                # 添加剂基本信息表
                if self.additives_basic:
                    basic_df = pd.DataFrame(self.additives_basic)
                    basic_df.to_excel(writer, sheet_name='添加剂基本信息', index=False)
                
                # 添加剂使用限量表
                if self.additives_usage:
                    usage_df = pd.DataFrame(self.additives_usage)
                    usage_df.to_excel(writer, sheet_name='添加剂使用限量', index=False)
                
                # 分类基本信息表
                if self.categories_basic:
                    cat_basic_df = pd.DataFrame(self.categories_basic)
                    cat_basic_df.to_excel(writer, sheet_name='分类基本信息', index=False)
                
                # 分类-添加剂关联表
                if self.category_additives:
                    cat_add_df = pd.DataFrame(self.category_additives)
                    cat_add_df.to_excel(writer, sheet_name='分类-添加剂关联', index=False)
                
                # 加工助剂表
                if self.processing_aids:
                    aids_df = pd.DataFrame(self.processing_aids)
                    aids_df.to_excel(writer, sheet_name='加工助剂', index=False)
                
                # 酶制剂表
                if self.enzymes:
                    enzymes_df = pd.DataFrame(self.enzymes)
                    enzymes_df.to_excel(writer, sheet_name='酶制剂', index=False)
                
                # 香精香料表
                if self.spices:
                    spices_df = pd.DataFrame(self.spices)
                    spices_df.to_excel(writer, sheet_name='香精香料', index=False)
                
                # 数据统计表
                stats_data = [
                    {'数据类型': '添加剂基本信息', '数量': len(self.additives_basic), '说明': '包含完整的添加剂基本信息'},
                    {'数据类型': '添加剂使用限量', '数量': len(self.additives_usage), '说明': '添加剂在不同食品分类中的使用限量'},
                    {'数据类型': '分类基本信息', '数量': len(self.categories_basic), '说明': '包含完整的分类基本信息'},
                    {'数据类型': '分类-添加剂关联', '数量': len(self.category_additives), '说明': '分类可以使用的添加剂列表'},
                    {'数据类型': '加工助剂', '数量': len(self.processing_aids), '说明': '加工助剂基本信息'},
                    {'数据类型': '酶制剂', '数量': len(self.enzymes), '说明': '酶制剂基本信息'},
                    {'数据类型': '香精香料', '数量': len(self.spices), '说明': '香精香料基本信息'}
                ]
                stats_df = pd.DataFrame(stats_data)
                stats_df.to_excel(writer, sheet_name='数据统计', index=False)
            
            logger.info(f"完整数据已保存到: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"保存Excel文件失败: {e}")
            return False

def main():
    """主函数"""
    scraper = FinalGB2760Scraper()
    
    if scraper.scrape_all_data():
        if scraper.save_to_excel():
            print("\n🎉 完整数据爬取和保存成功！")
            print("=" * 50)
            print(f"📊 添加剂基本信息: {len(scraper.additives_basic)} 个")
            print(f"📊 添加剂使用限量: {len(scraper.additives_usage)} 条")
            print(f"📊 分类基本信息: {len(scraper.categories_basic)} 个")
            print(f"📊 分类-添加剂关联: {len(scraper.category_additives)} 条")
            print(f"📊 加工助剂: {len(scraper.processing_aids)} 个")
            print(f"📊 酶制剂: {len(scraper.enzymes)} 个")
            print(f"📊 香精香料: {len(scraper.spices)} 个")
            print("\n💾 文件保存位置:")
            print( __import__('pathlib').Path(__file__).parent / "final_gb2760_data.xlsx")
            print(__import__('pathlib').Path(__file__).parent / "final_scraper.log")
        else:
            print("❌ 数据保存失败！")
    else:
        print("❌ 数据爬取失败！")

if __name__ == "__main__":
    main()