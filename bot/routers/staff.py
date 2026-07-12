"""O'qituvchi va admin buyruqlari (F4) — shaxsiy chat.

O'qituvchi (teacher/admin): /guruhlarim, /baholash
Admin: /stat, /cheklar (chek rasmi + ✅ Tasdiqlash / ❌ Rad etish tugmalari)
"""

import html

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from asgiref.sync import sync_to_async

from bot.services import (
    admin_stats,
    pending_receipts,
    reject_receipt,
    teacher_cohorts_overview,
    teacher_grading_queue,
    verify_receipt,
)

router = Router(name="staff")
router.message.filter(F.chat.type == "private")

HTML_MODE = "HTML"
STAFF_ROLES = {"teacher", "admin"}


def _fmt_sum(value):
    return f"{value:,}".replace(",", " ")


# ---------------------------------------------------------------- o'qituvchi

@router.message(Command("guruhlarim"))
async def cmd_cohorts(message: types.Message, lms_user, lms_role):
    if lms_role not in STAFF_ROLES:
        await message.answer("Bu buyruq o'qituvchilar uchun.")
        return
    items = await sync_to_async(teacher_cohorts_overview)(lms_user)
    if not items:
        await message.answer("Sizga biriktirilgan faol guruhlar yo'q.")
        return
    lines = ["👥 <b>Guruhlarim</b>\n"]
    for it in items:
        tg = "✈️ Telegram ulangan" if it["tg_bound"] else f"⚠️ Telegram ulanmagan (/link_cohort {it['id']})"
        last = f" · Oxirgi davomat: {it['last_session']}" if it["last_session"] else ""
        lines.append(
            f"▫️ <b>{html.escape(it['name'])}</b> — {html.escape(it['course'])}\n"
            f"   O'quvchilar: {it['students']} · {tg}{last}"
        )
    await message.answer("\n".join(lines), parse_mode=HTML_MODE)


@router.message(Command("baholash"))
async def cmd_grading(message: types.Message, lms_user, lms_role):
    if lms_role not in STAFF_ROLES:
        await message.answer("Bu buyruq o'qituvchilar uchun.")
        return
    queue = await sync_to_async(teacher_grading_queue)(lms_user)
    if not queue["exam_count"] and not queue["assignment_count"]:
        await message.answer("🎉 Baholash navbati bo'sh — hammasi tekshirilgan!")
        return
    lines = ["📝 <b>Baholash navbati</b>\n"]
    if queue["exam_count"]:
        lines.append(f"<b>Imtihonlar ({queue['exam_count']}):</b>")
        for e in queue["exams"]:
            lines.append(f"• {html.escape(e['student'])} — {html.escape(e['title'])}")
        lines.append("")
    if queue["assignment_count"]:
        lines.append(f"<b>Vazifalar ({queue['assignment_count']}):</b>")
        for a in queue["assignments"]:
            lines.append(f"• {html.escape(a['student'])} — {html.escape(a['title'])}")
        lines.append("")
    lines.append("Baholash: saytdagi O'qituvchi paneli → Baholash")
    await message.answer("\n".join(lines), parse_mode=HTML_MODE)


# ---------------------------------------------------------------- admin

@router.message(Command("stat"))
async def cmd_stats(message: types.Message, lms_role):
    if lms_role != "admin":
        await message.answer("Bu buyruq administratorlar uchun.")
        return
    s = await sync_to_async(admin_stats)()
    await message.answer(
        "📊 <b>Platforma holati</b>\n\n"
        f"👤 O'quvchilar: <b>{s['students']}</b>\n"
        f"✅ Faol obunalar: <b>{s['active_enrollments']}</b>\n"
        f"⏳ Kutilayotgan obunalar: <b>{s['pending_enrollments']}</b>\n"
        f"🧾 Tasdiqlanmagan cheklar: <b>{s['unverified_receipts']}</b>"
        + (" — /cheklar" if s["unverified_receipts"] else "")
        + f"\n🤖 Bot mehmonlari: <b>{s['guests']}</b>\n"
        f"📋 Bugungi check-inlar: <b>{s['today_checkins']}</b>",
        parse_mode=HTML_MODE,
    )


def _receipt_markup(receipt_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"adm:rcpt:ok:{receipt_id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"adm:rcpt:no:{receipt_id}"),
            ]
        ]
    )


@router.message(Command("cheklar"))
async def cmd_receipts(message: types.Message, lms_role):
    if lms_role != "admin":
        await message.answer("Bu buyruq administratorlar uchun.")
        return
    items = await sync_to_async(pending_receipts)()
    if not items:
        await message.answer("🎉 Tasdiqlanmagan cheklar yo'q.")
        return
    for it in items:
        caption = (
            f"🧾 <b>Chek №{it['id']}</b> · {it['submitted']}\n"
            f"O'quvchi: <b>{html.escape(it['student'])}</b>\n"
            f"Kurs: {html.escape(it['course'])} · Tarif: {html.escape(it['plan'])}\n"
            f"Summa: <b>{_fmt_sum(it['amount'])} so'm</b>"
        )
        markup = _receipt_markup(it["id"])
        if it["image_path"]:
            try:
                await message.answer_photo(
                    FSInputFile(it["image_path"]),
                    caption=caption,
                    parse_mode=HTML_MODE,
                    reply_markup=markup,
                )
                continue
            except Exception:
                pass  # rasm fayli yo'qolgan bo'lsa matn bilan davom etamiz
        await message.answer(caption, parse_mode=HTML_MODE, reply_markup=markup)


@router.callback_query(F.data.startswith("adm:rcpt:"))
async def cb_receipt_action(callback: types.CallbackQuery, lms_user, lms_role):
    if lms_role != "admin":
        await callback.answer("Ruxsat yo'q.", show_alert=True)
        return
    parts = callback.data.split(":")
    if len(parts) != 4 or not parts[3].isdigit():
        await callback.answer()
        return
    action, receipt_id = parts[2], int(parts[3])
    service = verify_receipt if action == "ok" else reject_receipt
    result = await sync_to_async(service)(receipt_id, lms_user)
    await callback.answer(result.message, show_alert=not result.ok)
    if result.ok and callback.message:
        try:
            base = callback.message.caption or callback.message.text or ""
            new_text = f"{base}\n\n{result.message}"
            if callback.message.caption is not None:
                await callback.message.edit_caption(caption=new_text, reply_markup=None)
            else:
                await callback.message.edit_text(new_text, reply_markup=None)
        except Exception:
            pass
