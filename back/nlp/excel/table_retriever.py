#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
表格数据回调检索器
当表头高相似度匹配时，回调读取实际表格数据，支持多表连接和条件检索
"""

import os
import csv
from typing import List, Dict, Optional


class TableDataRetriever:
    """读取 CSV/Excel 表格数据，支持多表连接和数据检索"""

    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir
        self.tables = {}         # {filename: [row_dict, ...]}
        self.table_headers = {}  # {filename: [header1, header2, ...]}
        self.joined = None       # 连接后的结果
        self.joined_headers = []
        self._loaded = False

    def load_all(self):
        """读取目录中所有 CSV 文件"""
        if not self.data_dir or not os.path.exists(self.data_dir):
            return

        for filename in sorted(os.listdir(self.data_dir)):
            _, ext = os.path.splitext(filename)
            if ext.lower() != '.csv':
                continue
            filepath = os.path.join(self.data_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    if rows:
                        self.tables[filename] = rows
                        self.table_headers[filename] = list(rows[0].keys())
            except Exception as e:
                print(f"[WARN] 读取 {filename} 失败: {e}")

        self._loaded = True
        if self.tables:
            print(f"[INFO] 已加载 {len(self.tables)} 个数据表")
            for fn, rows in self.tables.items():
                print(f"       {fn}: {len(rows)} 行, 列: {self.table_headers[fn]}")

    def _detect_join_pairs(self):
        """
        检测可连接的列对
        优先级：同名列 > 高重叠字符串列 > 数值重叠列
        """
        pairs = []
        filenames = list(self.tables.keys())

        for i in range(len(filenames)):
            for j in range(i + 1, len(filenames)):
                f1, f2 = filenames[i], filenames[j]
                h1, h2 = self.table_headers[f1], self.table_headers[f2]

                # 方法1: 同名列（最高优先级）
                common = set(h1) & set(h2)
                for col in common:
                    pairs.append({
                        'file_left': f1, 'file_right': f2,
                        'col_left': col, 'col_right': col,
                        'method': 'same_name',
                        'overlap_count': 0, 'overlap_ratio': 1.0,
                        'is_string': True,
                    })

                # 方法2: 值重叠列（仅在没有同名列时检测）
                if not common:
                    for c1 in h1:
                        vals1 = set(
                            row.get(c1, '') for row in self.tables[f1]
                            if row.get(c1, '')
                        )
                        if not vals1:
                            continue
                        # 判断该列是否主要是字符串类型
                        str_count1 = sum(
                            1 for v in vals1
                            if not v.replace('.', '').replace('-', '').replace('/', '').isdigit()
                        )
                        is_str1 = str_count1 / len(vals1) > 0.5 if vals1 else False

                        for c2 in h2:
                            vals2 = set(
                                row.get(c2, '') for row in self.tables[f2]
                                if row.get(c2, '')
                            )
                            if not vals2:
                                continue

                            overlap = vals1 & vals2
                            min_len = min(len(vals1), len(vals2))
                            ratio = len(overlap) / min_len if min_len > 0 else 0

                            # 判断该列是否主要是字符串类型
                            str_count2 = sum(
                                1 for v in vals2
                                if not v.replace('.', '').replace('-', '').replace('/', '').isdigit()
                            )
                            is_str2 = str_count2 / len(vals2) > 0.5 if vals2 else False

                            # 字符串列阈值更低（15%），数值列阈值更高（30%）
                            threshold = 0.15 if is_str1 and is_str2 else 0.30

                            if len(overlap) >= 3 and ratio >= threshold:

                                pairs.append({
                                    'file_left': f1, 'file_right': f2,
                                    'col_left': c1, 'col_right': c2,
                                    'method': 'value_overlap',
                                    'overlap_count': len(overlap),
                                    'overlap_ratio': round(ratio, 4),
                                    'is_string': is_str1 and is_str2,
                                })

        # 按优先级排序：同名列 > 字符串重叠 > 数值重叠；同优先级按重叠率降序
        def pair_priority(p):
            if p['method'] == 'same_name':
                return (0, 1.0, 0)
            elif p['is_string']:
                return (1, p['overlap_ratio'], p['overlap_count'])
            else:
                return (2, p['overlap_ratio'], p['overlap_count'])

        pairs.sort(key=pair_priority)
        return pairs

    def join_tables(self):
        """连接所有表（自动检测连接列，优先选择最佳连接对）"""
        if not self.tables:
            return None

        if self.joined is not None:
            return self.joined

        filenames = list(self.tables.keys())
        if len(filenames) == 1:
            self.joined = self.tables[filenames[0]]
            self.joined_headers = list(self.table_headers[filenames[0]])
            return self.joined

        # 检测连接对（已按优先级排序）
        join_pairs = self._detect_join_pairs()

        # 取第一个表作为基础
        result = self.tables[filenames[0]]
        result_headers = list(self.table_headers[filenames[0]])
        result_name = filenames[0]

        # 逐个连接后续表
        for other_file in filenames[1:]:
            other_rows = self.tables[other_file]
            other_headers = self.table_headers[other_file]

            # 找最佳连接列（优先级最高的）
            join_left = None
            join_right = None

            for pair in join_pairs:
                fl, fr = pair['file_left'], pair['file_right']
                cl, cr = pair['col_left'], pair['col_right']

                if (fl == result_name or fl in result_name) and fr == other_file:
                    join_left, join_right = cl, cr
                    break
                elif (fr == result_name or fr in result_name) and fl == other_file:
                    join_left, join_right = cr, cl
                    break

            if join_left and join_right:
                # 创建右表索引
                other_index = {}
                for row in other_rows:
                    key = row.get(join_right, '')
                    if key:
                        other_index.setdefault(key, []).append(row)

                new_result = []
                for row in result:
                    key = row.get(join_left, '')
                    if key and key in other_index:
                        for other_row in other_index[key]:
                            merged = dict(row)
                            for h in other_headers:
                                if h not in result_headers:  # 避免列名冲突
                                    merged[h] = other_row.get(h, '')
                            new_result.append(merged)
                    else:
                        new_result.append(row)

                result = new_result
                result_headers = list(set(
                    result_headers +
                    [h for h in other_headers if h not in result_headers]
                ))
                result_name = f"{result_name}+{other_file}"
                print(f"[INFO] 连接 {join_left} <-> {join_right}: "
                      f"{len(result)} 条记录")
            else:
                print(f"[WARN] 无法找到 {result_name} 与 {other_file} 的连接列，跳过连接")

        self.joined = result
        self.joined_headers = result_headers
        print(f"[INFO] 表连接完成: {len(self.joined)} 条记录, 列: {self.joined_headers}")
        return self.joined

    def retrieve(self, matched_headers: List[Dict], top_n: int = 50) -> Dict:
        """
        根据匹配的表头检索相关数据
        返回: {
            'records': [dict, ...],
            'headers': [str, ...],
            'total': int,
            'join_info': str,
            'files_loaded': [str, ...]
        }
        """
        if not self._loaded:
            self.load_all()

        if not self.tables:
            return {
                'records': [], 'headers': [], 'total': 0,
                'join_info': '', 'files_loaded': []
            }

        # 连接表
        self.join_tables()

        if not self.joined:
            return {
                'records': [], 'headers': [], 'total': 0,
                'join_info': '', 'files_loaded': list(self.tables.keys())
            }

        # 确定相关列：匹配的表头 + 通用关键列
        matched_header_names = set(
            item.get('header', '') for item in matched_headers
        )

        # 通用关键列（人员/健康相关查询常用）
        key_cols = {
            'name', '姓名', 'username', '年龄', 'age', 'id',
            '血压', 'blood_pressure', '健康', 'health',
            '性别', 'gender', '身高', '体重', 'weight', 'height',
        }

        relevant_cols = set()
        for col in self.joined_headers:
            if col in matched_header_names or col in key_cols:
                relevant_cols.add(col)

        # 确保至少有姓名/ID列
        name_cols = [c for c in self.joined_headers if c in ('name', '姓名', 'username')]
        for c in name_cols:
            relevant_cols.add(c)

        # 输出列：相关列（保持原始顺序）
        output_cols = [c for c in self.joined_headers if c in relevant_cols] \
            if relevant_cols else self.joined_headers

        # 取前 top_n 条记录
        records = []
        for row in self.joined[:top_n]:
            record = {col: row.get(col, '') for col in output_cols}
            records.append(record)

        # 连接信息描述
        join_pairs = self._detect_join_pairs()
        join_info = ''
        if join_pairs:
            best = join_pairs[0]
            if best['col_left'] == best['col_right']:
                join_info = f"{best['file_left']}.{best['col_left']} = {best['file_right']}.{best['col_right']}"
            else:
                join_info = (f"{best['file_left']}.{best['col_left']} <-> "
                             f"{best['file_right']}.{best['col_right']} "
                             f"(重叠{best['overlap_count']}值, 比率{best['overlap_ratio']:.0%})")

        return {
            'records': records,
            'headers': output_cols,
            'total': len(self.joined),
            'join_info': join_info,
            'files_loaded': list(self.tables.keys())
        }
