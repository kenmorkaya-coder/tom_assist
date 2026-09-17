"""Align Gemma's supervised assistant context to its native inference prefix.

The pinned template strips thought-channel markers from assistant messages but
adds an empty thought channel to inference prompts. This adapter preserves the
native inference prefix and native turn suffix for supervised answers. It edits
neither the checkpoint nor the installed tokenizer/template.
"""
VERSION = "gemma-supervised-prefix/1"


class AlignedChatTokenizer:
    def __init__(self, tokenizer):
        self._base = tokenizer

    def __getattr__(self, name):
        return getattr(self._base, name)

    def apply_chat_template(self, messages, **kwargs):
        if kwargs.get("enable_thinking", False):
            raise ValueError("this extraction experiment disables thinking")
        options = {**kwargs, "enable_thinking": False}
        if options.get("add_generation_prompt") or not messages or messages[-1]["role"] != "assistant":
            return self._base.apply_chat_template(messages, **options)
        if len(messages) != 2 or [m["role"] for m in messages] != ["user", "assistant"]:
            raise ValueError("aligned training requires one user/assistant pair")
        answer = messages[-1]["content"]
        if not isinstance(answer, str) or not answer or answer != answer.strip():
            raise ValueError("training answer must be nonempty unpadded text")
        text_options = {**options, "tokenize": False, "return_dict": False}
        native = self._base.apply_chat_template(messages, **text_options)
        if not native.endswith(answer + "<turn|>\n"):
            raise ValueError("native template changed or altered the supervised answer")
        prefix = self._base.apply_chat_template(
            messages[:-1], **{**text_options, "add_generation_prompt": True}
        )
        rendered = prefix + answer + "<turn|>\n"
        if options.get("tokenize", True) is False:
            return rendered
        if options.get("return_dict", False):
            raise ValueError("this training adapter returns token lists only")
        return self._base.encode(rendered, add_special_tokens=False)


def check_alignment(tokenizer, messages):
    """Return prefix/answer lengths only after exact text and token checks."""
    aligned = AlignedChatTokenizer(tokenizer)
    prefix = tokenizer.apply_chat_template(messages[:-1], tokenize=False, add_generation_prompt=True, enable_thinking=False)
    text = aligned.apply_chat_template(messages, tokenize=False)
    prefix_tokens = tokenizer.apply_chat_template(messages[:-1], return_dict=False, add_generation_prompt=True, enable_thinking=False)
    tokens = aligned.apply_chat_template(messages, return_dict=False)
    if not text.startswith(prefix) or tokens[:len(prefix_tokens)] != prefix_tokens:
        raise ValueError("supervised/inference prefix mismatch")
    # The first supervised token is the first answer token, not a later JSON key.
    suffix = tokenizer.decode(tokens[len(prefix_tokens):])
    if not suffix.startswith(messages[-1]["content"]):
        raise ValueError("answer boundary is masked or altered")
    return {"prefix_tokens": len(prefix_tokens), "total_tokens": len(tokens)}
