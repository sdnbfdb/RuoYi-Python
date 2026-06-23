#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel/CSV 表头处理综合工具
整合功能: 表头提取 → 关联矩阵分析 → 向量化编码存储
"""

import os
import sys

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from excel_viewer import HeaderExtractor
from header_matrix import HeaderMatrixAnalyzer
from header_embedding import HeaderEmbeddingEncoder


class ExcelHeaderToolkit:
    def __init__(self):
        self.extractor = HeaderExtractor()
        self.matrix_analyzer = HeaderMatrixAnalyzer()
        self.encoder = HeaderEmbeddingEncoder()
        self.current_directory = ""
    
    def load_files(self, directory_path: str) -> bool:
        """加载目录中的所有文件"""
        if not os.path.exists(directory_path):
            print(f"[错误] 目录不存在: {directory_path}")
            return False
        
        self.current_directory = directory_path
        
        print(f"\n" + "=" * 60)
        print(f"正在加载文件: {directory_path}")
        print(f"=" * 60)
        
        # 步骤1: 提取表头
        print("\n[步骤1/3] 提取表头...")
        self.extractor.extract_from_directory(directory_path)
        
        # 步骤2: 构建关联矩阵
        print("\n[步骤2/3] 构建关联矩阵...")
        self.matrix_analyzer.load_files_from_directory(directory_path)
        self.matrix_analyzer.build_association_matrix()
        
        # 步骤3: 向量化编码
        print("\n[步骤3/3] 向量化编码...")
        self.encoder.encode_directory(directory_path)
        
        print(f"\n" + "=" * 60)
        print("所有数据加载完成!")
        print(f"=" * 60)
        return True
    
    def extract_headers(self):
        """提取并显示表头"""
        if not self.current_directory:
            print("[错误] 请先加载文件 (使用 load 命令)")
            return
        
        self.extractor.extract_from_directory(self.current_directory)
    
    def analyze_matrix(self):
        """分析关联矩阵"""
        if not self.current_directory:
            print("[错误] 请先加载文件 (使用 load 命令)")
            return
        
        self.matrix_analyzer.print_summary()
    
    def encode_vectors(self):
        """向量化编码"""
        if not self.current_directory:
            print("[错误] 请先加载文件 (使用 load 命令)")
            return
        
        self.encoder.print_statistics()
    
    def save_all(self, output_dir: str):
        """保存所有分析结果"""
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"\n" + "=" * 60)
        print(f"正在保存结果到: {output_dir}")
        print(f"=" * 60)
        
        # 保存关联矩阵
        matrix_path = os.path.join(output_dir, 'header_association_matrix.csv')
        self.matrix_analyzer.save_matrix(matrix_path, 'csv')
        
        # 保存共现矩阵
        cooccurrence_path = os.path.join(output_dir, 'header_cooccurrence_matrix.csv')
        self.matrix_analyzer.save_cooccurrence_matrix(cooccurrence_path)
        
        # 保存向量化结果
        self.encoder.save_embeddings(output_dir)
        
        print(f"\n" + "=" * 60)
        print("所有结果保存完成!")
        print(f"=" * 60)
    
    def run_full_analysis(self, input_dir: str, output_dir: str):
        """运行完整分析流程"""
        print(f"\n" + "=" * 60)
        print("          开始完整分析流程")
        print(f"=" * 60)
        
        # 加载文件
        if not self.load_files(input_dir):
            return
        
        # 显示分析摘要
        print("\n" + "-" * 60)
        print("分析摘要")
        print("-" * 60)
        
        # 表头统计
        total_headers = len(self.matrix_analyzer.all_headers)
        total_files = len(self.matrix_analyzer.file_list)
        print(f"\n[文件] 文件数量: {total_files}")
        print(f"[表头] 表头总数: {total_headers}")
        
        # 公共表头
        common_headers = self.matrix_analyzer.find_common_headers(min_files=2)
        print(f"[关联] 公共表头（出现在≥2个文件中）: {len(common_headers)} 个")
        
        # 保存结果
        self.save_all(output_dir)
        
        print("\n[完成] 完整分析流程完成!")
    
    def find_similar(self, query_header: str, top_k: int = 5):
        """查找相似表头"""
        if not self.encoder.header_vectors:
            print("[错误] 请先加载文件 (使用 load 命令)")
            return
        
        results = self.encoder.find_similar_headers(query_header, top_k)
        print(f"\n与 '{query_header}' 相似的表头:")
        for i, res in enumerate(results, 1):
            print(f"  {i}. {res['header']} (相似度: {res['similarity']:.4f})")
    
    def compare_headers(self, header1: str, header2: str):
        """比较两个表头的相似度"""
        sim = self.encoder.calculate_similarity(header1, header2)
        print(f"\n'{header1}' 与 '{header2}' 的相似度: {sim:.4f}")


def print_help():
    """打印帮助信息"""
    help_text = """
