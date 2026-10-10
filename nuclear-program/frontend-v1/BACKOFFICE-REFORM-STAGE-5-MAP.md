# Backoffice 5-bosqich — kirish va amal pariteti

2026-10-10. Tayanch `45d94b9`; xarita 5-bosqichning joriy kodiga tegishli.
[Bosqich qaydi](BACKOFFICE-REFORM-STAGE-5.md),
[birinchi action inventari](BACKOFFICE-REFORM-STAGE-1.md).
Bu mahsulotning barcha adapterlari yoki Django admin CRUD xaritasi emas.

## Yangi o‘qish yuzalari

Manbalar: `core/backoffice_sections.py`, `core/backoffice_navigation.py`,
`core/urls.py`, `templates/backoffice/workspace/`.
`backoffice_unified_navigation` default **OFF**. Yangi yuzalar faqat GET;
login, faol staff/owner va flag tekshiriladi. POST — 405, flag OFF — 404.
Javoblar private/no-store; biznes holatini yozadigan yangi xizmat yo‘q.

| Route nomi | URL | O‘qish va ruxsat |
|---|---|---|
| `backoffice_workspace_payments` | `/backoffice/workspace/payments/` | Staff/owner: Cheklar; faqat owner: Tariflar havolasi |
| `backoffice_workspace_site` | `/backoffice/workspace/site/` | Staff: Blog; owner: brend, landing, SIT va design flag ON bo‘lsa Ko‘rinish |
| `backoffice_workspace_settings` | `/backoffice/workspace/settings/` | Owner: xizmat holati, runtime, flags, xabarlar, AI va jamoa yo‘llari |
| `backoffice_workspace_groups` | `/backoffice/workspace/groups/` | `teacher_cohort_queryset(actor)` scope, `with_seat_metrics()`, kurs/tarif join; owner hammasi, ustoz faqat o‘z kurslari |
| `backoffice_workspace_plans` | `/backoffice/workspace/payments/plans/` | Owner: mavjud Plan yozuvlari, `order, pk` tartibi |

Guruh/tarif ro‘yxatlari sahifada **12 tadan** yozuv beradi. Guruh qidiruvi
`q`ni trim qilib 200 belgigacha oladi; nom yoki kurs nomidan qidiradi.
`status=all/active/closed`; active/closed aynan `Cohort.is_active`ga tegishli.
Band joylar canonical model metrikasidan: active va expired joyni egallaydi;
pending/frozen joyni egallamaydi. Kirish ochiqligi bilan band joy teng emas.
Ro‘yxat umumiy checkout yoki o‘quvchi access tashxisi o‘rniga o‘tmaydi.
Takrorlangan GET parametrlar 400; sahifalash Django `Paginator.get_page`
qoidasi bilan ishlaydi. Markazlarda soxta navbat soni/holati chiqarilmaydi.

## Eski action → yangi kirish

Belgilash: **O** — active owner; **B** — mavjud staff/owner kirishi;
**S** — teacher course scope; **Blog** — staff o‘z muallifligidagi postlar,
owner barcha postlar. Jadvaldagi cheklovning haqiqiy authoritysi view/service;
menyuda tugmaning ko‘rinishi ruxsat bermaydi.

