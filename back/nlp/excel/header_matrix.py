#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
表头关联矩阵分析工具
分析多个数据表的表头之间的关联关系，并存储为矩阵形式
"""

import os
import csv
import json
from typing import List, Dict, Set, Any

try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


class HeaderMatrixAnalyzer:
    def __init__(self):
        self.file_headers = {}  # {文件名: [表头列表]}
        self.all_headers = set()  # 所有表头的集合
        self.matrix = None  # 关联矩阵
        self.file_list = []  # 文件列表顺序
    
    def load_files_from_directory(self, directory_path: str) -> bool:
        """从目录加载所有Excel/CSV文件的表头"""
        if not os.path.exists(directory_path):
            print(f"[错误] 目录不存在: {directory_path}")
            return False
        
        supported_exts = ['.xlsx', '.xls', '.csv']
        files_found = False
        
        for filename in os.listdir(directory_path):
            _, ext = os.path.splitext(filename)
            if ext.lower() in supported_exts:
                file_path = os.path.join(directory_path, filename)
                headers = self._extract_headers(file_path)
                if headers:
                    self.file_headers[filename] = headers
                    self.all_headers.update(headers)
                    self.file_list.append(filename)
                    files_found = True
                    print(f"[OK] 加载文件: {filename} ({len(headers)} 个表头)")
        
        if not files_found:
            print("[警告] 目录中未找到支持的文件")
            return False
        
        print(f"\n共加载 {len(self.file_list)} 个文件，发现 {len(self.all_headers)} 个不同表头")
        return True
    
    def _extract_headers(self, file_path: str) -> List[str]:
        """提取单个文件的表头"""
        _, ext = os.path.splitext(file_path)
        
        try:
            if ext.lower() in ['.xlsx', '.xls']:
                return self._extract_excel_headers(file_path)
            elif ext.lower() == '.csv':
                return self._extract_csv_headers(file_path)
            else:
                return []
        except Exception as e:
            print(f"[警告] 无法读取文件 {file_path}: {str(e)}")
            return []
    
    def _extract_excel_headers(self, file_path: str) -> List[str]:
        """提取Excel文件的表头"""
        if not PANDAS_AVAILABLE:
            print("[错误] 需要安装 pandas 来读取 Excel 文件")
            return []
        
        try:
            df = pd.read_excel(file_path, nrows=0)
            return df.columns.tolist()
        except Exception as e:
            print(f"[警告] 读取 Excel 文件失败: {str(e)}")
            return []
    
    def _extract_csv_headers(self, file_path: str) -> List[str]:
        """提取CSV文件的表头"""
        if PANDAS_AVAILABLE:
            try:
                df = pd.read_csv(file_path, nrows=0, encoding='utf-8')
                return df.columns.tolist()
            except Exception:
                pass
        
        # 纯Python方式
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                first_row = next(reader, None)
                return first_row if first_row else []
        except Exception as e:
            print(f"[警告] 读取 CSV 文件失败: {str(e)}")
            return []
    
    def build_association_matrix(self) -> np.ndarray:
        """构建表头关联矩阵"""
        if not self.file_headers or not self.all_headers:
            print("[错误] 请先加载文件")
            return None
        
        # 将表头和文件列表转换为索引
        header_list = sorted(list(self.all_headers))
        header_index = {header: i for i, header in enumerate(header_list)}
        
        # 创建矩阵: 行=文件, 列=表头, 值=1表示文件包含该表头
        num_files = len(self.file_list)
        num_headers = len(header_list)
        self.matrix = np.zeros((num_files, num_headers), dtype=int)
        
        for file_idx, filename in enumerate(self.file_list):
            headers = self.file_headers[filename]
            for header in headers:
                if header in header_index:
                    self.matrix[file_idx, header_index[header]] = 1
        
        print(f"\n关联矩阵构建完成: {num_files} × {num_headers}")
        return self.matrix
    
    def calculate_header_cooccurrence(self) -> np.ndarray:
        """计算表头共现矩阵（两个表头同时出现在多少个文件中）"""
        if self.matrix is None:
            print("[错误] 请先构建关联矩阵")
            return None
        
        # 共现矩阵 = 矩阵转置 × 矩阵
        cooccurrence = self.matrix.T @ self.matrix
        return cooccurrence
    
    def find_common_headers(self, min_files: int = 2) -> List[str]:
        """找出在多个文件中出现的公共表头"""
        if self.matrix is None:
            print("[错误] 请先构建关联矩阵")
            return []
        
        # 计算每个表头出现在多少个文件中
        header_counts = self.matrix.sum(axis=0)
        header_list = sorted(list(self.all_headers))
        
        common_headers = []
        for i, count in enumerate(header_counts):
            if count >= min_files:
                common_headers.append((header_list[i], int(count)))
        
        common_headers.sort(key=lambda x: -x[1])
        return common_headers
    
    def find_file_relationships(self) -> List[Dict]:
        """分析文件之间的关系（共享多少表头）"""
        if self.matrix is None:
            print("[错误] 请先构建关联矩阵")
            return []
        
        relationships = []
        num_files = len(self.file_list)
        
        for i in range(num_files):
            for j in range(i + 1, num_files):
                # 计算两个文件共享的表头数量
                shared_count = np.sum(self.matrix[i] & self.matrix[j])
                total_count = np.sum(self.matrix[i] | self.matrix[j])
                
                if total_count > 0:
                    similarity = shared_count / total_count
                else:
                    similarity = 0.0
                
                relationships.append({
                    'file1': self.file_list[i],
                    'file2': self.file_list[j],
                    'shared_headers': int(shared_count),
                    'total_unique_headers': int(total_count),
                    'similarity': round(similarity, 4)
                })
        
        relationships.sort(key=lambda x: -x['similarity'])
        return relationships
    
    def save_matrix(self, output_path: str, format_type: str = 'csv') -> bool:
        """保存矩阵到文件"""
        if self.matrix is None:
            print("[错误] 请先构建关联矩阵")
            return False
        
        try:
            header_list = sorted(list(self.all_headers))
            
            if format_type == 'csv':
                # 保存为CSV格式，第一行是表头名，第一列是文件名
                with open(output_path, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    # 写入表头行
                    writer.writerow(['文件名'] + header_list)
                    # 写入数据行
                    for i, filename in enumerate(self.file_list):
                        row = [filename] + self.matrix[i].tolist()
                        writer.writerow(row)
                print(f"[成功] 矩阵已保存为 CSV 文件: {output_path}")
            
            elif format_type == 'json':
                data = {
                    'files': self.file_list,
                    'headers': header_list,
                    'matrix': self.matrix.tolist()
                }
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"[成功] 矩阵已保存为 JSON 文件: {output_path}")
            
            elif format_type == 'npy':
                np.save(output_path, self.matrix)
                # 同时保存索引信息
                index_info = {
                    'files': self.file_list,
                    'headers': sorted(list(self.all_headers))
                }
                index_path = output_path.replace('.npy', '_index.json')
                with open(index_path, 'w', encoding='utf-8') as f:
                    json.dump(index_info, f, ensure_ascii=False, indent=2)
                print(f"[成功] 矩阵已保存为 NPY 文件: {output_path}")
            
            return True
        
        except Exception as e:
            print(f"[错误] 保存文件失败: {str(e)}")
            return False
    
    def save_cooccurrence_matrix(self, output_path: str) -> bool:
        """保存表头共现矩阵"""
        cooccurrence = self.calculate_header_cooccurrence()
        if cooccurrence is None:
            return False
        
        header_list = sorted(list(self.all_headers))
        
        try:
            with open(output_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                # 写入表头行（包含空列用于行标签）
                writer.writerow([''] + header_list)
                # 写入数据行
                for i, header in enumerate(header_list):
                    row = [header] + cooccurrence[i].tolist()
                    writer.writerow(row)
            print(f"[成功] 共现矩阵已保存: {output_path}")
            return True
        except Exception as e:
            print(f"[错误] 保存共现矩阵失败: {str(e)}")
            return False
    
    def print_summary(self):
        """打印分析摘要"""
        print("\n" + "=" * 60)
        print("              表头关联分析摘要")
        print("=" * 60)
        
        # 基本信息
        print(f"\n📁 加载的文件: {len(self.file_list)} 个")
        print(f"📊 不同表头总数: {len(self.all_headers)} 个")
        
        # 公共表头
        common_headers = self.find_common_headers(min_files=2)
        print(f"\n🔗 在多个文件中出现的表头 ({len(common_headers)} 个):")
        for header, count in common_headers[:10]:
            print(f"  - {header}: 出现在 {count} 个文件中")
        if len(common_headers) > 10:
            print(f"  ... 还有 {len(common_headers) - 10} 个")
        
        # 文件关系
        relationships = self.find_file_relationships()
        print(f"\n🔍 文件间关系分析 ({len(relationships)} 对):")
        for rel in relationships[:5]:
            print(f"  - {rel['file1']} ↔ {rel['file2']}")
            print(f"    共享表头: {rel['shared_headers']} 个, 相似度: {rel['similarity']:.2%}")
        if len(relationships) > 5:
            print(f"  ... 还有 {len(relationships) - 5} 对")
    
    def print_matrix(self):
        """打印关联矩阵（简化版）"""
        if self.matrix is None:
            print("[错误] 请先构建关联矩阵")
            return
        
        header_list = sorted(list(self.all_headers))
        
        print("\n" + "=" * 60)
        print("                   表头关联矩阵")
        print("=" * 60)
        
        # 打印表头名（只显示前20个）
        display_headers = header_list[:20]
        print(" " * 20 + "".join(f"{h[:8]:<10}" for h in display_headers))
        print("-" * (20 + len(display_headers) * 10))
        
        # 打印每行
        for i, filename in enumerate(self.file_list):
            row_str = f"{filename[:18]:<20}"
            for j, header in enumerate(display_headers):
                row_str += f"{self.matrix[i, j]:<10}"
            print(row_str)
            
            # 只显示前10行
            if i >= 9:
                print(f"... (还有 {len(self.file_list) - 10} 行)")
                break
        
        if len(header_list) > 20:
            print(f"\n注：只显示前20个表头，共 {len(header_list)} 个")


def main():
    """主函数"""
    print("=" * 60)
    print("        表头关联矩阵分析工具")
    print("=" * 60)
    print("功能: 分析多个数据表的表头关联关系")
    print("支持: .xlsx, .xls, .csv")
    print("=" * 60)
    
    analyzer = HeaderMatrixAnalyzer()
    
    while True:
        try:
            command = input("\n> ").strip()
            if not command:
                continue
            
            parts = command.split()
            cmd = parts[0].lower()
            
            if cmd in ['exit', 'q']:
                print("\n👋 退出程序")
                break
            
            elif cmd == 'load':
                if len(parts) < 2:
                    print("用法: load <目录路径>")
                    continue
                directory_path = ' '.join(parts[1:])
                analyzer.load_files_from_directory(directory_path)
            
            elif cmd == 'build':
                analyzer.build_association_matrix()
            
            elif cmd == 'summary':
                analyzer.print_summary()
            
            elif cmd == 'matrix':
                analyzer.print_matrix()
            
            elif cmd == 'common':
                min_files = int(parts[1]) if len(parts) > 1 else 2
                headers = analyzer.find_common_headers(min_files)
                print(f"\n出现在至少 {min_files} 个文件中的表头:")
                for header, count in headers:
                    print(f"  {header}: {count} 个文件")
            
            elif cmd == 'save':
                if len(parts) < 2:
                    print("用法: save <输出文件路径> [csv/json/npy]")
                    continue
                output_path = parts[1]
                format_type = parts[2] if len(parts) > 2 else 'csv'
                analyzer.save_matrix(output_path, format_type)
            
            elif cmd == 'cooccurrence':
                if len(parts) > 1:
                    analyzer.save_cooccurrence_matrix(parts[1])
                else:
                    print("用法: cooccurrence <输出文件路径>")
            
            elif cmd == 'help':
                print("""
表头关联矩阵分析工具命令:
  load <目录路径>       - 加载目录中所有Excel/CSV文件的表头
  build                 - 构建关联矩阵
  summary               - 打印分析摘要
  matrix                - 打印关联矩阵
  common [n]            - 显示在至少n个文件中出现的表头（默认n=2）
  save <路径> [格式]     - 保存矩阵到文件（格式: csv/json/npy，默认csv）
  cooccurrence <路径>    - 保存表头共现矩阵
  help                  - 显示此帮助信息
  exit / q              - 退出程序
""")
            
            else:
                print(f"未知命令: {cmd}")
                print("输入 'help' 查看命令列表")
        
        except KeyboardInterrupt:
            print("\n\n👋 退出程序")
            break
        except Exception as e:
            print(f"[错误] {e}")


if __name__ == '__main__':
    main()