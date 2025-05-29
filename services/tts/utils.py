import re

# 预编译正则表达式模式
_EMOTICON_PATTERN = re.compile(
    r'[:;=\-][D\)(\|/\\oOpP]|'  # 西式颜文字 :) :( :D 等
    r'<3|</3|><|>\.<|'          # 爱心和简单表情
    r'\^[_\-o]\^|'              # ^_^ ^-^ ^o^
    r'[（(][＾^>＜<][_\-ω∀∇○〇][＾^>＜<][）)]|'  # 日式基本颜文字
    r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000027BF\U0001F900-\U0001F9FF]'  # Unicode表情
)
_BRACKET_PATTERN = re.compile(r'[（(][^）)]*[）)]')  # 括号及其内容
_WHITESPACE_PATTERN = re.compile(r'\s+')  # 多个空白字符

def get_clean_tts_text(text: str) -> str:
    """
    简单清洗TTS文本：去除颜文字和括号内容
    """
    if not text or not isinstance(text, str):
        return ""
    # 1. 去除颜文字
    cleaned_text = _EMOTICON_PATTERN.sub('', text)
    # 2. 去除括号及其内容
    cleaned_text = _BRACKET_PATTERN.sub('', cleaned_text)
    # 3. 标准化空白字符
    cleaned_text = _WHITESPACE_PATTERN.sub(' ', cleaned_text)
    return cleaned_text.strip()
