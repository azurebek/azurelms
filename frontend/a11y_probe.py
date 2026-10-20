"""Ochiq sahifalar uchun statik qulaylik (a11y) tekshiruvi (PUB1.7c).

axe-core'ning *critical/serious* qoidalaridan HTML'ning o'zidan aniqlanadiganlari
— brauzersiz, CI'da har sahifada ishlaydi. Rang kontrasti, fokus ko'rinishi,
zoom/reflow va ekran o'quvchi bu yerda tekshirilmaydi: ular brauzer va qo'lda
tekshiruvda (`nuclear-program/frontend-v1/PUBLIC-A11Y-EVIDENCE.md`).

`probe(html)` → `[Finding(rule, detail), ...]`; bo'sh ro'yxat — topilma yo'q.
"""

import re
from dataclasses import dataclass
from html.parser import HTMLParser

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
FOCUSABLE_TAGS = {"button", "select", "textarea", "summary", "iframe"}
LABELABLE_INPUT_EXCLUDED = {"hidden", "submit", "button", "reset", "image"}


@dataclass(frozen=True)
class Finding:
    rule: str
    detail: str


class _Node:
    __slots__ = ("tag", "attrs", "children", "parent", "text")

    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent = tag, attrs, parent
        self.children, self.text = [], []

    def ancestors(self):
        node = self.parent
        while node is not None:
            yield node
            node = node.parent

    def iter(self):
        yield self
        for child in self.children:
            yield from child.iter()

    def all_text(self):
        parts = list(self.text)
        for child in self.children:
            if child.tag in {"script", "style", "template"}:
                continue
            if child.tag == "img":
                parts.append(child.attrs.get("alt") or "")
            elif child.tag == "svg":
                title = next((n for n in child.iter() if n.tag == "title"), None)
                parts.append(title.all_text() if title else "")
            elif child.attrs.get("aria-hidden") != "true":
                parts.append(child.all_text())
        return " ".join(part for part in parts if part).strip()


class _TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Node("#document", {}, None)
        self.current = self.root

    def handle_starttag(self, tag, attrs):
        node = _Node(tag, {name: (value if value is not None else "") for name, value in attrs}, self.current)
        self.current.children.append(node)
        if tag not in VOID:
            self.current = node

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID and self.current.tag == tag:
            self.current = self.current.parent

    def handle_endtag(self, tag):
        node = self.current
        while node is not None and node.tag != tag:
            node = node.parent
        if node is not None and node.parent is not None:
            self.current = node.parent

    def handle_data(self, data):
        if data.strip():
            self.current.text.append(" ".join(data.split()))


def _is_focusable(node):
    if node.attrs.get("tabindex", "") not in ("", None) and node.attrs.get("tabindex") != "-1":
        return True
    if node.tag == "a" and "href" in node.attrs:
        return True
    if node.tag == "input" and node.attrs.get("type", "text") != "hidden":
        return "disabled" not in node.attrs
    if node.tag in FOCUSABLE_TAGS:
        return "disabled" not in node.attrs
    return False


def _accessible_name(node, labels_for):
    for attr in ("aria-label", "title"):
        if node.attrs.get(attr, "").strip():
            return node.attrs[attr].strip()
    if node.attrs.get("aria-labelledby", "").strip():
        return node.attrs["aria-labelledby"]
    if node.tag in {"input", "select", "textarea"}:
        if node.attrs.get("id") and node.attrs["id"] in labels_for:
            return labels_for[node.attrs["id"]]
        label = next((a for a in node.ancestors() if a.tag == "label"), None)
        if label is not None and label.all_text():
            return label.all_text()
        if node.tag == "input" and node.attrs.get("type") in {"submit", "button", "reset"}:
            return node.attrs.get("value", "").strip()
        return ""
    return node.all_text()


