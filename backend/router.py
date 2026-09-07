import os
import re

class TaskRouter:
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
    CODE_EXTENSIONS = {".py", ".js", ".java", ".cpp", ".c", ".html", ".css", ".sql", ".sh", ".json"}
    TEXT_EXTENSIONS = {".txt", ".md", ".csv"}
    PDF_EXTENSIONS = {".pdf"}

    VISION_KEYWORDS = ["image", "photo", "picture", "screenshot", "diagram", "graph", "chart", "visual"]
    
    CODING_PATTERNS = [
        r"\bwrite.*?code\b",
        r"\bcreate.*?code\b",
        r"\bgenerate.*?code\b",
        r"\bgive me.*?code\b",
        r"\bprovide.*?code\b",
        r"\b(?:python|java|javascript|js|c\+\+|cpp|c|html|css|sql) (?:program|code|script)\b",
        r"\bwrite.*?(?:python|java|javascript|js|c\+\+|cpp|c) (?:program|code|script)\b",
        r"\bgenerate.*?(?:python|java|javascript|js|c\+\+|cpp|c) (?:program|code|script)\b",
        r"\bwrite (?:a )?program in (?:python|java|javascript|js|c\+\+|cpp|c)\b",
        r"\bcreate (?:a )?program in (?:python|java|javascript|js|c\+\+|cpp|c)\b",
        r"\bsolve .* in (?:python|java|javascript|js|c\+\+|cpp|c)\b",
        r"\bimplement .* in (?:python|java|javascript|js|c\+\+|cpp|c)\b",
        r"\bdebug (?:this )?code\b",
        r"\bfix (?:this )?code\b",
        r"\brefactor (?:this )?code\b",
        r"\bexplain this code\b",
        r"\brun (?:this )?(?:code|program|script)\b",
    ]

    def route(self, prompt: str, file_path: str = None) -> str:
        prompt_lower = prompt.lower() if prompt else ""

        if file_path:
            ext = os.path.splitext(file_path)[1].lower()
            if ext in self.IMAGE_EXTENSIONS or ext in self.PDF_EXTENSIONS:
                return "qwen2.5vl:7b"
            if ext in self.CODE_EXTENSIONS:
                return "qwen2.5-coder:3b"
            return "qwen2.5:3b"

        if any(kw in prompt_lower for kw in self.VISION_KEYWORDS):
            return "qwen2.5vl:7b"

        for pattern in self.CODING_PATTERNS:
            if re.search(pattern, prompt_lower, re.IGNORECASE):
                return "qwen2.5-coder:3b"

        return "qwen2.5:3b"