| Yangi kirish | Saqlangan aniq route / POST amali | Yagona mavjud writer yoki o‘qish manbasi |
|---|---|---|
| Ish stoli | `backoffice_dashboard`, `backoffice_workspace_home` | Eski dashboard read yoki kurs workspace home; course flag bo‘yicha tanlanadi |
| Kurslar | `backoffice_workspace_courses`, `backoffice_workspace_course_create/edit`, `backoffice_workspace_course` | S; kurs ustaxonasi `courses.authoring_service` va library xizmatlarini iste’mol qiladi; 2-bosqich shartnomasi |
| Kurslar → eski kontent yo‘llari | `backoffice_courses`, `backoffice_course_create/edit`, `backoffice_lessons`, `backoffice_lesson_edit`, `backoffice_exams`, `backoffice_exam_edit` | S; mavjud core form/view va V1 editor himoyalari; URLlar o‘chirilmaydi |
| Kurslar → Materiallar | `library_backoffice:resources`, `resource_create/edit`, `resource_file`, `resource_archive`, `resource_delete` | B; ombor mavjud umumiy staff scope; resource form/xizmat, lifecycle auditi |
| Dars ichidan material | `library_backoffice:lesson_picker`, `material_attach`, `material_reorder`, `material_update`, `material_detach` | S; `library.services`, lesson parent scope; mavjud revision/confirm kontrakti |
| Kurslar → Guruhlar → Sozlamalar | `backoffice_cohort_create`, `backoffice_cohort_edit` | O; `subscriptions.catalog_service.save_cohort`; sabab/tasdiq + audit |
| Kurslar → Guruhlar → A’zolar | `backoffice_cohort_members`; POST `release/restore/difference/transfer` | O; `cohorts.membership_service.release_seat/restore_seat/request_tier_difference/transfer_member` |
| Guruh → Dars ruxsati / Davomat | `teacher_release?cohort=ID`, `teacher_attendance?cohort=ID` | S; mavjud faol-guruh gate, `courses.release_service.set_lesson_release`, canonical attendance/XP xizmati; teacher renderer saqlanadi |
| Kurslar → Tekshiruv | `teacher_grading`, `teacher_grade_assignment`, `teacher_grade_exam` | S; assignment review xizmati / mavjud exam review writer; baho va nashr kontrakti o‘zgarmaydi |
| O‘quvchilar | `backoffice_workspace_students`, `backoffice_workspace_student` | S; 3-bosqich `student_support_service` read tashxisi; flag mustaqil |
| O‘quvchilar → qo‘shimcha ro‘yxatlar | `backoffice_users`, `backoffice_chats` | B; mavjud qidiruv/filter read yuzalari, ularga yangi privacy yoki ticket writer qo‘shilmaydi |
| To‘lovlar → Cheklar | `backoffice_receipts`; POST `verify/reject` | B; `cohorts.receipt_service.verify_receipt/reject_receipt`, active actor, sabab/tasdiq + audit |
| To‘lovlar → Tariflar → Tahrirlash | `backoffice_plan_edit` | O; `subscriptions.catalog_service.update_plan`, sabab/tasdiq + audit; historical payment/access saqlanadi |
| Eski katalog deep linki | `backoffice_catalog` | O; eski qo‘shma tarif/guruh ro‘yxati o‘qiladi; yangi ro‘yxatlar ikkinchi writer emas |
| Sayt va dizayn → Ko‘rinish | `backoffice_design`, `backoffice_design_state`, `backoffice_design_command` | O; 4-bosqich `core.design_service`; own flag, typed draft/preset/version/receipt kontrakti |
| Sayt va dizayn → Logo va brend | `backoffice_brand` | O; `BrandSettingsForm` / SiteSettings, reason/confirm, atomic `brand.update`, no-op |
| Sayt va dizayn → Sayt bosh sahifasi | `backoffice_landing` | O; `LandingPageForm`, `landing.update`; saqlash darhol amalda, design-version nashri emas |
| Sayt va dizayn → Blog | `blog:studio`, `blog:studio_create`, `blog:studio_edit` | Blog; `BlogPostForm`, BlogPost/BlogTag; status/published_at va live-save public redirect saqlanadi |
| Sayt va dizayn → Turkiyada o‘qish | `sit_backoffice:dashboard`, `universities`, `announcements`, `guides` | O; University/Announcement/KnowledgeArticle o‘qish |
| Turkiyada o‘qish → Tahrirlash | `sit_backoffice:university_create/edit`, `announcement_create/edit`, `guide_create/edit`; `save_draft` | O; mavjud ModelForm/child formsetlar, atomic save va Django LogEntry; draft nashr belgisini o‘chiradi |
| Sozlamalar → Platforma holati | `backoffice_control` | O; `build_control_center_snapshot`, read-only |
| Sozlamalar → Yoqish/o‘chirish | `backoffice_feature_flags`; POST `slug/enabled` | O; `core.flags.set_flag`, reason/confirm/audit |
| Sozlamalar → Muddat va limitlar | `backoffice_runtime_settings`; POST `form_name=exam_receipts/checkout/delivery/thresholds/reminders/dispatcher/library` | O; mavjud core runtime forms, OperationalSettings/BotRuntimeSettings/ReminderSettings/LibrarySettings; sabab/tasdiq, changed-field write, audit/no-op |
| Sozlamalar → AI yordamchi | `backoffice_ai_control`; POST `save_settings/save_policy/apply_event` | O; AISettings / AIPlanPolicy mavjud writerlari; reset/bonus `aicontrol.service.apply_reset_event` |
| Sozlamalar → AI sarfi va narxlari | `backoffice_ai_cost` | O; cost rollup read; `core.ai_cost.record_price` yangi narx yozuvi + audit |
| AI → vaqtincha to‘xtatish / qayta urinish | `backoffice_ai_kill_switch`, `backoffice_ai_circuit_reset` | O; mavjud AISettings switch va AISupplyState circuit writerlari; reason/confirm/audit |
| Sozlamalar → Yetkazilmagan xabarlar | `backoffice_dead_letter`; POST tanlangan `rows` | O; `bot.dead_letter.visible_rows/counts/replay`, audit; navbatga qaytarish yetkazildi degani emas |
| Sozlamalar → Jamoa | `backoffice_users?role=teachers`, `backoffice_users?role=admins` | O uchun yangi kirish; eski users read/filter ruxsatlari o‘zgarmaydi, akkaunt writeri yaratilmaydi |

