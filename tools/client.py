"""Call the FastGPT dataset searchTest API and shape the chunks."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

DEFAULT_TIMEOUT = 90
SEARCH_MODES = {"embedding", "fullTextRecall", "mixedRecall"}
SCORE_PRIORITY = ("reRank", "embedding", "fullText", "rrf")


class FastGPTApiError(Exception):
    def __init__(self, status: int, payload: Any):
        self.status = status
        self.payload = payload
        super().__init__(format_api_error(status, payload))


def format_api_error(status: int, payload: Any) -> str:
    if isinstance(payload, dict):
        code = payload.get("code") or ""
        message = payload.get("message") or payload.get("statusText") or ""
        if code and message and str(code) not in {"200", ""}:
            return f"FastGPT 接口错误 {status} {code}: {message}"
        if message:
            return f"FastGPT 接口错误 {status}: {message}"
    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return f"FastGPT 接口错误 {status}: {text}"


def normalize_base_url(api_base: str | None) -> str:
    if not api_base or not str(api_base).strip():
        raise ValueError("请填写 FastGPT 地址，例如 https://cloud.fastgpt.cn 或 http://localhost:3000。")
    base = str(api_base).strip().rstrip("/")
    if not base.startswith(("http://", "https://")):
        raise ValueError("FastGPT 地址需要以 http:// 或 https:// 开头。")
    suffix = "/api/core/dataset/searchTest"
    if base.endswith(suffix):
        base = base[: -len(suffix)]
    if not base.endswith("/api"):
        base = f"{base}/api"
    return base


def as_bool(value: Any, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return default


def optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def optional_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError("数值参数不能是布尔值。")
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except ValueError as exc:
        raise ValueError(f"无法把 {value!r} 转成数字。") from exc


def require_unit_interval(name: str, value: float) -> float:
    if value < 0 or value > 1:
        raise ValueError(f"{name} 的范围是 0 到 1。")
    return value


def build_search_body(parameters: dict[str, Any]) -> dict[str, Any]:
    dataset_id = optional_text(parameters.get("datasetId"))
    text = optional_text(parameters.get("text"))
    if not dataset_id:
        raise ValueError("datasetId 不能为空。请填写 FastGPT 知识库 ID。")
    if not text:
        raise ValueError("text 不能为空。请填写需要检索的内容。")

    search_mode = optional_text(parameters.get("searchMode")) or "embedding"
    if search_mode not in SEARCH_MODES:
        raise ValueError("searchMode 只能是 embedding、fullTextRecall 或 mixedRecall。")

    limit = optional_number(parameters.get("limit"))
    if limit is None:
        limit = 5000
    if limit < 1 or limit > 20000 or not float(limit).is_integer():
        raise ValueError("limit 是最大 Token 数，只能是 1 到 20000 的整数。")

    using_extension = as_bool(parameters.get("datasetSearchUsingExtensionQuery"), False)
    embedding_weight = optional_number(parameters.get("embeddingWeight"))
    body: dict[str, Any] = {
        "datasetId": dataset_id,
        "text": text,
        "queryImageUrls": parse_image_keys(parameters.get("queryImageUrls")),
        "searchMode": search_mode,
        "usingReRank": as_bool(parameters.get("usingReRank"), False),
        "limit": int(limit),
        "datasetSearchUsingExtensionQuery": using_extension,
    }

    if search_mode == "mixedRecall":
        if embedding_weight is None:
            embedding_weight = 0.5
        body["embeddingWeight"] = require_unit_interval("embeddingWeight", embedding_weight)

    similarity = optional_number(parameters.get("similarity"))
    if similarity is not None:
        body["similarity"] = require_unit_interval("similarity", similarity)

    rerank_weight = optional_number(parameters.get("rerankWeight"))
    if body["usingReRank"]:
        if rerank_weight is None:
            rerank_weight = 0.5
        body["rerankWeight"] = require_unit_interval("rerankWeight", rerank_weight)
        _put_text(body, "rerankModelId", parameters.get("rerankModelId"))

    if using_extension:
        body["datasetSearchExtensionBg"] = optional_text(parameters.get("datasetSearchExtensionBg")) or ""
        _put_text(body, "datasetSearchExtensionModelId", parameters.get("datasetSearchExtensionModelId"))

    return body


def parse_image_keys(value: Any) -> list[str]:
    if value is None or value == "" or value == []:
        return []
    if isinstance(value, list):
        keys = [str(item).strip() for item in value if str(item).strip()]
    else:
        keys = [part.strip() for part in str(value).split(",") if part.strip()]
    if len(keys) > 10:
        raise ValueError("queryImageUrls 最多 10 个，并且必须是 FastGPT 预签名返回的临时 key。")
    return keys


def _put_text(body: dict[str, Any], key: str, value: Any) -> None:
    text = optional_text(value)
    if text is not None:
        body[key] = text


def primary_score(score: Any) -> tuple[float | None, list[dict[str, Any]] | None]:
    if isinstance(score, bool):
        return None, None
    if isinstance(score, (int, float)):
        return float(score), None
    if not isinstance(score, list):
        return None, None

    details: list[dict[str, Any]] = []
    by_type: dict[str, float] = {}
    for item in score:
        if not isinstance(item, dict):
            continue
        value = item.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        kind = str(item.get("type") or "")
        number = float(value)
        detail: dict[str, Any] = {"type": kind, "value": number}
        index = item.get("index")
        if isinstance(index, int) and not isinstance(index, bool):
            detail["index"] = index
        details.append(detail)
        by_type.setdefault(kind, number)
    if not details:
        return None, []
    for kind in SCORE_PRIORITY:
        if kind in by_type:
            return by_type[kind], details
    return details[0]["value"], details


def chunk_text(question: Any, answer: Any) -> str:
    question_text = str(question or "").strip()
    answer_text = str(answer or "").strip()
    if question_text and answer_text:
        return f"{question_text}\n{answer_text}"
    return question_text or answer_text


def map_records(items: list[Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        score, details = primary_score(item.get("score"))
        records.append(
            {
                "content": chunk_text(item.get("q"), item.get("a")),
                "q": item.get("q") or "",
                "a": item.get("a") or "",
                "score": score,
                "score_details": details,
                "id": item.get("id") or "",
                "dataset_id": item.get("datasetId") or "",
                "collection_id": item.get("collectionId") or "",
                "source_name": item.get("sourceName") or "",
                "source_id": item.get("sourceId") or "",
                "chunk_index": item.get("chunkIndex"),
                "update_time": item.get("updateTime") or "",
                "position": index,
            }
        )
    return records


def join_context(records: list[dict[str, Any]]) -> str:
    return "\n\n".join(record["content"] for record in records if record.get("content"))


def unwrap_data(payload: Any) -> Any:
    if not isinstance(payload, dict) or "code" not in payload:
        return payload
    code = payload.get("code")
    if code not in (200, "200", None):
        message = payload.get("message") or payload.get("statusText") or payload
        raise ValueError(f"FastGPT 接口错误 {code}: {message}")
    return payload.get("data", payload)


def search_result(payload: Any) -> dict[str, Any]:
    data = unwrap_data(payload)
    if isinstance(data, list):
        return {"list": data}
    if isinstance(data, dict):
        listed = data.get("list")
        if listed is None:
            return {**data, "list": []}
        if not isinstance(listed, list):
            raise ValueError("FastGPT 检索结果的 list 不是数组。")
        return data
    raise ValueError("FastGPT 检索返回的不是对象。")


def request_json(
    method: str,
    url: str,
    api_key: str,
    payload: dict[str, Any] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Any:
    if not api_key or not str(api_key).strip():
        raise ValueError("请填写 FastGPT API Key。")
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {str(api_key).strip()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed: Any = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = raw
        raise FastGPTApiError(exc.code, parsed) from exc
    except urllib.error.URLError as exc:
        raise ValueError(
            "无法连接 FastGPT。请确认插件进程能访问所填地址。"
            f"原因: {exc.reason}"
        ) from exc
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("FastGPT 接口返回的不是 JSON。") from exc


MODEL_PARAMETER_TYPES = {
    "rerankModelId": "rerank",
    "datasetSearchExtensionModelId": "llm",
}


def list_model_options(credentials: dict[str, Any], model_type: str) -> list[dict[str, str]]:
    api_base = optional_text(credentials.get("api_base"))
    api_key = optional_text(credentials.get("api_key"))
    if not api_base or not api_key:
        raise ValueError("请先填写并保存 FastGPT 地址和 API Key。保存成功后，再打开模型下拉。")
    base = normalize_base_url(api_base)
    try:
        payload = request_json("GET", f"{base}/core/ai/model/catalog", api_key)
    except FastGPTApiError as exc:
        if exc.status == 401:
            raise ValueError("FastGPT API Key 无效。请重新保存凭证后，再打开模型下拉。") from exc
        raise
    models = _catalog_models(payload)
    options: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in models:
        if not isinstance(item, dict) or item.get("type") != model_type:
            continue
        if item.get("isActive") is False:
            continue
        model_id = optional_text(item.get("modelId"))
        if not model_id or model_id in seen:
            continue
        seen.add(model_id)
        name = optional_text(item.get("name")) or optional_text(item.get("model")) or model_id
        provider = optional_text(item.get("provider"))
        label = f"{name} ({provider})" if provider else name
        option = {"value": model_id, "label": label}
        avatar = optional_text(item.get("avatar"))
        if avatar and avatar.startswith(("http://", "https://")):
            option["icon"] = avatar
        options.append(option)
    options.sort(key=lambda option: option["label"].lower())
    if not options:
        kind = "重排模型" if model_type == "rerank" else "语言模型"
        raise ValueError(f"当前账号没有可用的{kind}。请确认凭证已保存，且该账号在 FastGPT 中启用了对应模型。")
    return options


def _catalog_models(payload: Any) -> list[Any]:
    data = unwrap_data(payload)
    if not isinstance(data, dict):
        return []
    inner = data.get("data")
    if isinstance(inner, dict) and isinstance(inner.get("models"), list):
        return inner["models"]
    models = data.get("models")
    return models if isinstance(models, list) else []


def validate_credentials(credentials: dict[str, Any]) -> None:
    base = normalize_base_url(credentials.get("api_base"))
    api_key = str(credentials.get("api_key") or "")
    try:
        payload = request_json("POST", f"{base}/core/dataset/list", api_key, {"parentId": None})
    except FastGPTApiError as exc:
        if exc.status == 401:
            raise ValueError("FastGPT API Key 无效。") from exc
        if exc.status == 403:
            raise ValueError("当前密钥没有列出知识库的权限。") from exc
        raise
    unwrap_data(payload)


def retrieve(
    credentials: dict[str, Any],
    parameters: dict[str, Any],
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    base = normalize_base_url(credentials.get("api_base"))
    api_key = str(credentials.get("api_key") or "")
    body = build_search_body(parameters)
    payload = request_json(
        "POST",
        f"{base}/core/dataset/searchTest",
        api_key,
        body,
        timeout=timeout,
    )
    found = search_result(payload)
    result = map_records(found.get("list") or [])
    return {
        "datasetId": body["datasetId"],
        "text": body["text"],
        "duration": found.get("duration"),
        "limit": found.get("limit", body["limit"]),
        "searchMode": found.get("searchMode", body["searchMode"]),
        "usingReRank": found.get("usingReRank", body["usingReRank"]),
        "similarity": found.get("similarity", body.get("similarity")),
        "queryExtensionModel": found.get("queryExtensionModel"),
        "result": result,
        "context": join_context(result),
    }
