"""Classbook mashqlarini tekshirish va muallif kiritgan matnni strukturalash.

Mashq formati model yoki view ichiga sochilib ketmaydi. Har bir tur shu
moduldagi bitta kontrakt orqali parse, validate va grade qilinadi. Client
hech qachon to'g'ri javobni yubormaydi; answer key faqat server snapshotida.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError


KIND_SINGLE_CHOICE = "single_choice"
KIND_MULTIPLE_CHOICE = "multiple_choice"
KIND_TRUE_FALSE = "true_false"
KIND_SHORT_ANSWER = "short_answer"
KIND_FILL_BLANK = "fill_blank"
KIND_MATCHING = "matching"
KIND_ORDERING = "ordering"
KIND_CATEGORIZATION = "categorization"
KIND_UNSCRAMBLE = "unscramble"
KIND_POLL = "poll"

CHOICE_KINDS = {KIND_SINGLE_CHOICE, KIND_MULTIPLE_CHOICE, KIND_POLL}
TEXT_KINDS = {KIND_SHORT_ANSWER, KIND_FILL_BLANK}
ORDER_KINDS = {KIND_ORDERING, KIND_UNSCRAMBLE}
ALL_KINDS = CHOICE_KINDS | TEXT_KINDS | ORDER_KINDS | {
    KIND_TRUE_FALSE,
    KIND_MATCHING,
    KIND_CATEGORIZATION,
}
MAX_AUTHOR_ITEMS = 100
MAX_ITEM_LENGTH = 500
MAX_TEXT_ANSWER_LENGTH = 2000


@dataclass(frozen=True)
class Grade:
    fraction: Decimal
    is_correct: bool
    details: dict


def _nonempty_lines(raw):
    lines = [line.strip() for line in (raw or "").splitlines() if line.strip()]
    if len(lines) > MAX_AUTHOR_ITEMS:
        raise ValidationError(f"Bitta mashqda ko'pi bilan {MAX_AUTHOR_ITEMS} ta qator bo'lishi mumkin.")
    if any(len(line) > MAX_ITEM_LENGTH for line in lines):
        raise ValidationError(f"Har bir qator {MAX_ITEM_LENGTH} belgidan oshmasin.")
    return lines


def _stable_items(lines, prefix="o"):
    return [{"id": f"{prefix}{index}", "text": text} for index, text in enumerate(lines, 1)]


def _split_pair(line, separator="="):
    if separator not in line:
        raise ValidationError(f'Har qatorda "{separator}" bo\'lishi kerak: {line}')
    left, right = (part.strip() for part in line.split(separator, 1))
    if not left or not right:
        raise ValidationError(f"Ikki tomon ham to'ldirilishi kerak: {line}")
    return left, right


def parse_author_definition(kind, raw):
    """Teacher formadagi tez yoziladigan matnni config + answer key qiladi."""
    lines = _nonempty_lines(raw)
    if kind in CHOICE_KINDS:
        if len(lines) < 2:
            raise ValidationError("Kamida ikkita variant kiriting.")
        options = []
        correct = []
        for index, line in enumerate(lines, 1):
            marked = line.startswith("*")
            text = line[1:].strip() if marked else line
            if not text:
                raise ValidationError("Bo'sh variant bo'lishi mumkin emas.")
            option_id = f"o{index}"
            options.append({"id": option_id, "text": text})
            if marked:
                correct.append(option_id)
        if kind == KIND_SINGLE_CHOICE and len(correct) != 1:
            raise ValidationError("Bitta javobli mashqda aynan bitta qatorni * bilan belgilang.")
        if kind == KIND_MULTIPLE_CHOICE and not correct:
            raise ValidationError("Kamida bitta to'g'ri variantni * bilan belgilang.")
        if kind == KIND_POLL and correct:
            raise ValidationError("Poll variantlarida * ishlatilmaydi — unda to'g'ri javob yo'q.")
        return {"options": options}, {"correct": correct}

    if kind == KIND_TRUE_FALSE:
        answer = (lines[0] if lines else "").casefold()
        truthy = {"true", "t", "ha", "to'g'ri", "togri", "doğru", "dogru"}
        falsy = {"false", "f", "yo'q", "yoq", "noto'g'ri", "notogri", "yanlış", "yanlis"}
        if answer in truthy:
            correct = True
        elif answer in falsy:
            correct = False
        else:
            raise ValidationError("To'g'ri javob sifatida `ha` yoki `yo'q` yozing.")
        return {
            "options": [{"id": "true", "text": "To'g'ri"}, {"id": "false", "text": "Noto'g'ri"}]
        }, {"correct": correct}

    if kind in TEXT_KINDS:
        if not lines:
            raise ValidationError("Kamida bitta qabul qilinadigan javob yozing.")
        return {"placeholder": "Javobingizni yozing"}, {"accepted": lines, "case_sensitive": False}

    if kind == KIND_MATCHING:
        if len(lines) < 2:
            raise ValidationError("Kamida ikkita juftlik kiriting.")
        left, right, pairs = [], [], {}
        for index, line in enumerate(lines, 1):
            left_text, right_text = _split_pair(line)
            left_id, right_id = f"l{index}", f"r{index}"
            left.append({"id": left_id, "text": left_text})
            right.append({"id": right_id, "text": right_text})
            pairs[left_id] = right_id
        return {"left": left, "right": right}, {"pairs": pairs}

    if kind in ORDER_KINDS:
        if len(lines) < 2:
            raise ValidationError("Kamida ikkita element kiriting.")
        items = _stable_items(lines, "i")
        return {"items": items}, {"order": [item["id"] for item in items]}

    if kind == KIND_CATEGORIZATION:
        if len(lines) < 2:
            raise ValidationError("Kamida ikkita kategoriya qatori kiriting.")
        categories, items, assignments = [], [], {}
        item_index = 0
        for category_index, line in enumerate(lines, 1):
            category, raw_items = _split_pair(line, ":")
            category_id = f"c{category_index}"
            categories.append({"id": category_id, "text": category})
            category_items = [part.strip() for part in raw_items.split(",") if part.strip()]
            if not category_items:
                raise ValidationError(f'"{category}" kategoriyasida element yo\'q.')
            for item_text in category_items:
                item_index += 1
                item_id = f"i{item_index}"
                items.append({"id": item_id, "text": item_text})
                assignments[item_id] = category_id
        return {"categories": categories, "items": items}, {"assignments": assignments}

    raise ValidationError("Noma'lum mashq turi.")


def author_definition(kind, config, answer_key):
    """Saqlangan strukturalangan mashqni teacher textarea ko'rinishiga qaytaradi."""
    if kind in CHOICE_KINDS:
        correct = set(answer_key.get("correct", []))
        return "\n".join(
            f"{'*' if item['id'] in correct else ''}{item['text']}" for item in config.get("options", [])
        )
    if kind == KIND_TRUE_FALSE:
        return "ha" if answer_key.get("correct") is True else "yo'q"
    if kind in TEXT_KINDS:
        return "\n".join(answer_key.get("accepted", []))
    if kind == KIND_MATCHING:
        right = {item["id"]: item["text"] for item in config.get("right", [])}
        pairs = answer_key.get("pairs", {})
        return "\n".join(f"{item['text']} = {right.get(pairs.get(item['id']), '')}" for item in config.get("left", []))
    if kind in ORDER_KINDS:
        by_id = {item["id"]: item["text"] for item in config.get("items", [])}
        return "\n".join(by_id.get(item_id, "") for item_id in answer_key.get("order", []))
    if kind == KIND_CATEGORIZATION:
        categories = {item["id"]: item["text"] for item in config.get("categories", [])}
        grouped = {key: [] for key in categories}
        assignments = answer_key.get("assignments", {})
        for item in config.get("items", []):
            grouped.setdefault(assignments.get(item["id"]), []).append(item["text"])
        return "\n".join(f"{categories[key]}: {', '.join(grouped.get(key, []))}" for key in categories)
    return ""


