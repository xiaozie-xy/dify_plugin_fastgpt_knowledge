from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities import ParameterOption
from dify_plugin.entities.parameters import I18nObject
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.client import MODEL_PARAMETER_TYPES, list_model_options, retrieve


class FastGPTKnowledgeRetrievalTool(Tool):
    def _fetch_parameter_options(self, parameter: str) -> list[ParameterOption]:
        model_type = MODEL_PARAMETER_TYPES.get(parameter)
        if model_type is None:
            return []
        try:
            items = list_model_options(self.runtime.credentials or {}, model_type)
        except Exception as exc:
            message = str(exc) or "Save the FastGPT URL and API key before opening this list."
            return [ParameterOption(value="", label=I18nObject(en_US=message, zh_Hans=message))]
        return [
            ParameterOption(
                value=item["value"],
                label=I18nObject(en_US=item["label"], zh_Hans=item["label"]),
                icon=item.get("icon"),
            )
            for item in items
        ]

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        retrieved = retrieve(self.runtime.credentials, tool_parameters)
        yield self.create_variable_message("result", retrieved["result"])
        yield self.create_variable_message("context", retrieved["context"])
        yield self.create_json_message(
            {
                "datasetId": retrieved["datasetId"],
                "text": retrieved["text"],
                "duration": retrieved["duration"],
                "limit": retrieved["limit"],
                "searchMode": retrieved["searchMode"],
                "usingReRank": retrieved["usingReRank"],
                "similarity": retrieved["similarity"],
                "queryExtensionModel": retrieved["queryExtensionModel"],
                "result": retrieved["result"],
            }
        )
        yield self.create_text_message(retrieved["context"] or "No chunks were retrieved.")
