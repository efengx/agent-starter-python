# src/agent_starter_python/sentence_processor.py
import logging

class SentenceStreamProcessor:
    def __init__(self, sentence_enders: str = ".?!"):
        self._buffer = ""
        self._sentence_enders = sentence_enders

    def process(self, text_chunk: str) -> list[str]:
        """处理传入的文本块，并返回找到的完整句子列表。"""
        self._buffer += text_chunk
        sentences = []
        
        last_end_index = -1
        for i, char in enumerate(self._buffer):
            if char in self._sentence_enders:
                sentence = self._buffer[:i+1].strip()
                if sentence:
                    sentences.append(sentence)
                last_end_index = i

        if last_end_index != -1:
            self._buffer = self._buffer[last_end_index+1:]

        return sentences

    def flush(self) -> str:
        """返回缓冲区中剩余的任何文本。"""
        remaining_text = self._buffer.strip()
        self._buffer = ""
        return remaining_text