def validate_exercise_payload(kind, config, answer_key):
    """JSONField qo'lda/admin orqali yozilganda ham kontraktni tekshiradi."""
    if kind not in ALL_KINDS:
        raise ValidationError("Noma'lum mashq turi.")
    if not isinstance(config, dict) or not isinstance(answer_key, dict):
        raise ValidationError("Mashq konfiguratsiyasi obyekt bo'lishi kerak.")

    def item_ids(name, minimum=1):
        items = config.get(name)
        if not isinstance(items, list) or not minimum <= len(items) <= MAX_AUTHOR_ITEMS:
            raise ValidationError(f"{name} ro'yxati {minimum}–{MAX_AUTHOR_ITEMS} element bo'lishi kerak.")
        if any(
            not isinstance(item, dict)
            or not isinstance(item.get("id"), str)
            or not item["id"]
            or not isinstance(item.get("text"), str)
            or not item["text"].strip()
            or len(item["text"]) > MAX_ITEM_LENGTH
            for item in items
        ):
            raise ValidationError(f"{name} elementlari id va qisqa matnga ega bo'lishi kerak.")
        ids = [item["id"] for item in items]
        if len(ids) != len(set(ids)):
            raise ValidationError(f"{name} ichida takroriy id bor.")
        return set(ids)

    if kind in CHOICE_KINDS:
        options = item_ids("options", minimum=2)
        correct = answer_key.get("correct")
        if (
            not isinstance(correct, list)
            or any(not isinstance(item, str) for item in correct)
            or len(correct) != len(set(correct))
            or not set(correct).issubset(options)
        ):
            raise ValidationError("Tanlov javob kaliti variantlarga mos emas.")
        if kind == KIND_SINGLE_CHOICE and len(correct) != 1:
            raise ValidationError("Bitta javobli mashqda aynan bitta to'g'ri variant bo'lishi kerak.")
        if kind == KIND_MULTIPLE_CHOICE and not correct:
            raise ValidationError("Bir nechta javobli mashqda to'g'ri variant bo'lishi kerak.")
        if kind == KIND_POLL and correct:
            raise ValidationError("Poll javob kalitiga ega bo'lmaydi.")
    elif kind == KIND_TRUE_FALSE:
        if item_ids("options", minimum=2) != {"true", "false"}:
            raise ValidationError("To'g'ri/noto'g'ri variant idlari buzilgan.")
        if not isinstance(answer_key.get("correct"), bool):
            raise ValidationError("To'g'ri/noto'g'ri kaliti boolean bo'lishi kerak.")
    elif kind in TEXT_KINDS:
        accepted = answer_key.get("accepted")
        if (
            not isinstance(accepted, list)
            or not accepted
            or len(accepted) > MAX_AUTHOR_ITEMS
            or any(not isinstance(item, str) or not item.strip() or len(item) > MAX_ITEM_LENGTH for item in accepted)
        ):
            raise ValidationError("Qabul qilinadigan javoblar noto'g'ri yoki bo'sh.")
    elif kind == KIND_MATCHING:
        left = item_ids("left", minimum=2)
        right = item_ids("right", minimum=2)
        pairs = answer_key.get("pairs")
        if (
            not isinstance(pairs, dict)
            or any(not isinstance(item, str) for item in pairs.values())
            or set(pairs) != left
            or set(pairs.values()) != right
        ):
            raise ValidationError("Moslashtirish juftliklari elementlarga to'liq mos emas.")
    elif kind in ORDER_KINDS:
        items = item_ids("items", minimum=2)
        order = answer_key.get("order")
        if (
            not isinstance(order, list)
            or any(not isinstance(item, str) for item in order)
            or len(order) != len(set(order))
            or set(order) != items
        ):
            raise ValidationError("Tartib kaliti elementlarga to'liq mos emas.")
    elif kind == KIND_CATEGORIZATION:
        categories = item_ids("categories", minimum=2)
        items = item_ids("items", minimum=2)
        assignments = answer_key.get("assignments")
        if (
            not isinstance(assignments, dict)
            or any(not isinstance(item, str) for item in assignments.values())
            or set(assignments) != items
            or not set(assignments.values()).issubset(categories)
        ):
            raise ValidationError("Kategoriya kaliti elementlarga to'liq mos emas.")


