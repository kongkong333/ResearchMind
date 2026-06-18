from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.research_service import ResearchService


class _OfflineLLMClient:
    def generate_structured(self, *, prompt: str, schema: dict) -> dict:
        del prompt
        if "gaps" in schema.get("required", []):
            return {
                "gaps": [
                    {
                        "title": "Offline diagnostic gap",
                        "description": "未提供 OpenAI 凭证，当前结果来自离线诊断模式。",
                        "opportunity": "补充真实 API Key 后可生成完整分析。",
                    }
                ],
                "summary": "当前为离线诊断模式，重点用于验证抓取与报告链路是否可执行。",
            }
        return {
            "problem": "离线诊断模式未启用真实论文理解。",
            "method": "使用本地占位分析确保 CLI 链路可验证。",
            "innovation": "将抓取、趋势和报告流程与在线模型调用解耦。",
            "results": "可在未配置 OpenAI 凭证时验证脚本执行与报告写出。",
            "limitations": "内容不代表真实模型分析结果。",
            "research_gap": "缺少真实 LLM 支撑的细粒度研究洞察。",
            "research_opportunity": "补充有效 OpenAI 凭证后运行完整工作流。",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the weekly research workflow.")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--report-dir", default="reports")
    parser.add_argument("--openai-api-key", default=None)
    parser.add_argument("--openai-model", default=None)
    parser.add_argument("--openai-base-url", default=None)
    args = parser.parse_args()

    service = ResearchService(report_output_dir=Path(args.report_dir))
    if not (args.openai_api_key and args.openai_model):
        service._build_llm_client = lambda **kwargs: _OfflineLLMClient()
    result = service.run(
        topic=args.topic,
        openai_api_key=args.openai_api_key,
        openai_model=args.openai_model,
        openai_base_url=args.openai_base_url,
    )
    print(result["report_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
