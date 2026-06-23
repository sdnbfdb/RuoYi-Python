#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel/CSV 文件表头提取工具
支持 .xlsx, .xls, .csv 文件格式
"""

import os
import csv
from typing import List

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("[警告] pandas 未安装，将使用纯 Python 方式读取 CSV")


class HeaderExtractor:
    def __init__(self):
        self.headers = []
        self.file_path = ""
        self.file_type = ""

    def extract_header(self, file_path: str) -> List[str]:
        """提取 Excel 或 CSV 文件的表头"""
        if not os.path.exists(file_path):
            print(f"[错误] 文件不存在: {file_path}")
            return []

        self.file_path = file_path
        _, ext = os.path.splitext(file_path)
        self.file_type = ext.lower()

        try:
            if self.file_type in ['.xlsx', '.xls']:
                return self._extract_excel_header(file_path)
            elif self.file_type == '.csv':
                return self._extract_csv_header(file_path)
            else:
                print(f"[错误] 不支持的文件格式: {ext}")
                return []
        except Exception as e:
            print(f"[错误] 提取表头失败: {str(e)}")
            return []

    def _extract_excel_header(self, file_path: str) -> List[str]:
        """提取 Excel 文件的表头"""
        if not PANDAS_AVAILABLE:
            print("[错误] 需要安装 pandas 来读取 Excel 文件")
            print("请运行: pip install pandas openpyxl xlrd")
            return []

        try:
            df = pd.read_excel(file_path, nrows=0)  # 只读取表头
            self.headers = df.columns.tolist()
            self._print_header()
            return self.headers
        except Exception as e:
            print(f"[错误] 读取 Excel 表头失败: {str(e)}")
            return []

    def _extract_csv_header(self, file_path: str) -> List[str]:
        """提取 CSV 文件的表头"""
        if PANDAS_AVAILABLE:
            try:
                df = pd.read_csv(file_path, nrows=0, encoding='utf-8')
                self.headers = df.columns.tolist()
                self._print_header()
                return self.headers
            except Exception as e:
                print(f"[警告] pandas 读取失败，尝试纯 Python 方式: {str(e)}")

        # 纯 Python 方式读取 CSV 表头
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                first_row = next(reader, None)
            
            if first_row is None:
                print("[错误] CSV 文件为空")
                return []

            self.headers = first_row
            self._print_header()
            return self.headers
        except Exception as e:
            print(f"[错误] 读取 CSV 表头失败: {str(e)}")
            return []

    def _print_header(self):
        """打印表头"""
        print(f"\n=== 文件: {os.path.basename(self.file_path)} ===")
        print(f"格式: {self.file_type}")
        print(f"列数: {len(self.headers)}")
        print(f"表头:")
        for i, header in enumerate(self.headers, 1):
            print(f"  {i}. {header}")

    def extract_from_directory(self, directory_path: str) -> dict:
        """从目录中提取所有 Excel/CSV 文件的表头"""
        if not os.path.exists(directory_path):
            print(f"[错误] 目录不存在: {directory_path}")
            return {}

        print(f"=" * 60)
        print(f"批量提取目录文件表头: {directory_path}")
        print(f"=" * 60)

        supported_exts = ['.xlsx', '.xls', '.csv']
        results = {}

        for filename in os.listdir(directory_path):
            _, ext = os.path.splitext(filename)
            if ext.lower() in supported_exts:
                file_path = os.path.join(directory_path, filename)
                headers = self.extract_header(file_path)
                if headers:
                    results[filename] = headers

        print(f"\n" + "=" * 60)
        print(f"提取完成! 共处理 {len(results)} 个文件")
        print(f"=" * 60)
        return results


def print_help():
    """打印帮助信息"""
    help_text = """
Excel/CSV 文件表头提取工具

命令列表:
  extract <文件路径>       - 提取单个文件的表头
  batch <目录路径>         - 批量提取目录中所有文件的表头
  help                    - 显示此帮助信息
  exit / q                - 退出程序

示例:
  > extract data.xlsx
  > batch ./data_folder
"""
    print(help_text)


def main():
    """主函数"""
    print("=" * 60)
    print("        Excel/CSV 文件表头提取工具")
    print("=" * 60)
    print("支持格式: .xlsx, .xls, .csv")
    print("输入 'help' 查看命令列表")
    print("=" * 60)

    extractor = HeaderExtractor()

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

            elif cmd == 'help':
                print_help()

            elif cmd == 'extract':
                if len(parts) < 2:
                    print("用法: extract <文件路径>")
                    continue
                file_path = ' '.join(parts[1:])
                extractor.extract_header(file_path)

            elif cmd == 'batch':
                if len(parts) < 2:
                    print("用法: batch <目录路径>")
                    continue
                directory_path = ' '.join(parts[1:])
                extractor.extract_from_directory(directory_path)

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