def normalize_text(value):
    value = unicodedata.normalize("NFKC", str(value or ""))
    value = value.replace("’", "'").replace("`", "'")
    value = re.sub(r"\s+", " ", value).strip().casefold()
    return value


def _as_ids(answer):
    if isinstance(answer, list):
        return [str(item) for item in answer]
    if answer in (None, ""):
        return []
    return [str(answer)]


def grade_answer(kind, config, answer_key, answer):
    """Pure grader: bir xil payload har doim bir xil natija beradi."""
    validate_exercise_payload(kind, config, answer_key)
    zero, one = Decimal("0"), Decimal("1")

    if kind == KIND_POLL:
        selected = _as_ids(answer)
        valid = {item["id"] for item in config["options"]}
        if len(selected) != 1 or selected[0] not in valid:
            raise ValidationError("Bitta poll variantini tanlang.")
        return Grade(zero, False, {"graded": False, "selected": selected[0]})

    if kind == KIND_SINGLE_CHOICE:
        selected = _as_ids(answer)
        valid = {item["id"] for item in config["options"]}
        if len(selected) != 1 or selected[0] not in valid:
            raise ValidationError("Bitta variantni tanlang.")
        correct = answer_key["correct"]
        fraction = one if selected[0] in correct else zero
        return Grade(fraction, fraction == one, {"selected": selected, "correct": correct})

    if kind == KIND_MULTIPLE_CHOICE:
        selected = set(_as_ids(answer))
        correct = set(answer_key["correct"])
        valid = {item["id"] for item in config["options"]}
        if not selected or not selected.issubset(valid):
            raise ValidationError("Kamida bitta variantni tanlang.")
        right = len(selected & correct)
        wrong = len(selected - correct)
        fraction = Decimal(max(0, right - wrong)) / Decimal(len(correct))
        return Grade(fraction, selected == correct, {"selected": sorted(selected), "correct": sorted(correct)})

    if kind == KIND_TRUE_FALSE:
        if isinstance(answer, bool):
            selected = answer
        elif isinstance(answer, str) and answer.casefold() in {"true", "false"}:
            selected = answer.casefold() == "true"
        else:
            raise ValidationError("To'g'ri yoki noto'g'ri variantini tanlang.")
        correct = bool(answer_key["correct"])
        fraction = one if selected == correct else zero
        return Grade(fraction, fraction == one, {"selected": selected, "correct": correct})

    if kind in TEXT_KINDS:
        selected = str(answer or "").strip()
        if not selected:
            raise ValidationError("Javob bo'sh bo'lishi mumkin emas.")
        if len(selected) > MAX_TEXT_ANSWER_LENGTH:
            raise ValidationError(f"Javob {MAX_TEXT_ANSWER_LENGTH} belgidan oshmasin.")
        accepted = answer_key["accepted"]
        normalizer = (lambda value: str(value).strip()) if answer_key.get("case_sensitive") else normalize_text
        correct = normalizer(selected) in {normalizer(item) for item in accepted}
        return Grade(one if correct else zero, correct, {"selected": selected, "accepted": accepted})

    if kind == KIND_MATCHING:
        selected = answer if isinstance(answer, dict) else {}
        correct = answer_key["pairs"]
        valid_right = {item["id"] for item in config["right"]}
        if (
            len(selected) > len(correct)
            or any(not isinstance(key, str) or not isinstance(value, str) for key, value in selected.items())
            or not set(selected).issubset(correct)
            or not set(selected.values()).issubset(valid_right)
        ):
            raise ValidationError("Moslashtirish javobi mashq elementlariga mos emas.")
        matched = sum(str(selected.get(left)) == str(right) for left, right in correct.items())
        fraction = Decimal(matched) / Decimal(len(correct))
        return Grade(fraction, fraction == one, {"selected": selected, "correct": correct, "matched": matched})

    if kind in ORDER_KINDS:
        selected = _as_ids(answer)
        correct = [str(item) for item in answer_key["order"]]
        if set(selected) != set(correct) or len(selected) != len(correct):
            raise ValidationError("Barcha elementlarni bir martadan tartiblang.")
        placed = sum(item == correct[index] for index, item in enumerate(selected))
        fraction = Decimal(placed) / Decimal(len(correct))
        return Grade(fraction, fraction == one, {"selected": selected, "correct": correct, "placed": placed})

    if kind == KIND_CATEGORIZATION:
        selected = answer if isinstance(answer, dict) else {}
        correct = answer_key["assignments"]
        valid_categories = {item["id"] for item in config["categories"]}
        if (
            len(selected) > len(correct)
            or any(not isinstance(key, str) or not isinstance(value, str) for key, value in selected.items())
            or not set(selected).issubset(correct)
            or not set(selected.values()).issubset(valid_categories)
        ):
            raise ValidationError("Kategoriya javobi mashq elementlariga mos emas.")
        placed = sum(str(selected.get(item)) == str(category) for item, category in correct.items())
        fraction = Decimal(placed) / Decimal(len(correct))
        return Grade(fraction, fraction == one, {"selected": selected, "correct": correct, "placed": placed})

    raise ValidationError("Bu mashq turi uchun grader topilmadi.")


def points_for_grade(*, grade, max_points, speed_bonus_percent, elapsed_ms, time_limit_seconds):
    """Aniqlik asosiy, tezlik bonusi esa kichik va chegaralangan."""
    max_points = Decimal(str(max_points))
    bonus_cap = (max_points * Decimal(speed_bonus_percent) / Decimal("100")).quantize(Decimal("0.01"))
    base = (max_points * grade.fraction).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if grade.fraction <= 0 or not time_limit_seconds:
        bonus = Decimal("0")
    else:
        limit_ms = Decimal(time_limit_seconds * 1000)
        remaining_ratio = max(Decimal("0"), min(Decimal("1"), (limit_ms - Decimal(elapsed_ms)) / limit_ms))
        bonus = (bonus_cap * remaining_ratio * grade.fraction).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return base + bonus, max_points + bonus_cap, bonus
