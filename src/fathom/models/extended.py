"""
Extended ChatDeepSeek with support for automatically handling reasoning_content

Problem Solved: In tool invocation scenarios, DeepSeek Reasoner requires the assistant message to include `reasoning_content` as a top-level field, but LangChain only puts it in `additional_kwargs`.

This extended class will automatically promote the `reasoning_content` from `additional_kwargs` to a top-level field in the message when sending a request.
"""

from typing import Any

from langchain_core.language_models import LanguageModelInput
from langchain_deepseek import ChatDeepSeek


class ChatDeepSeekReasoningAware(ChatDeepSeek):
    """Most reliable implementation: completely rewrite the messsage serializationn logic."""

    def _get_request_payload(
        self,
        input_: LanguageModelInput,
        *,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> dict:
        """构建请求 payload，完全控制消息序列化"""
        import json

        from langchain_core.messages import (
            AIMessage,
            BaseMessage,
            HumanMessage,
            SystemMessage,
            ToolMessage,
            convert_to_messages,
        )

        # 调用父类方法获取基础 payload
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)

        # 获取原始消息列表
        if isinstance(input_, str):
            # 如果是字符串，不需要处理
            return payload

        if isinstance(input_, BaseMessage):
            messages: list[BaseMessage] = [input_]
        else:
            # Use LangChain helper to normalize MessageLikeRepresentation → BaseMessage
            messages = convert_to_messages(input_)

        # 🔥 重新构建消息列表，正确处理 reasoning_content
        new_messages = []
        payload_messages = payload.get("messages", [])

        for i, msg in enumerate(messages):
            if isinstance(msg, SystemMessage):
                new_messages.append(
                    {
                        "role": "system",
                        "content": msg.content,
                    }
                )

            elif isinstance(msg, HumanMessage):
                new_messages.append(
                    {
                        "role": "user",
                        "content": msg.content,
                    }
                )

            elif isinstance(msg, AIMessage):
                msg_dict = {
                    "role": "assistant",
                    "content": msg.content or "",
                }

                # 处理 tool_calls
                if msg.tool_calls:
                    msg_dict["tool_calls"] = [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc["args"])
                                if isinstance(tc["args"], dict)
                                else tc["args"],
                            },
                        }
                        for tc in msg.tool_calls
                    ]

                # 🔥 关键：把 reasoning_content 提升为顶级字段
                reasoning_content = msg.additional_kwargs.get("reasoning_content")
                if reasoning_content:
                    msg_dict["reasoning_content"] = reasoning_content

                new_messages.append(msg_dict)

            elif isinstance(msg, ToolMessage):
                new_messages.append(
                    {
                        "role": "tool",
                        "content": msg.content
                        if isinstance(msg.content, str)
                        else json.dumps(msg.content),
                        "tool_call_id": msg.tool_call_id,
                    }
                )

            else:
                # 其他类型，使用父类序列化的结果（从 payload 中获取）
                if i < len(payload_messages):
                    new_messages.append(payload_messages[i])
                else:
                    # 如果 payload 中没有对应消息，尝试通用转换
                    new_messages.append(
                        {
                            "role": getattr(msg, "type", "user"),
                            "content": getattr(msg, "content", str(msg)),
                        }
                    )

        # 替换 payload 中的消息
        if new_messages:
            payload["messages"] = new_messages

        return payload
