"""
Camada única pra falar com diferentes LLMs (Anthropic, OpenAI ou Ollama local).
Assim os agentes não sabem (nem precisam saber) qual motor está por trás.
"""

import os


DEFAULT_MODELS = {
    "anthropic": "claude-haiku-4-5-20251001",  # rápido e barato, bom pra rodar muitos ticks
    "openai": "gpt-4o-mini",
    "ollama": "llama3",
}


class LLMClient:
    def __init__(self, provider=None, model=None):
        self.provider = (provider or os.getenv("LLM_PROVIDER", "ollama")).lower()
        self.model = model or os.getenv("LLM_MODEL") or DEFAULT_MODELS.get(self.provider, "llama3")

    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 200) -> str:
        if self.provider == "anthropic":
            return self._call_anthropic(system_prompt, user_prompt, max_tokens)
        if self.provider == "openai":
            return self._call_openai(system_prompt, user_prompt, max_tokens)
        if self.provider == "ollama":
            return self._call_ollama(system_prompt, user_prompt, max_tokens)
        raise ValueError(
            f"Provedor de LLM desconhecido: '{self.provider}'. "
            "Use 'anthropic', 'openai' ou 'ollama' na variável LLM_PROVIDER."
        )

    def _call_anthropic(self, system_prompt, user_prompt, max_tokens):
        import anthropic

        client = anthropic.Anthropic()  # lê ANTHROPIC_API_KEY do ambiente
        resp = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return resp.content[0].text.strip()

    def _call_openai(self, system_prompt, user_prompt, max_tokens):
        from openai import OpenAI

        client = OpenAI()  # lê OPENAI_API_KEY do ambiente
        resp = client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return resp.choices[0].message.content.strip()

    def _call_ollama(self, system_prompt, user_prompt, max_tokens):
        import requests

        resp = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "options": {"num_predict": max_tokens},
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()
