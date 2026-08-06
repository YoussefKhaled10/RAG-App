import re
from importlib import import_module
from pathlib import Path
from string import Template

class TemplateParser:
    LANGUAGE_PATTERN = re.compile(r"^[a-z]{2}(?:-[a-z]{2})?$")
    GROUP_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")
    KEY_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")

    def __init__(
        self,
        language: str | None = None,
        default_language: str = "en",
    ):
        self.current_path = Path(__file__).resolve().parent
        self.default_language = self._normalize_language(
            default_language
        )
        self.language = self.default_language
        self.set_language(language)

    @classmethod
    def _normalize_language(cls, language: str | None) -> str:
        value = str(language or "").strip().lower().replace("_", "-")
        if not cls.LANGUAGE_PATTERN.fullmatch(value):
            return "en"
        return value

    def _language_directory(self, language: str) -> Path:
        return self.current_path / "locales" / language

    def set_language(self, language: str | None = None) -> str:
        selected_language = self._normalize_language(
            language or self.default_language
        )
        if self._language_directory(selected_language).is_dir():
            self.language = selected_language
        else:
            self.language = self.default_language
        return self.language

    def get(
        self,
        group: str,
        key: str,
        vars: dict | None = None,
    ) -> str | None:
        if not self.GROUP_PATTERN.fullmatch(str(group or "")):
            return None
        if not self.KEY_PATTERN.fullmatch(str(key or "")):
            return None

        variables = {
            str(name): "" if value is None else str(value)
            for name, value in (vars or {}).items()
        }

        targeted_language = self.language
        group_path = (
            self._language_directory(targeted_language)
            / f"{group}.py"
        )

        if not group_path.is_file():
            targeted_language = self.default_language
            group_path = (
                self._language_directory(targeted_language)
                / f"{group}.py"
            )

        if not group_path.is_file():
            return None

        module_path = (
            "stores.llm.templates.locales."
            f"{targeted_language}.{group}"
        )

        try:
            module = import_module(module_path)
        except (ImportError, ModuleNotFoundError, SyntaxError):
            return None

        template_object = getattr(module, key, None)
        if template_object is None:
            return None

        if isinstance(template_object, Template):
            return template_object.safe_substitute(variables)
        if isinstance(template_object, str):
            return Template(template_object).safe_substitute(
                variables
            )
        return None