Excel/CSV 表头处理综合工具

命令列表:
  load <目录路径>           - 加载目录中的所有文件
  extract                   - 提取并显示所有表头
  matrix                    - 分析并显示关联矩阵
  encode                    - 显示向量化统计
  find <表头> [top_k]       - 查找相似表头（默认top_k=5）
  compare <h1> <h2>         - 比较两个表头的相似度
  save <输出目录>           - 保存所有分析结果
  run <输入目录> <输出目录>  - 运行完整分析流程
  help                      - 显示此帮助信息
  exit / q                  - 退出程序

示例:
  > load ./data_folder
  > extract
  > matrix
  > find 用户ID 10
  > compare 姓名 名称
  > save ./output
  > run ./data ./output
"""
    print(help_text)


def main():
    """主函数"""
    print("=" * 60)
    print("        Excel/CSV 表头处理综合工具")
    print("=" * 60)
    print("整合功能: 表头提取 → 关联矩阵 → 向量化编码")
    print("支持格式: .xlsx, .xls, .csv")
    print("输入 'help' 查看命令列表")
    print("=" * 60)
    
    toolkit = ExcelHeaderToolkit()
    
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
            
            elif cmd == 'load':
                if len(parts) < 2:
                    print("用法: load <目录路径>")
                    continue
                directory_path = ' '.join(parts[1:])
                toolkit.load_files(directory_path)
            
            elif cmd == 'extract':
                toolkit.extract_headers()
            
            elif cmd == 'matrix':
                toolkit.analyze_matrix()
            
            elif cmd == 'encode':
                toolkit.encode_vectors()
            
            elif cmd == 'find':
                if len(parts) < 2:
                    print("用法: find <表头> [top_k]")
                    continue
                query = parts[1]
                top_k = int(parts[2]) if len(parts) > 2 else 5
                toolkit.find_similar(query, top_k)
            
            elif cmd == 'compare':
                if len(parts) < 3:
                    print("用法: compare <表头1> <表头2>")
                    continue
                toolkit.compare_headers(parts[1], parts[2])
            
            elif cmd == 'save':
                if len(parts) < 2:
                    print("用法: save <输出目录>")
                    continue
                output_dir = ' '.join(parts[1:])
                toolkit.save_all(output_dir)
            
            elif cmd == 'run':
                if len(parts) < 3:
                    print("用法: run <输入目录> <输出目录>")
                    continue
                input_dir = parts[1]
                output_dir = ' '.join(parts[2:])
                toolkit.run_full_analysis(input_dir, output_dir)
            
            else:
                print(f"未知命令: {cmd}")
                print("输入 'help' 查看命令列表")
        
        except KeyboardInterrupt:
            print("\n\n👋 退出程序")
            break
        except Exception as e:
            print(f"[错误] {e}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Excel/CSV 表头处理综合工具')
    parser.add_argument('--input', '-i', help='输入目录路径')
    parser.add_argument('--output', '-o', help='输出目录路径')
    parser.add_argument('--run', '-r', action='store_true', help='运行完整分析流程')
    
    args = parser.parse_args()
    
    if args.run and args.input and args.output:
        toolkit = ExcelHeaderToolkit()
        toolkit.run_full_analysis(args.input, args.output)
    else:
        main()