#!/usr/bin/env python3
"""端到端冒烟验证：选题 → 脚本 → 分镜 → 提示词包 → 导出文本。

不依赖 pytest / 数据库 / Docker / LLM Key，只用 Python 标准库（3.9+），
针对一个**已经在运行的 Agent 服务**（默认 http://localhost:8000）做真实调用，
并把最终可复制使用的提示词包写到本地文件，用来确认「确实拿到了产出物」。

用法：
    make smoke
    python3 scripts/smoke_journey.py --agent http://localhost:8000
    python3 scripts/smoke_journey.py --models sora-turbo,kling-v3,midjourney-v7
    python3 scripts/smoke_journey.py --web http://localhost:3000   # 顺带验证 Next.js 代理
    make smoke SMOKE_WEB=http://localhost:3000

退出码：0 全部通过；1 有断言失败；2 服务不可达。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterator, List, Set, Tuple

DEFAULT_MODELS = ["sora-turbo", "kling-v3", "midjourney-v7"]
CJK = re.compile(r"[\u4e00-\u9fff]")
GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"


def paint(text: str, color: str) -> str:
    return color + text + RESET if sys.stdout.isatty() else text


def http_json(url: str, payload: Dict[str, Any] = None, timeout: float = 20.0) -> Dict[str, Any]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - 固定本机地址
        return json.loads(resp.read().decode())


def sse_run(url: str, payload: Dict[str, Any], timeout: float = 120.0) -> Iterator[Tuple[str, Dict[str, Any]]]:
    """从 Agent 的 SSE 端点逐条产出 (event_name, data)。"""
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        event = ""
        for raw in resp:
            line = raw.decode("utf-8").rstrip("\n\r")
            if line.startswith("event: "):
                event = line[7:].strip()
            elif line.startswith("data: ") and event:
                yield event, json.loads(line[6:])
                event = ""


def check(results: List[bool], cond: bool, label: str, detail: str = "") -> None:
    if cond:
        print("  " + paint("✓", GREEN) + " " + label)
    else:
        tail = paint("  → " + detail, DIM) if detail else ""
        print("  " + paint("✗", RED) + " " + label + tail)
    results.append(bool(cond))


def collect(results: List[bool]) -> int:
    failed = results.count(False)
    print()
    if failed:
        print(paint("✗ 冒烟未通过：" + str(failed) + " 项失败（共 " + str(len(results)) + " 项）", RED))
        return 1
    print(paint("✓ 冒烟全部通过：" + str(len(results)) + " 项", GREEN))
    return 0


def duplicate_clause(text: str) -> bool:
    """同一条提示词里出现两次以上的完整短语，通常意味着字段被重复拼接。"""
    clauses = [c.strip().lower() for c in re.split(r"[,;，、]", text) if len(c.strip()) > 12]
    return len(clauses) != len(set(clauses))


def main() -> int:
    ap = argparse.ArgumentParser(description="Mago 端到端冒烟验证")
    ap.add_argument("--agent", default="http://localhost:8000", help="Agent 服务地址")
    ap.add_argument("--web", default="", help="可选：Next.js 地址，用于验证 /api/agent 代理")
    ap.add_argument("--models", default=",".join(DEFAULT_MODELS), help="逗号分隔的目标模型 id")
    ap.add_argument("--topic", default="口红测评，第一视角，30秒", help="测试选题")
    ap.add_argument("--out", default="/tmp/mago-smoke-pack.md", help="提示词包输出文件")
    args = ap.parse_args()

    base = args.agent.rstrip("/")
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    results: List[bool] = []

    print(paint("Mago 冒烟验证：真实调用服务端，确认真的能拿到可复制的产出物", YELLOW))
    print(paint("Agent=" + base + "  选题=" + repr(args.topic) + "  模型=" + ",".join(models), DIM))
    print()

    # ---------- 1. 服务可用性 ----------
    print("[1/5] 服务可用性")
    try:
        health = http_json(base + "/health", timeout=8)
        check(results, health.get("status") == "ok", "GET /health", json.dumps(health)[:200])
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        print(paint("  无法连接 " + base + "/health：" + str(exc), RED))
        print()
        print("  先启动 Agent：make dev-agent  或  make demo  或双击「启动Agent服务.command」")
        return 2

    # ---------- 2. 模型清单 ----------
    print("[2/5] 提示词模型清单")
    try:
        listing = http_json(base + "/api/v1/agent/prompt-models", timeout=15)
    except Exception as exc:  # noqa: BLE001
        check(results, False, "GET /prompt-models", str(exc))
        return collect(results)
    catalog: Dict[str, Any] = {}
    for m in listing.get("models", []):
        if isinstance(m, dict) and m.get("model_id"):
            catalog[str(m["model_id"])] = m
    known = list(catalog)
    check(results, len(known) >= 10, "可用模型 " + str(len(known)) + " 个", "、".join(known))
    untagged = sorted(k for k, v in catalog.items() if v.get("language") not in ("zh", "en"))
    check(
        results,
        not untagged and any(v.get("language") == "zh" for v in catalog.values()),
        "每个模型都声明了提示词语言（前端据此标注 中文/EN）",
        "缺少或非法 language：" + "、".join(untagged) if untagged else "没有任何 zh 模型，语言标注可能失效",
    )
    for mid in models:
        hint = "未知模型，可选：" + "、".join(known[:8]) + "…"
        check(results, mid in catalog, "请求的模型存在：" + mid, "" if mid in catalog else hint)
    if results.count(False):
        return collect(results)

    # ---------- 3. 创作链路 ----------
    print("[3/5] 选题 → 脚本 → 分镜（mode=quick：走内置模板引擎，不消耗任何模型额度）")
    events: Dict[str, Dict[str, Any]] = {}
    try:
        for name, data in sse_run(
            base + "/api/v1/agent/run",
            {"message": args.topic, "mode": "quick", "approved": True, "history": []},
        ):
            if name == "error":
                check(results, False, "创作链路返回 error 事件", json.dumps(data, ensure_ascii=False)[:300])
                return collect(results)
            events[name] = data  # 同类事件保留最后一份
    except Exception as exc:  # noqa: BLE001
        check(results, False, "POST /run（SSE）", str(exc))
        return collect(results)

    provenance = events.get("meta", {})
    script_obj = (events.get("script") or {}).get("script") or {}
    check(results, bool(script_obj), "产出脚本" + ("" if provenance.get("llm_configured") else "（模板引擎，未配置 LLM Key）"), "只收到事件：" + str(sorted(events)))
    title = str(script_obj.get("title", "")).strip()
    check(results, bool(title), "脚本标题：" + title)
    check(results, len(str(script_obj.get("body_text", ""))) > 30, "脚本正文非空", str(script_obj.get("body_text"))[:80])
    check(results, title.count("第一视角") <= 1, "标题没有重复堆砌关键词", title)

    storyboard = (events.get("storyboard") or {}).get("storyboard") or {}
    shots = storyboard.get("shots") or []
    check(results, len(shots) >= 1, "分镜镜头数：" + str(len(shots)), "分镜未生成，后续步骤跳过")
    if not shots:
        return collect(results)
    check(
        results,
        all(str(s.get("visual_description") or "").strip() for s in shots),
        "每个镜头都有画面描述",
    )
    bad_dur = [i + 1 for i, s in enumerate(shots) if float(s.get("duration_sec") or 0) <= 0]
    check(results, not bad_dur, "每个镜头都有时长", "异常镜头：" + str(bad_dur))
    no_shot_size = [i + 1 for i, s in enumerate(shots) if not str(s.get("shot_size") or "").strip()]
    check(results, not no_shot_size, "每个镜头都有景别", "缺失镜头：" + str(no_shot_size))

    # ---------- 4. 提示词包 ----------
    print("[4/5] 分镜 → 多模型提示词包")
    try:
        pack_resp = http_json(
            base + "/api/v1/agent/prompt-pack",
            {"storyboard": storyboard, "script": script_obj, "target_models": models},
            timeout=60,
        )
    except urllib.error.HTTPError as exc:
        check(results, False, "POST /prompt-pack 返回 HTTP " + str(exc.code), exc.read().decode("utf-8", "ignore")[:300])
        return collect(results)
    except Exception as exc:  # noqa: BLE001
        check(results, False, "POST /prompt-pack", str(exc))
        return collect(results)

    package = pack_resp.get("package") or {}
    # 服务端契约：package.prompts[] = 「镜头 × 模型」的扁平列表
    items = [it for it in (package.get("prompts") or []) if isinstance(it, dict)]
    expect = len(shots) * len(models)
    check(
        results,
        len(items) == expect,
        "提示词条数 " + str(len(items)) + "（" + str(len(shots)) + " 镜头 × " + str(len(models)) + " 模型）",
        "期望 " + str(expect),
    )
    check(results, bool(package.get("aspect_ratio")), "整包宽高比：" + str(package.get("aspect_ratio")))
    if not items:
        print(paint("  提示词列表为空，后续断言跳过（请看 Agent 日志）", RED))
        return collect(results)

    check(results, not [it for it in items if not str(it.get("positive_prompt", "")).strip()], "没有空提示词")
    short = [it for it in items if len(str(it.get("positive_prompt", ""))) < 20]
    check(results, not short, "提示词长度合理", str(len(short)) + " 条过短")

    seen: Set[Tuple[Any, Any]] = {(it.get("shot_index"), it.get("model_id")) for it in items}
    missing = [(i + 1, m) for i in range(len(shots)) for m in models if (i + 1, m) not in seen]
    check(results, not missing, "镜头 × 模型矩阵完整", "缺失 " + str(missing[:4]))

    maxlen_bad = [
        it for it in items
        if int((catalog.get(str(it.get("model_id"))) or {}).get("max_length") or 0) > 0
        and len(str(it.get("positive_prompt", ""))) > int(catalog[str(it.get("model_id"))]["max_length"])
    ]
    check(results, not maxlen_bad, "提示词长度不超过模型上限", "超限 " + str([str(i.get("model_id")) for i in maxlen_bad[:3]]))

    want_ratio = str(package.get("aspect_ratio") or "")
    no_ratio = [
        it for it in items
        if want_ratio
        and want_ratio not in json.dumps(it.get("parameters") or {}, ensure_ascii=False)
        and want_ratio not in str(it.get("positive_prompt", ""))
    ]
    detail = ""
    if no_ratio:
        detail = str(len(no_ratio)) + " 条缺失，例：shot " + str(no_ratio[0].get("shot_index")) + " / " + str(no_ratio[0].get("model_id"))
    check(results, not no_ratio, "宽高比写进了参数或提示词", detail)

    dup = [it for it in items if duplicate_clause(str(it.get("positive_prompt", "")))]
    check(results, not dup, "提示词内没有整段重复的描述", "例：" + str(dup[0].get("model_id")) if dup else "")

    silent_cjk = [
        it for it in items
        if it.get("language") == "en"
        and CJK.search(str(it.get("positive_prompt", "")))
        and not any("中文" in str(w) for w in (it.get("warnings") or []))
    ]
    check(results, not silent_cjk, "英文系模型的中文内容都带翻译提醒", str(len(silent_cjk)) + " 条静默")

    misplaced = [
        it for it in items
        if (catalog.get(str(it.get("model_id"))) or {}).get("language") == "zh"
        and any("翻译成英文" in str(w) for w in (it.get("warnings") or []))
    ]
    check(
        results,
        not misplaced,
        "中文模型不会被误判成英文模型（不出现「请翻译成英文」）",
        "例：" + str(misplaced[0].get("model_id")) if misplaced else "",
    )

    neg_bad = [
        it for it in items
        if (catalog.get(str(it.get("model_id"))) or {}).get("supports_negative") is False
        and str(it.get("negative_prompt", "")).strip()
    ]
    check(results, not neg_bad, "不支持负向提示词的模型没有硬塞负向词", str([i.get("model_id") for i in neg_bad]))

    no_duration = [
        it for it in items
        if it.get("prompt_type") == "video" and not (it.get("parameters") or {}).get("duration") and not it.get("duration_sec")
    ]
    check(results, not no_duration, "视频模型都带了时长参数", str([i.get("model_id") for i in no_duration]))

    over = [it for it in items if float(it.get("duration_sec") or 0) > 10]
    check(results, not over, "时长都在引擎上限（10s）以内", str(len(over)) + " 条超出")

    # ---------- 5. 产出物落地 ----------
    print("[5/5] 产出物与代理链路")
    lines: List[str] = [
        "# 提示词包 · " + (title or args.topic),
        "",
        "- 生成方式：" + str(pack_resp.get("generated_by", "prompt_engine_template")) + "（模板引擎，不消耗模型额度）",
        "- 宽高比：" + str(package.get("aspect_ratio")) + "　镜头数：" + str(len(shots)) + "　模型：" + "、".join(models),
        "- LLM Key：" + ("已配置 " + str(provenance.get("model")) if provenance.get("llm_configured") else "未配置（走内置模板引擎，仍产出可直接使用的提示词）"),
    ]
    grouped: Dict[Any, List[Dict[str, Any]]] = {}
    for it in items:
        grouped.setdefault(it.get("shot_index"), []).append(it)
    for idx in sorted(grouped, key=lambda v: (v is None, v)):
        shot = shots[idx - 1] if isinstance(idx, int) and 0 < idx <= len(shots) else {}
        lines += ["", "## 镜头 " + str(idx) + "（" + str(shot.get("duration_sec")) + "s · " + str(shot.get("shot_size")) + "）", ""]
        if shot.get("visual_description"):
            lines += ["画面：" + str(shot["visual_description"]), ""]
        if shot.get("dialogue"):
            lines += ["台词：" + str(shot["dialogue"]), ""]
        for it in grouped[idx]:
            lines += ["### " + str(it.get("model_name") or it.get("model_id")), "", "```", str(it.get("positive_prompt", "")).strip(), "```", ""]
            if it.get("negative_prompt"):
                lines += ["负向提示词：`" + str(it["negative_prompt"]) + "`", ""]
            params = it.get("parameters") or {}
            if params:
                lines += ["参数：`" + json.dumps(params, ensure_ascii=False) + "`", ""]
            for warn in it.get("warnings") or []:
                lines += ["- ⚠️ " + str(warn), ""]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    check(results, Path(args.out).stat().st_size > 500, "提示词包已写入：" + args.out + "（" + str(len(lines)) + " 行，可直接复制使用）")

    sample = items[0]
    print()
    print(paint("─" * 72, DIM))
    print(paint("样例产出（复制进对应平台即可生成）：", YELLOW))
    print(paint("─" * 72, DIM))
    print("[" + str(sample.get("model_id")) + "] shot " + str(sample.get("shot_index")))
    print(str(sample.get("positive_prompt", ""))[:400])
    print(paint("参数：" + json.dumps(sample.get("parameters") or {}, ensure_ascii=False), DIM))
    for warn in (sample.get("warnings") or [])[:2]:
        print(paint("提醒：" + str(warn), DIM))
    print(paint("─" * 72, DIM))

    if args.web:
        web_base = args.web.rstrip("/")
        try:
            proxied = http_json(web_base + "/api/agent/health", timeout=10)
            check(results, proxied.get("agent") == "running", "Next.js 代理可用：" + web_base + "/api/agent/*", json.dumps(proxied)[:120])
        except Exception as exc:  # noqa: BLE001
            check(results, False, "Next.js 代理：" + web_base + "/api/agent/health", str(exc))

    return collect(results)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(paint("\n已中断", YELLOW))
        sys.exit(130)
