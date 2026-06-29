# utils/json_extractor.py
"""
共享 JSON 提取工具 — 从 LLM 文本输出中提取 JSON。

跨模块使用:
  retrieval_agent.py, knowledge_builder.py, test_runner.py
"""

import re
import json
from typing import Optional, Dict, Any, List, Union


def extract_json(text: str) -> Optional[Union[Dict, List]]:
    """从文本中提取 JSON 对象或数组。

    尝试顺序:
      1. <FILES_START> ... <FILES_END> 标记
      2. <MEMORY_START> ... </MEMORY_START> 标记
      3. ```json ... ``` 代码块
      4. ``` ... ``` 代码块
      5. 直接 {} 对象匹配
      6. 直接 [] 数组匹配

    Args:
        text: LLM 输出的原始文本

    Returns:
        解析后的 JSON 对象/数组，或 None
    """
    if not text or not text.strip():
        return None

    # 1. <FILES_START> ... <FILES_END>
    match = re.search(r'<FILES_START>\s*([\s\S]*?)\s*</FILES_END>', text, re.DOTALL)
    if match:
        inner = match.group(1).strip()
        try:
            return json.loads(inner)
        except json.JSONDecodeError:
            # 尝试清理非法控制字符
            cleaned = ''.join(ch for ch in inner if ord(ch) >= 32 or ch in '\n\r\t')
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

    # 2. <MEMORY_START> ... </MEMORY_START>
    match = re.search(r'<MEMORY_START>\s*([\s\S]*?)\s*</MEMORY_START>', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 3. ```json ... ```
    match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 4. ``` ... ```
    match = re.search(r'```\s*([\s\S]*?)\s*```', text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 5. JSON 对象 { ... } — 匹配最外层
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start != -1:
                try:
                    obj = json.loads(text[start:i+1])
                    if isinstance(obj, dict) and obj:  # 非空 dict
                        return obj
                except json.JSONDecodeError:
                    pass
                start = -1

    # 6. JSON 数组 [ ... ]
    arr_start = text.find('[')
    if arr_start != -1:
        arr_end = text.rfind(']')
        if arr_end != -1 and arr_end > arr_start:
            try:
                return json.loads(text[arr_start:arr_end+1])
            except json.JSONDecodeError:
                pass

    return None


def extract_json_dict(text: str) -> Optional[Dict]:
    """从文本中提取 JSON 对象（仅对象，非数组）。

    与 test_runner._extract_json 行为兼容。
    """
    if not text or not text.strip():
        return None

    # <MEMORY_START> ... </MEMORY_START>
    match = re.search(r'<MEMORY_START>\s*([\s\S]*?)\s*</MEMORY_START>', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # ```json ... ```
    match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 查找最外层 { ... }
    start = text.find('{')
    if start == -1:
        return None
    brace_count = 0
    end = -1
    for i in range(start, len(text)):
        if text[i] == '{':
            brace_count += 1
        elif text[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                end = i + 1
                break
    if end != -1:
        candidate = text[start:end]
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass

    # 回退：找最后一对 {}
    last_brace = text.rfind('}')
    if last_brace != -1:
        first_brace = text.rfind('{', 0, last_brace)
        if first_brace != -1:
            try:
                return json.loads(text[first_brace:last_brace+1])
            except json.JSONDecodeError:
                pass

    return None