def probe(html):
    builder = _TreeBuilder()
    builder.feed(html)
    nodes = list(builder.root.iter())
    findings = []

    def add(rule, detail):
        findings.append(Finding(rule, detail[:160]))

    html_tag = next((n for n in nodes if n.tag == "html"), None)
    if html_tag is None or not html_tag.attrs.get("lang", "").strip():
        add("html-has-lang", "<html> lang yo'q")
    title = next((n for n in nodes if n.tag == "title"), None)
    if title is None or not title.all_text():
        add("document-title", "<title> bo'sh")
    for meta in (n for n in nodes if n.tag == "meta" and n.attrs.get("name") == "viewport"):
        content = meta.attrs.get("content", "").replace(" ", "").lower()
        scale = re.search(r"maximum-scale=([\d.]+)", content)
        if "user-scalable=no" in content or (scale and float(scale.group(1)) < 2):
            add("meta-viewport", content)

    h1 = [n for n in nodes if n.tag == "h1"]
    if len(h1) != 1:
        add("page-has-heading-one", f"h1 soni: {len(h1)}")
    mains = [n for n in nodes if n.tag == "main" or n.attrs.get("role") == "main"]
    if len(mains) != 1:
        add("landmark-one-main", f"main soni: {len(mains)}")

    ids = {}
    for node in nodes:
        if node.attrs.get("id"):
            ids.setdefault(node.attrs["id"], []).append(node)
    for value, owners in ids.items():
        if len(owners) > 1 and any(_is_focusable(o) or o.tag == "label" for o in owners):
            add("duplicate-id-active", value)
        elif len(owners) > 1:
            add("duplicate-id", value)

    labels_for = {}
    for label in (n for n in nodes if n.tag == "label"):
        target = label.attrs.get("for")
        if target:
            if target not in ids:
                add("label-for-missing", target)
            labels_for[target] = label.all_text()

    for node in nodes:
        for attr in ("aria-labelledby", "aria-describedby", "aria-controls"):
            for ref in node.attrs.get(attr, "").split():
                if ref not in ids:
                    add("aria-valid-ref", f"{node.tag}[{attr}={ref}]")
        tabindex = node.attrs.get("tabindex", "")
        if tabindex.lstrip("-").isdigit() and int(tabindex) > 0:
            add("tabindex", f"{node.tag} tabindex={tabindex}")
        if node.tag == "img" and "alt" not in node.attrs:
            add("image-alt", node.attrs.get("src", "")[:80])
        if node.tag in {"input", "select", "textarea"} and node.attrs.get("type", "").lower() not in LABELABLE_INPUT_EXCLUDED:
            if not _accessible_name(node, labels_for):
                add("label", f"{node.tag}[name={node.attrs.get('name', '')}]")
        if node.tag == "a" and "href" in node.attrs:
            href = node.attrs["href"].strip()
            if not _accessible_name(node, labels_for):
                add("link-name", href[:80])
            if href.lower().startswith("javascript:"):
                add("link-javascript", href[:80])
        if node.tag == "button" and not _accessible_name(node, labels_for):
            add("button-name", str(node.attrs)[:80])
        if node.attrs.get("aria-hidden") == "true":
            hidden_focus = [n for n in node.iter() if n is not node and _is_focusable(n)] + ([node] if _is_focusable(node) else [])
            if hidden_focus:
                add("aria-hidden-focus", f"{node.tag} ichida {hidden_focus[0].tag}")
        if node.tag in {"a", "button"} and _is_focusable(node):
            nested = [n for n in node.iter() if n is not node and n.tag in {"a", "button", "input", "select", "textarea"}]
            if nested:
                add("nested-interactive", f"{node.tag} ichida {nested[0].tag}")
    return findings


def page_forms(html):
    """JavaScriptsiz brauzer ko'radigan formalar: `[{action, method, fields, controls}]`.

    `fields` — yuboriladigan standart qiymatlar (hidden, checked, tanlangan option);
    `controls` — forma ichidagi barcha maydon nomlari.
    """
    builder = _TreeBuilder()
    builder.feed(html)
    forms = []
    for form in (n for n in builder.root.iter() if n.tag == "form"):
        fields, controls = {}, []
        for node in form.iter():
            name = node.attrs.get("name")
            if not name or node.tag not in {"input", "select", "textarea"}:
                continue
            controls.append(name)
            kind = node.attrs.get("type", "text").lower()
            if node.tag == "input" and kind in {"checkbox", "radio"}:
                if "checked" in node.attrs:
                    fields[name] = node.attrs.get("value", "on")
            elif node.tag == "input" and kind not in {"submit", "button", "image", "reset", "file"}:
                fields[name] = node.attrs.get("value", "")
            elif node.tag == "select":
                options = [o for o in node.iter() if o.tag == "option"]
                chosen = next((o for o in options if "selected" in o.attrs), options[0] if options else None)
                if chosen is not None:
                    fields[name] = chosen.attrs.get("value", chosen.all_text())
            elif node.tag == "textarea":
                fields[name] = node.all_text()
        forms.append({"action": form.attrs.get("action", ""), "method": form.attrs.get("method", "get").lower(),
                      "fields": fields, "controls": controls})
    return forms


def missing_fragment_targets(html):
    """`href="#x"` havolalari, sahifada `id="x"` yo'q bo'lsa (o'lik ichki havola)."""
    builder = _TreeBuilder()
    builder.feed(html)
    nodes = list(builder.root.iter())
    ids = {n.attrs["id"] for n in nodes if n.attrs.get("id")}
    return sorted({n.attrs["href"] for n in nodes if n.tag == "a" and n.attrs.get("href", "").startswith("#")
                   and len(n.attrs["href"]) > 1 and n.attrs["href"][1:] not in ids})
