import pytest
from gateway.gemma_training_alignment import AlignedChatTokenizer, check_alignment


class NativeTemplateStub:
    """Reproduce the observed missing training marker, not model behavior."""
    def encode(self,text,add_special_tokens=False):return list(text.encode())
    def decode(self,tokens):return bytes(tokens).decode()
    def apply_chat_template(self,messages,tokenize=True,add_generation_prompt=False,**kwargs):
        prefix='<bos>user:'+messages[0]['content']+'<turn|>\nmodel\n'
        text=prefix+('<|channel>thought\n<channel|>' if add_generation_prompt else messages[-1]['content']+'<turn|>\n')
        return self.encode(text) if tokenize else text


def test_training_uses_exact_native_inference_prefix_and_complete_answer():
    native=NativeTemplateStub();messages=[{'role':'user','content':'source'},{'role':'assistant','content':'{"a":1}'}]
    assert not native.apply_chat_template(messages,tokenize=False).startswith(native.apply_chat_template(messages[:-1],tokenize=False,add_generation_prompt=True))
    aligned=AlignedChatTokenizer(native)
    assert aligned.apply_chat_template(messages,tokenize=False).endswith('<|channel>thought\n<channel|>{"a":1}<turn|>\n')
    result=check_alignment(native,messages)
    assert result['total_tokens']>result['prefix_tokens']


def test_no_answer_repair_or_silent_template_change():
    messages=[{'role':'user','content':'source'},{'role':'assistant','content':' JSON '}]
    with pytest.raises(ValueError):AlignedChatTokenizer(NativeTemplateStub()).apply_chat_template(messages)
    class Altered(NativeTemplateStub):
        def apply_chat_template(self,*args,**kwargs):return 'different suffix'
    messages[-1]['content']='{}'
    with pytest.raises(ValueError,match='template changed'):AlignedChatTokenizer(Altered()).apply_chat_template(messages)


def test_no_thinking_or_unsupported_multi_turn_training():
    t=AlignedChatTokenizer(NativeTemplateStub())
    m=[{'role':'user','content':'x'},{'role':'assistant','content':'{}'}]
    with pytest.raises(ValueError):t.apply_chat_template(m,enable_thinking=True)
    with pytest.raises(ValueError):t.apply_chat_template(m+m)
