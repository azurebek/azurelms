"""Canonical typed design schema; no arbitrary CSS, HTML or external assets."""
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import json
import math
from pathlib import Path
import re


CATALOG = json.loads(Path(__file__).with_name("design_catalog.json").read_text(encoding="utf-8"))
FIELDS = tuple(field for group in CATALOG["groups"] for field in group["fields"])
BY_KEY = {field["key"]: field for field in FIELDS}


class DesignValidationError(ValueError):
    def __init__(self, message, *, field=None, section=None):
        self.field, self.section = field, section
        super().__init__(message)


def defaults():
    value = {"version": CATALOG["version"], "light": {}, "dark": {}, "values": {}}
    for field in FIELDS:
        for section in ("light", "dark") if field.get("mode") else ("values",):
            value[section][field["key"]] = deepcopy(
                field["default"][section] if field.get("mode") else field["default"])
    return value


def contrast(foreground, background):
    def luminance(color):
        channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [channel / 12.92 if channel <= .04045 else ((channel + .055) / 1.055) ** 2.4
                  for channel in channels]
        return sum(channel * weight for channel, weight in zip(linear, (.2126, .7152, .0722)))
    first, second = luminance(foreground), luminance(background)
    return (max(first, second) + .05) / (min(first, second) + .05)


def _effective_color(value, mode, key):
    seen = set()
    while value[mode][key] is None:
        if key in seen:
            raise DesignValidationError("Rang merosi noto‘g‘ri.")
        seen.add(key)
        key = BY_KEY[key]["inherit"]
    return value[mode][key]


def validate(value):
    """Return a detached normalized snapshot, or reject unsafe/unreadable values."""
    expected = defaults()
    if (type(value) is not dict or set(value) != set(expected)
            or type(value["version"]) is not int or value["version"] != CATALOG["version"]):
        raise DesignValidationError("Ko‘rinish formati mos emas. Sahifani qayta oching.")
    for section in ("light", "dark", "values"):
        if type(value[section]) is not dict or set(value[section]) != set(expected[section]):
            raise DesignValidationError("Ko‘rinish maydonlari mos emas.", section=section)
    # Read only the schema's scalar leaves. Copying the untrusted graph first
    # would recurse through arbitrary nested arrays before we could reject them.
    normalized = expected
    for field in FIELDS:
        key = field["key"]
        for section in ("light", "dark") if field.get("mode") else ("values",):
            item = value[section][key]
            valid = False
            if field["kind"] == "color":
                valid = ((item is None and bool(field.get("inherit")))
                         or (type(item) is str and bool(re.fullmatch(r"#[a-fA-F0-9]{6}", item))))
                if valid and item is not None:
                    item = item.lower()
            elif field["kind"] == "select":
                valid = type(item) is str and item in {option["value"] for option in field["options"]}
            elif field["kind"] == "number":
                valid = item is None
                if (type(item) in (int, float) and field["min"] <= item <= field["max"]
                        and math.isfinite(item)):
                    number = Decimal(str(item))
                    minimum, maximum, step = (Decimal(str(field[name])) for name in ("min", "max", "step"))
                    try:
                        valid = minimum <= number <= maximum and (number - minimum) % step == 0
                    except InvalidOperation:
                        valid = False
                    if valid:
                        item = int(number) if number == number.to_integral_value() else float(number)
            if not valid:
                raise DesignValidationError(f"{field['label']}: qiymat ruxsat etilmagan.", field=key, section=section)
            normalized[section][key] = item
    value = normalized
    for mode in ("light", "dark"):
        for foreground, background, minimum in CATALOG["validation"]["contrastPairs"]:
            if contrast(_effective_color(value, mode, foreground), _effective_color(value, mode, background)) < minimum:
                label = "Yorug‘" if mode == "light" else "Qorong‘i"
                raise DesignValidationError(
                    f"{label} ko‘rinish: {BY_KEY[foreground]['label']} va {BY_KEY[background]['label']} "
                    f"kontrasti kamida {minimum}:1 bo‘lsin.", field=foreground, section=mode)
    sizes = CATALOG["validation"]["typeDefaults"]
    ranges = [sizes[key] if value["values"][key] is None else [value["values"][key]] * 2 for key in sizes]
    if any(previous[1] > following[0] for previous, following in zip(ranges, ranges[1:])):
        raise DesignValidationError("Sarlavha kichik matndan kichik bo‘lmasin. Matn o‘lchamlarini tekshiring.")
    leading = value["values"]["body-leading"]
    if (1.6 if leading is None else leading) < CATALOG["validation"]["bodyLeadingMin"]:
        raise DesignValidationError("Matn satr oralig‘i kamida 1.5 bo‘lsin.", field="body-leading", section="values")
    return value


def _css_number(number):
    return format(Decimal(str(number)).normalize(), "f")


def compile_css(value):
    """Compile only catalog properties; screen scope preserves paper defaults."""
    value = validate(value)
    blocks = []
    for mode in ("light", "dark"):
        properties = []
        for field in FIELDS:
            item = value[mode if field.get("mode") else "values"][field["key"]]
            if item is None:
                continue
            if field["kind"] == "select":
                item = next(option["css"] for option in field["options"] if option["value"] == item)
            elif field["kind"] == "number":
                if field["key"] == "overlay":
                    item = f"rgb(0 0 0 / {_css_number(item)}%)"
                elif field["key"].startswith("text-"):
                    item = f"{_css_number(Decimal(str(item)) / 16)}rem"
                else:
                    item = f"{_css_number(item)}{field['unit']}"
            if item != "":
                properties.append(f"{field['css']}:{item};")
                # Literal-size consumers preserve their own baseline when a
                # typography override is unset; --az-text-* always has defaults.
                if field["kind"] == "number" and field["key"].startswith("text-"):
                    properties.append(f"--dc-{field['key']}:{item};")
        selector = ':root:not([data-theme="dark"])' if mode == "light" else ':root[data-theme="dark"]'
        blocks.append(selector + "{" + "".join(properties) + "}")
    return "@media screen{" + "".join(blocks) + "}"