Manbalar: `core/views.py`, `core/teacher_views.py`,
`subscriptions/backoffice_views.py`, `subscriptions/catalog_service.py`,
`library/backoffice_urls.py`, `library/backoffice_views.py`, `blog/views.py`,
`sit/backoffice_urls.py`, `sit/backoffice_views.py`.

## Saqlanadigan kontekst va qaytish

- Plan muvaffaqiyatli saqlansa flag ON’da `backoffice_workspace_plans`ga,
  guruh yaratish/tahrirlash `backoffice_workspace_groups`ga qaytadi;
  OFF’da ikkalasi `backoffice_catalog`ga qaytadi. Xatoli forma redirect qilmaydi.
- Member/receipt focused handoff `enrollment`, `receipt`, `lesson` doirasini
  tekshiradi. Qarordan keyin ayni enrollment/lesson hamda o‘quvchini qayta
  tekshirish yo‘li saqlanadi. Receipt rejection chekni o‘chirganda barqaror
  enrollment konteksti qoladi; yangi ro‘yxat rootiga majburiy yuborilmaydi.
- A’zoni boshqa tarif guruhiga ko‘chirishda `allow_tier_change` alohida
  qoladi. Joyni qaytarish muddati tugagan obunani faol qilib qo‘ymaydi.
- Brend, landing, SIT va boshqa eski formlar ayni URLga POST qiladi;
  field nomlari, formset management data, fayl upload va mavjud audit saqlanadi.
- Blog live-save avvalgi public post manziliga, draft-save editoriga qaytadi.
  Staff boshqa muallif postini tahrirlay olmaydi.

## Renderer, flag va ochiq chegaralar

`backoffice/base.html` faqat admitted route va flag ON bo‘lganda workspace
bridge tanlaydi; OFF’da oldingi `backoffice/legacy_base.html` ishlaydi.
Blog studio alohida bridge’dan foydalanadi; public blog/SIT o‘quvchi sahifalari
bu almashishga kirmaydi. Dizayn/course/student flaglari mustaqil: tegishli
flag OFF bo‘lsa menyu mavjud eski yo‘lga qaytadi yoki yopiq design kirishini
taklif qilmaydi. Yangi navigatsiya ularni yashirin yoqmaydi.

V1 library va course/lesson muharrirlari `frontend_v1/platform.html` qobig‘ida
qoladi; ularda boshqaruvga qaytish havolasi bor. Teacher release, attendance,
grading va chuqur review ham mavjud teacher rendererda qoladi. Ularning
revision, `confirm_scope`, feature-flag va javob/nashr himoyalari saqlanadi.
Classbook, Django adminning barcha CRUDlari, bot/Mini App adapterlari va
assignment/quiz to‘liq authoring bu bosqichda qayta qurilmaydi.

AI settings/policy umumiy reason/confirm/SystemAuditEvent qarzi (A2-D01)
ochiq; blog oddiy kontent writeri, SIT esa Django LogEntry ishlatadi.
Interfeysning yangilanishi barcha writerlar audit/idempotency jihatidan bir
xil bo‘ldi degan da’vo emas. Eski chat/users read siyosati bu kesimda qayta
belgilanmaydi. Qabul, browser/CI dalili va qolgan cheklovlar asosiy
[5-bosqich hisobotida](BACKOFFICE-REFORM-STAGE-5.md) yuritiladi.
