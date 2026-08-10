import re


_ARABIC_GREETING_RESPONSES = {
    "hello": "أهلًا! أنا جاهز أساعدك. يمكنك سؤالي عن الملفات الموجودة داخل المشروع.",
    "how_are_you": "أهلًا! أنا جاهز لمساعدتك. اسألني عن أي ملف أو معلومة داخل المشروع.",
    "thanks": "العفو! لو محتاج أي مساعدة أخرى في ملفات المشروع أنا جاهز.",
    "bye": "إلى اللقاء! يمكنك العودة في أي وقت للسؤال عن ملفات المشروع.",
    "capabilities": "أستطيع البحث داخل ملفات المشروع، تلخيصها، استخراج المعلومات منها، والمقارنة بين محتوياتها.",
}

_ENGLISH_GREETING_RESPONSES = {
    "hello": "Hello! I am ready to help. You can ask me about the files in this project.",
    "how_are_you": "Hello! I am ready to help with your project documents.",
    "thanks": "You are welcome! I am here if you need more help with the project files.",
    "bye": "Goodbye! You can return anytime to ask about the project files.",
    "capabilities": "I can search, summarize, extract information from, and compare the documents in this project.",
}


def _normalize_message(message: str) -> str:
    value = str(message or "").strip().lower()
    value = re.sub(r"[!?؟.,،;:]+", "", value)
    value = re.sub(r"\s+", " ", value)
    return value


def local_conversation_response(message: str) -> str | None:
    value = _normalize_message(message)
    if not value or len(value) > 80:
        return None

    arabic = bool(re.search(r"[\u0600-\u06ff]", value))
    responses = _ARABIC_GREETING_RESPONSES if arabic else _ENGLISH_GREETING_RESPONSES

    exact_groups = {
        "hello": {
            "hi", "hello", "hey", "good morning", "good evening",
            "مرحبا", "مرحباً", "اهلا", "أهلا", "السلام عليكم",
            "صباح الخير", "مساء الخير", "هاي",
        },
        "how_are_you": {
            "how are you", "how are you doing", "عامل ايه", "عامل إيه",
            "اخبارك ايه", "أخبارك إيه", "ازيك", "إزيك", "كيف حالك",
        },
        "thanks": {
            "thanks", "thank you", "thx", "شكرا", "شكراً", "متشكر",
        },
        "bye": {
            "bye", "goodbye", "see you", "مع السلامة", "سلام",
            "إلى اللقاء", "الى اللقاء",
        },
        "capabilities": {
            "what can you do", "what do you do", "who are you",
            "بتعمل ايه", "بتعمل إيه", "تقدر تعمل ايه", "تقدر تعمل إيه",
            "انت مين", "أنت مين", "من أنت", "ماذا تستطيع أن تفعل",
        },
    }

    for intent, values in exact_groups.items():
        normalized_values = {_normalize_message(item) for item in values}
        if value in normalized_values:
            return responses[intent]
    return None
