"""
GraphRAG API 路由
提供知识图谱索引构建和查询接口
"""

from flask import Flask, jsonify, request
import os
import sys
import subprocess
import threading
from pathlib import Path

# Graph 目录路径
GRAPH_DIR = Path(__file__).resolve().parent.parent / "old" / "Graph"


def register_graph_routes(app: Flask):
    """注册 GraphRAG 相关路由"""

    @app.route("/api/graph/build", methods=["POST"])
    def api_graph_build():
        """构建 GraphRAG 索引（异步执行）"""
        try:
            # 异步执行构建脚本
            def run_build():
                cmd = [sys.executable, str(GRAPH_DIR / "build_graph_index.py")]
                subprocess.run(cmd, cwd=str(GRAPH_DIR))

            thread = threading.Thread(target=run_build, daemon=True)
            thread.start()

            return jsonify({
                "success": True,
                "message": "索引构建任务已启动，请稍后查看结果",
                "data": {
                    "status": "running",
                    "output_dir": str(GRAPH_DIR / "output"),
                    "lancedb_dir": str(GRAPH_DIR / "lancedb")
                }
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"启动构建失败: {str(e)}"
            }), 500

    @app.route("/api/graph/status", methods=["GET"])
    def api_graph_status():
        """获取 GraphRAG 索引状态"""
        try:
            artifacts_dir = GRAPH_DIR / "output"
            lancedb_dir = GRAPH_DIR / "output" / "lancedb"

            artifacts_exists = artifacts_dir.exists()
            lancedb_exists = lancedb_dir.exists()

            required_files = [
                "entities.parquet",
                "relationships.parquet",
                "text_units.parquet",
                "documents.parquet",
            ]

            files_status = {}
            if artifacts_exists:
                for filename in required_files:
                    filepath = artifacts_dir / filename
                    files_status[filename] = {
                        "exists": filepath.exists(),
                        "size": filepath.stat().st_size if filepath.exists() else 0
                    }

            has_core_files = all(files_status.get(f, {}).get("exists", False) for f in ["entities.parquet", "relationships.parquet"])
            status = "ready" if artifacts_exists and has_core_files else "not_built"

            return jsonify({
                "success": True,
                "data": {
                    "status": status,
                    "artifacts_dir": str(artifacts_dir),
                    "lancedb_dir": str(lancedb_dir),
                    "artifacts_exists": artifacts_exists,
                    "lancedb_exists": lancedb_exists,
                    "files": files_status,
                    "has_core_files": has_core_files
                }
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"获取状态失败: {str(e)}"
            }), 500

    @app.route("/api/graph/search", methods=["POST"])
    def api_graph_search():
        """执行 GraphRAG 搜索"""
        try:
            data = request.get_json() or {}
            query = data.get("query", "").strip()
            mode = data.get("mode", "local")  # local 或 global

            if not query:
                return jsonify({
                    "success": False,
                    "message": "查询内容不能为空"
                }), 400

            # 检查索引是否存在
            artifacts_dir = GRAPH_DIR / "output"
            entities_file = artifacts_dir / "entities.parquet"
            if not artifacts_dir.exists() or not entities_file.exists():
                return jsonify({
                    "success": False,
                    "message": "索引尚未构建，请先运行构建任务"
                }), 400

            # 调用查询脚本
            cmd = [
                sys.executable,
                str(GRAPH_DIR / "query_graph.py"),
                query,
                "--mode", mode
            ]

            result = subprocess.run(
                cmd,
                cwd=str(GRAPH_DIR),
                capture_output=True,
                text=True,
                timeout=60
            )

            output = result.stdout
            error = result.stderr

            if result.returncode != 0:
                return jsonify({
                    "success": False,
                    "message": f"查询失败: {error}",
                    "output": output
                }), 500

            # 提取搜索结果（从输出中解析）
            lines = output.split("\n")
            result_text = ""
            in_result = False
            for line in lines:
                if "搜索结果:" in line:
                    in_result = True
                    continue
                if in_result and line.startswith("=" * 60):
                    break
                if in_result:
                    result_text += line + "\n"

            return jsonify({
                "success": True,
                "data": {
                    "query": query,
                    "mode": mode,
                    "result": result_text.strip(),
                    "full_output": output
                }
            })
        except subprocess.TimeoutExpired:
            return jsonify({
                "success": False,
                "message": "查询超时（60秒）"
            }), 500
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"查询失败: {str(e)}"
            }), 500

    @app.route("/api/graph/entities", methods=["GET"])
    def api_graph_entities():
        """获取图谱实体列表"""
        try:
            import pandas as pd

            entities_file = GRAPH_DIR / "output" / "entities.parquet"
            if not entities_file.exists():
                return jsonify({
                    "success": False,
                    "message": "实体文件不存在，请先构建索引"
                }), 404

            df = pd.read_parquet(entities_file)

            entities = []
            for _, row in df.iterrows():
                entities.append({
                    "id": row.get("id", ""),
                    "name": row.get("title", row.get("id", "")),
                    "type": row.get("type", ""),
                    "description": row.get("description", ""),
                    "frequency": row.get("frequency", 0),
                    "degree": row.get("degree", 0)
                })

            entities = sorted(entities, key=lambda x: x.get("degree", 0), reverse=True)[:50]

            return jsonify({
                "success": True,
                "data": {
                    "total": len(entities),
                    "entities": entities
                }
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"获取实体失败: {str(e)}"
            }), 500

    @app.route("/api/graph/relationships", methods=["GET"])
    def api_graph_relationships():
        """获取图谱关系列表"""
        try:
            import pandas as pd

            rel_file = GRAPH_DIR / "output" / "relationships.parquet"
            if not rel_file.exists():
                return jsonify({
                    "success": False,
                    "message": "关系文件不存在，请先构建索引"
                }), 404

            df = pd.read_parquet(rel_file)

            relationships = []
            for _, row in df.iterrows():
                relationships.append({
                    "id": row.get("id", ""),
                    "source": row.get("source", ""),
                    "target": row.get("target", ""),
                    "type": row.get("type", ""),
                    "description": row.get("description", ""),
                    "weight": row.get("weight", 1)
                })

            relationships = sorted(relationships, key=lambda x: x.get("weight", 1), reverse=True)[:50]

            return jsonify({
                "success": True,
                "data": {
                    "total": len(relationships),
                    "relationships": relationships
                }
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"获取关系失败: {str(e)}"
            }), 500

    @app.route("/api/graph/communities", methods=["GET"])
    def api_graph_communities():
        """获取社区报告列表"""
        try:
            import pandas as pd

            report_file = GRAPH_DIR / "output" / "communities.parquet"
            if not report_file.exists():
                return jsonify({
                    "success": False,
                    "message": "社区报告文件不存在，请先构建索引"
                }), 404

            df = pd.read_parquet(report_file)

            communities = []
            for _, row in df.iterrows():
                communities.append({
                    "id": row.get("id", ""),
                    "title": row.get("title", ""),
                    "level": row.get("level", 0),
                    "size": row.get("size", 0),
                    "entity_count": len(row.get("entity_ids", [])) if isinstance(row.get("entity_ids"), list) else 0,
                    "relationship_count": len(row.get("relationship_ids", [])) if isinstance(row.get("relationship_ids"), list) else 0
                })

            communities = sorted(communities, key=lambda x: x.get("size", 0), reverse=True)

            return jsonify({
                "success": True,
                "data": {
                    "total": len(communities),
                    "communities": communities
                }
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"获取社区报告失败: {str(e)}"
            }), 500