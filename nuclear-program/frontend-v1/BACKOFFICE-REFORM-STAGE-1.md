# Backoffice birinchi bosqich — vazifalar va amallar xaritasi

2026-10-10. [Asosiy reja](BACKOFFICE-REFORM-PLAN.md)ning birinchi bosqichi.
**Tuzilma, manbaga bog‘langan amallar xaritasi va keyingi implementatsiya chegarasi tayyor.**
Bu bosqichda mahsulotning runtime kodi o‘zgarmadi. Owner vaqtli foydalanish sinovi va yangi interfeys qabuli bajarilgan deb hisoblanmaydi.

## Owner bergan yo‘nalish va boshlang‘ich holat

Ustuvorlik: kurs/dars tayyorlash, o‘quvchi muammosini hal qilish, platforma dizaynini texnik bilimsiz moslash.

| Vazifa | Ownerning 2026-10-10 javobi | Dizayn uchun oqibat |
|---|---|---|
| Kurs/dars tayyorlash | «Yo‘lini topishda qiynalaman yoki ishni tugata olmayman» | Kurs ichida ko‘rinadigan tuzilma va izchil qo‘shish/tahrirlash yo‘li kerak |
| Darsga kira olmayotgan o‘quvchiga yordam | «Qayerdan tekshirishni bilmayman» | O‘quvchini topish va kirish sababini ko‘rish bitta kirishga birlashadi |
| Dizaynni moslash | «Sinadim, lekin yordam kerak bo‘ldi» | Oddiy tanlovlar, tushunarli natija va yonida namuna kerak |

Bu **ownerning sifat bo‘yicha boshlang‘ich bahosi**. URL, qurilma va davomiylik o‘lchanmagan; vaqt, klik yoki muvaffaqiyat foizi chiqarilmaydi.
Olti bo‘limni matndan tanlash savollariga owner «bilmadim, tushunmadim o‘zing hal qil» deb javob berdi va professional, texnik bilimsiz ishlatiladigan panelni talab qildi.
Bu javob **0/6 xato yoki navigatsiya qabuli emas**: savol usuli to‘xtatildi. Tuzilma va nomlarni agent hal qiladi; ownerdan kategoriyalarni loyihalash talab qilinmaydi.
Keyingi ko‘rib chiqish aniq ishlaydigan vazifani ko‘rsatish orqali bo‘ladi; reja ishini yangi so‘rovnomaga javob kutish bilan to‘xtatmaymiz.

## Tanlangan tuzilma

Kirishda uch aniq amal: **Dars tayyorlash**, **O‘quvchiga yordam**, **Dizaynni o‘zgartirish**.
Ular menyuni yodlashni talab qilmasdan kerakli ishga olib boradi. Mavjud ma’lumot bo‘lmasa soxta «so‘nggi ish» yoki navbat soni berilmaydi.

| Ko‘rinadigan joy | Ichki yo‘llar | Asosiy natija |
|---|---|---|
| **Ish stoli** | Uch asosiy amal, mavjud ishga qaytish, ta’siri aniq muhim ogohlantirish | Ishni boshlash |
| **Kurslar** | Kurs → Tuzilma → Modul → Dars; Materiallar; Guruhlar; Imtihonlar; Tekshiruv; Davomat | O‘qitish ishlarini kurs kontekstida tugatish |
| **O‘quvchilar** | Qidiruv → O‘quvchi → Kirish / To‘lov / Topshiriq va natija / Mavjud suhbat | Aniq odamning muammosini tushunish |
| **Sayt va dizayn** | Platforma ko‘rinishi; Logo va brend; Sayt sahifalari; Blog; Turkiyada o‘qish | Ko‘rinish va ochiq kontentni boshqarish |
| **To‘lovlar** | Cheklar; Tariflar; mavjud qarorlar tarixi | To‘lov bo‘yicha aniq qaror |
| **Sozlamalar** — menyuning quyi qismida | Xizmatlar; Yoqish/o‘chirish; Muddat va limitlar; AI; Yetkazilmagan xabarlar; mavjud ustoz/admin ro‘yxatiga ruxsatli kirish | Zarur bo‘lganda texnik boshqaruv |

Oldingi umumiy nomlar aniqlashtirildi: Bugun → Ish stoli; Ta’lim → Kurslar; Odamlar → O‘quvchilar; Tizim → Sozlamalar.
Ustoz/admin ro‘yxati yangi akkaunt yaratish yoki rol o‘zgartirish imkoniyati degani emas; mavjud read-only users filtri bilan cheklanadi.
Guruhning yagona muharriri Kurslar ichida; o‘quvchi kartasidan shu a’zolikka kontekstli havola ochiladi. Tarif muharriri To‘lovlarda qoladi.
Platforma ko‘rinishi birinchi ichki kirish bo‘ladi: «Sayt» faqat marketing sahifasi degan taassurot bermasligi kerak.

Kurs ichida tuzilma/muharrir/namuna, o‘quvchida shaxs/muammo/sabab, dizaynda tanlov/jonli namuna ishlatiladi.
Texnik izohlar ishning asosiy qismiga chiqmaydi. Xato va saqlash holati esa ayni amal yonida aniq qoladi.

Professional platformalardan tekshirilgan tayanchlar: [Thinkific course builder](https://support.thinkific.com/hc/en-us/articles/37783573725463-How-to-Add-Content-and-Configure-Your-Course-in-the-New-Course-Builder) modul va darsni kurs ichida yaratish hamda ko‘rinishni birga ko‘rishni ko‘rsatadi.
[Teachable student information](https://support.teachable.com/en/articles/11682531-student-information) shaxsga bog‘langan profilni, [Site boshqaruvi](https://support.teachable.com/en/articles/11682399-site) esa theme/sahifalar/navigatsiya guruhini ko‘rsatadi.
AzureLMS uchun xulosa: vazifalarni shu turdagi tanish joylarga yig‘ish. Ularning permission, pricing yoki biznes qoidalari ko‘chirilmaydi; bu manbalar bizdagi qulaylikning isboti emas.

## Uch ishning boshlanishi va yakuni

| Ish | Hozirgi source bo‘yicha yo‘l | Yangi yo‘lning yakuni | Xato paytidagi talab |
|---|---|---|---|
| Dars tayyorlash | Kurslar → course form; alohida lesson form; library picker; teacher release | Aniq kurs/modul/dars saqlangan; material ko‘rinadi; guruhga ochish ta’siri alohida tekshirilgan | Begona kurs 404; invalid maydon va saqlanmagan matn qoladi; V1 stale 409; javob noma’lum bo‘lsa o‘qib tekshirish |
| O‘quvchi muammosi | Users → teacher students → guruh a’zoligi / chek / release / grading; birlashtirilgan karta yo‘q | Aniq o‘quvchi + kurs + dars uchun haqiqiy sabab; mavjud vakolatli tuzatish joyi; ayni natijani qayta o‘qish | Ma’lumot yetarli bo‘lmasa taxmin yo‘q; begona scope ochilmaydi; boshqa shaxs holati aralashmaydi |
| Dizaynni moslash | Logo/brend va landing real formalar; DESIGN-01 alohida lokal ustaxona | Oddiy tanlov → namuna → doimiy qoralama → aniq nashr → kerak bo‘lsa tarixdan qaytish | Custom qiymat jimgina almashtirilmaydi; kontrast/stale/unknown holati saqlanadi; sessionStorage doimiy saqlash deyilmaydi |

Ownerga ko‘rsatiladigan learner sababi actorning o‘z access natijasi emas, **tanlangan o‘quvchining** canonical policy natijasi bo‘ladi.
O‘qish vakolati alohida tekshiriladi. Active enrollment tanlovi `Enrollment.has_active_access`/`enrollment_active_access_q`ga mos; `courses/access_service.py`dagi bundle funksiyasiga nofaol enrollment berib tashxis chiqarmaymiz.
Course va lesson saqlash hozir view/ModelForm writer; alohida tayyor authoring service bor deb hisoblanmaydi.

## Amal xaritasi

Tayanch: tracked repo **`d05813d`**. `G` — ishlatilayotgan GET yo‘li; bu boshqa methodlar albatta 405 bo‘ladi degani emas.
`P` — POST; action ko‘rsatilmasa oddiy forma submiti. Qisqartirilgan nomlar faqat ushbu texnik jadval uchun.

- **B:** login va staff/superuser — [core/access.py](../../core/access.py):1.
- **S:** B va `teacher_course_queryset`/`teacher_cohort_queryset`; active superuser barcha, qolgan active ustoz biriktirilgan kurslar — shu fayl:9–37.
- **O:** login va active superuser — shu fayl:5; katalogda service orqali ham tekshiriladi.
- **Blog:** login staff/superuser; staff o‘z maqolasi, superuser barchasi — [blog/views.py](../../blog/views.py):20,196–262.

### Kurslar va materiallar

Named URL manbalari: [core/urls.py](../../core/urls.py), [library/backoffice_urls.py](../../library/backoffice_urls.py).
Writerlar: [core/views.py](../../core/views.py):854–1108, [library/backoffice_views.py](../../library/backoffice_views.py):95–437, [library/services.py](../../library/services.py).

| Eski route va amal | Yangi joy | Vakolat va amaldagi writer/read source |
|---|---|---|
| `backoffice_courses` G `q/status/page` | Kurslar → Ro‘yxat | S; scoped queryset va pagination |
| `backoffice_course_create`, `backoffice_course_edit` G/P; oddiy save yoki `save_draft=1` | Kurs → Ma’lumotlar | S; `CourseBackofficeForm`, course.save; draft `is_active=False`; bo‘sh kursga boshlang‘ich Module yaratiladi |
| `backoffice_lessons`, `backoffice_lesson_edit` G/P | Kurs → Tuzilma → Dars | S; `LessonBackofficeForm.save`; V1 ID-siz POST mavjud dars bo‘lsa 409. Odatdagi yangi dars oqimi emas |
| `backoffice_exams`, `backoffice_exam_edit` G/P | Kurslar → Imtihonlar → Sozlamalar | S; Exam va birinchi ExamSection formasi; to‘liq savollar/ko‘p bo‘lim muharriri emas |
| `library_backoffice:resources` G | Kurslar → Materiallar | B; staff uchun umumiy library query |
| `library_backoffice:resource_create`, `library_backoffice:resource_edit` G/P | Material → Yuklash/tahrirlash/faylni almashtirish | B; LibraryResourceForm, `apply_upload`, `sync_tags`, view.save; upload/replacement auditi |
| `library_backoffice:resource_file` G | Material → Fayl | B; `serve_private_file` |
| `library_backoffice:resource_archive` P | Material → Arxivlash yoki tiklash | B; joriy holatga qarab model.archive/restore + audit; action field yo‘q |
| `library_backoffice:resource_delete` P | Material → O‘chirish | B; `delete_resource` + audit; ishlatilayotgan resurs rad etiladi |
| `library_backoffice:lesson_picker` G | Dars → Material tanlash | S; `_editable_lesson` + library read |
| `library_backoffice:material_attach` P `resource`, optional `next/querystring` | Dars → Biriktirish | S; `attach_to_lesson`, duplicate no-op, scoped lock |
| `library_backoffice:material_update` P | Dars → Biriktirma sozlamasi | S; `_locked_material` + LessonMaterialForm.save |
| `library_backoffice:material_detach` P | Dars → Biriktirmani uzish | S; LessonMaterial.delete + audit; library fayli qoladi |
| `library_backoffice:material_reorder` P `order-<id>` | Dars → Materiallar tartibi | S; `reorder_materials` |
| `teacher_courses`, `teacher_cohorts` G | Kurslar → Kurslar/Guruhlar | S; scoped teacher read; teacher kirishi saqlanadi |
| `teacher_release` G/P `action=release/lock` | Kurslar → Guruh → Darslar ruxsati | S; `courses.release_service.set_lesson_release`; ilk explicit release ta’siri va V1 `confirm_impact` saqlanadi |
| `teacher_attendance` G/P `att_<enrollment_id>` | Kurslar → Guruh → Davomat | S; V1 `save_attendance_sheet`; legacy `upsert_attendance_and_xp` |
| `teacher_attendance` legacy P `release_lesson` | Davomatdan guruh darsini ochishga o‘tish | S; to‘liq davomatdan keyin `set_lesson_release`; **V1 attendance bu qo‘shimcha amalni bajarmaydi**, alohida release yo‘li bor |

Teacher dalili: [core/teacher_views.py](../../core/teacher_views.py):139,229,569–756; [core/frontend_v1_attendance.py](../../core/frontend_v1_attendance.py):38–72; [courses/release_service.py](../../courses/release_service.py):41.
V1 editorning actor/action/object revision va confirmation himoyasi saqlanadi; legacy writerlarning barchasiga xuddi shu kafolat berilmaydi.

### O‘quvchi, guruh, to‘lov va tekshiruv

Manbalar: [core/views.py](../../core/views.py):665–849,1128–1209; [subscriptions/backoffice_views.py](../../subscriptions/backoffice_views.py):26–187; [core/teacher_views.py](../../core/teacher_views.py):168–499.

| Eski route va amal | Yangi joy | Vakolat va amaldagi writer/read source |
|---|---|---|
| `backoffice_users` G `q/role/status/page` | O‘quvchilar → Qidiruv; Sozlamalar → Ustoz/admin filtri | B; umumiy users read; mutation yo‘q. Yangi learner karta uchun torroq read projection alohida tekshiriladi |
| `teacher_students` G `q/cohort/page` | O‘quvchilar → Kursdagi o‘quvchilar | S; enrollment/progress/last activity |
| `backoffice_chats` G `q/type/page` | O‘quvchi → Mavjud suhbat | B; room metadata va oxirgi xabar parchasi; qidiruv xabar matniga ham tegadi. Yangi kartada bu read scope/maxfiylik alohida tekshiriladi; xona ichiga kirish vakolatini bermaydi |
| `backoffice_catalog` G | Kurslar → Guruhlar va To‘lovlar → Tariflar | O; Plan/Cohort read; obyektlarning muharriri bittadan |
| `backoffice_cohort_create`, `backoffice_cohort_edit` G/P | Kurslar → Guruh → Sozlamalar | O; `subscriptions.catalog_service.save_cohort` |
| `backoffice_plan_edit` G/P | To‘lovlar → Tarif | O; `subscriptions.catalog_service.update_plan`; Plan+PlanFeature/audit |
| `backoffice_cohort_members` G | Guruh → A’zolar; o‘quvchidan shu a’zolikka havola | O; access/seat/difference read |
| Shu route P `action=difference` | A’zolik → Tarif farqini so‘rash | O web; `membership_service.request_tier_difference` |
| Shu route P `action=transfer` | A’zolik → Boshqa guruhga ko‘chirish | O; `membership_service.transfer_member`; `allow_tier_change` alohida |
| Shu route P `action=release/restore` | A’zolik → Joyni bo‘shatish/qaytarish | O; `membership_service.release_seat/restore_seat` |
| `backoffice_receipts` G/P `action=verify/reject` | To‘lovlar → Cheklar; o‘quvchidan ayni chek havolasi | B; service active staff/owner tekshiradi; `receipt_service.verify_receipt/reject_receipt`, reason/confirm. GET pending+recent10; POST hozir filtrni yo‘qotib rootga qaytadi |
| `teacher_grading` G | Kurslar → Tekshiruv; o‘quvchi → Topshiriq/natija | S; pending assignment/exam read |
| `teacher_grade_assignment` G/P `action=approve/revision` | Aniq topshiriq → Qaror | S; `review_assignment_submission`; XP/audit/notification service ichida |
| `teacher_grade_exam` G/P `action=save/finalize` | Aniq attempt → Baholar/natija | S + completed attempt; view answer/section writes + `ExamAttempt.finalize_review`; V1 finalize faqat saqlangan bahoni oladi |
| `cohorts:receipt_file` G | Chek → Dalil | Active staff/owner yoki chek egasi; private media guard |
| `courses:submission_file`, `courses:exam_answer_audio` G | Topshiriq/imtihon → Dalil | Active egasi yoki course-scoped teacher; private media guard |

Service dalillari: [membership](../../cohorts/membership_service.py), [receipt](../../cohorts/receipt_service.py), [catalog](../../subscriptions/catalog_service.py), [private media](../../core/private_media_views.py):136–229.
Kirish tashxisi manbalari: [lesson access](../../courses/access_service.py):42,124, [exam/result policy](../../courses/policy_service.py):84,100,163, [entitlement](../../core/entitlements.py):82,109.
Birlashtirilgan «hamma ruxsatni yoqish», universal undo/refund yoki impersonation yangi amal sifatida kiritilmaydi.

### Sayt va dizayn

Manbalar: [core/views.py](../../core/views.py):121–155,626–658; [blog/urls.py](../../blog/urls.py), [blog/views.py](../../blog/views.py):196–262; [sit/backoffice_urls.py](../../sit/backoffice_urls.py), [sit/backoffice_views.py](../../sit/backoffice_views.py):129–487.

| Eski route va amal | Yangi joy | Vakolat va amaldagi writer/read source |
|---|---|---|
| `backoffice_brand` G/P, action field yo‘q | Sayt va dizayn → Logo va brend | O; SiteSettings + BrandSettingsForm.save; `brand.update` audit/reason/confirm/no-op; view+form writer |
| `backoffice_landing` G/P | Sayt va dizayn → Sayt sahifalari → Bosh sahifa | O; LandingPageForm.save + `landing.update`; o‘zgarish darhol amalda, versiyali publish emas |
| `blog:studio` G; `blog:studio_create`, `blog:studio_edit` G/P | Sayt va dizayn → Blog | Blog; BlogPostForm → BlogPost/BlogTag; status/published_at. Umumiy SystemAuditEvent/reason/confirm yo‘q |
| `sit_backoffice:dashboard`, `sit_backoffice:universities`, `sit_backoffice:announcements`, `sit_backoffice:guides` G | Sayt va dizayn → Turkiyada o‘qish | O; University/Announcement/KnowledgeArticle read |
| `sit_backoffice:university_create`, `sit_backoffice:university_edit` G/P | Turkiyada o‘qish → Universitet | O; ModelForm va mavjud child formsetlar, atomic save, **Django LogEntry**; reason/confirm/no-op |
| `sit_backoffice:announcement_create`, `sit_backoffice:announcement_edit`, `sit_backoffice:guide_create`, `sit_backoffice:guide_edit` G/P | Turkiyada o‘qish → E’lon/Qo‘llanma | O; ModelForm + LogEntry; barcha SIT editorlarda `save_draft=1` nashrni o‘chiradi; oddiy save formdagi holatni oladi |
| Lokal `design_studio`, `design_frame`, `design_consumer` G | Sayt va dizayn → Platforma ko‘rinishi | Lokal fixture; consumer inert snapshot, real renderer emas |
| Lokal `design_release_read` G; `design_release_command` P `prepare/publish/rollback` | Ko‘rinish → Qoralama/nashr/tarix | Fixture owner, `state.SESSIONS[trial_identity]`; process/session umrida |
| Lokal draft/preset yaratish/tanlash/o‘chirish | Ko‘rinish → Oddiy/Kengaytirilgan | Tab sessionStorage; POST yoki doimiy backend writer emas |

Lokal dalil: `playground/Eleventh Trial/prototype/preview/urls.py:14–18`, `design_release.py:32–172`, `prototype/static/js/design_studio.mjs:11–14,137–153`.
[DC6 holati](DESIGN-01-DC6-ACCEPTANCE.md) o‘zgarmaydi: owner/native qabul PENDING. Brend, landing va design-version bir xil writer deb olinmaydi.

### Sozlamalar

Quyidagi barchasi O. Manba [core/views.py](../../core/views.py):108–620,1212–1277 va [core/urls.py](../../core/urls.py):64–89.

| Eski route va amal | Yangi joy | Amaldagi writer/read source |
|---|---|---|
| `backoffice_control` G | Sozlamalar → Xizmatlar | `build_control_center_snapshot`; read-only |
| `backoffice_feature_flags` G/P `slug/enabled` | Sozlamalar → Yoqish/o‘chirish | `core.flags.set_flag`; FLAG_REGISTRY/FeatureFlag; reason/confirm |
| `backoffice_runtime_settings` G/P `form_name=exam_receipts` | Muddat va limitlar → Imtihon jurnali | OperationalSettings + ExamReceiptSettingsForm |
| Shu route P `form_name=checkout` | Muddat va limitlar → To‘lov tasdiq muddati | OperationalSettings + CheckoutSettingsForm |
| Shu route P `form_name=delivery` | Xabar yetkazish | BotRuntimeSettings + BotDeliverySettingsForm |
| Shu route P `form_name=thresholds/dispatcher` | Kuzatuv chegaralari | OperationalSettings + OperationalThresholdsForm/DispatcherThresholdsForm |
| Shu route P `form_name=reminders` | Eslatmalar | ReminderSettings + ReminderSettingsForm |
| Shu route P `form_name=library` | Material saqlash | LibrarySettings + MaterialLibrarySettingsForm |
| `backoffice_ai_cost` G/P | AI → Sarf va model narxlari | `cost_rollup`; `core.ai_cost.record_price` yangi snapshot + audit, eski narxni tahrirlamaydi |
| `backoffice_ai_kill_switch` P | AI → Tashqi so‘rovlarni to‘xtatish | **AISettings.ai_remote_calls_enabled**, AIKillSwitchForm + audit; hozir FeatureFlag writeri emas |
| `backoffice_ai_circuit_reset` P | AI → Vaqtinchalik himoya | AISupplyState.circuit_open_until=None + audit; asosiy AI kalitini yoqmaydi |
| `backoffice_dead_letter` G/P tanlangan `rows` | Yetkazilmagan xabarlar | `bot.dead_letter.visible_rows/counts/replay` + audit; replay yetkazildi degani emas |
| `backoffice_ai_control` G/P `action=save_settings` | AI → Limitlar | Bevosita AISettings.save; A2-D01 reason/confirm/audit qarzi ochiq |
| Shu route P `action=save_policy` | AI → Tarif limitlari | Bevosita AIPlanPolicy.update_or_create; shu qarz ochiq |
| Shu route P `action=apply_event` | AI → Hisoblagich/bonus | AIUsageResetEvent.save → `aicontrol.service.apply_reset_event`; o‘z event yozuvi, umumiy settings auditi bilan teng emas |

Runtime formalarining umumiy writeri `core/views.py:304–328`: validation, o‘zgargan maydonlargagina save, actor/reason/audit/no-op.
Mavjud kill-switch holati loyiha flag doktrinasiga to‘liq mos deb yozilmaydi; birinchi bosqich uni yashirin migratsiya qilmaydi.
Ish stolidagi eski `backoffice_dashboard` G → yangi xulosa; hozirgi read `_backoffice_context` va dashboard view. Umumiy qidiruv va xulosalar **yangi read imkoniyati** sifatida alohida baholanadi.
«So‘nggi ish» mavjud `updated_at`dan o‘qilsa aynan tahrir vaqtini bildiradi; uni oxirgi tashrif deb atamaymiz. Tashrif/oxirgi ochilgan obyektni doimiy saqlash kerak bo‘lsa bu **yangi persistence/write scope**, read projection emas; birinchi kurs kesimiga yashirin qo‘shilmaydi.

## Mavjud va yangi imkoniyatlar chegarasi

| Imkoniyat | Holat va keyingi ish |
|---|---|
| Course/lesson form, material upload va biriktirish, release, receipt, membership, grading | Mavjud writer/read yo‘llariga ulanadi; action xaritasidagi scope va farqlar saqlanadi |
| Modul create/edit/reorder va odatiy yangi dars | Custom backoffice’da to‘liq emas; ikkinchi bosqichda service/validation/audit shartnomasi kerak |
| O‘quvchi kartasi, course-aware sabab, umumiy qidiruv, Ish stoli xulosasi | Yangi read projection; actor permissioni va target o‘quvchi policy natijasi alohida |
| Barqaror kurs preview, uzilishdan keyin draft/kontekst | Umumiy kafolat hali yo‘q; alohida kontrakt va tegishli sinov |
| Assignment/quiz authoring, barcha exam section/question editor | Legacy admin mavjudligi to‘liq custom backoffice oqimi deb olinmaydi; keyingi paritet inventari |
| Oddiy design mapping | Mavjud typed schema ustida yangi presentation; ikkinchi theme engine emas |
| Doimiy design draft/preset/version, haqiqiy owner auth, consumer/cache | Yangi production port; lokal DESIGN-01 session state bilan yopilmaydi |
| Barcha writerlarda umumiy durable revision/idempotency/audit | Mavjud emas; har writerning haqiqiy himoyasi alohida ko‘rsatiladi |

Bu xarita core backoffice, library, katalog, blog/SIT, o‘quvchi muammosiga bog‘liq teacher va private-file kirishlarini qamraydi.
Classbook, Telegram adapterlari, Django adminning to‘liq CRUDi, chat ichidagi barcha actionlar va vendor upload endpointlari bu bosqichda ko‘chirilmaydi/o‘chirilmaydi.
Ular bilan kesishadigan capability portida dependency xaritasi kengaytiriladi. Hozir «platformadagi barcha actionlar to‘liq inventarlangan» degan da’vo yo‘q.
Eski GET deep linklar saqlanadi; POST ko‘r-ko‘rona redirect qilinmaydi. Yangi joyi, scope va writeri aniqlanmagan actionning eski kirishi olib tashlanmaydi.

## Sakkizta amaliy qabul vazifasi

Vazifalar endi nomma-nom berilgan. Keyingi ishlaydigan versiyani shu vazifalar bilan tekshiramiz; ownerdan hozir ularni matnda hal qilish so‘ralmaydi.
Synthetic kurs/o‘quvchi/material, aniq renderer/flag holati, qurilma va test data qaydi talab qilinadi. Productionda to‘lov yoki kirish qarori sinov uchun o‘zgartirilmaydi.

| ID | Tayyor shart va topshiriq | Yakun dalili |
|---|---|---|
| T1 | Ruxsatli kurs va mavjud dars: nomi berilgan darsni topish | To‘g‘ri kurs/modul/dars ochilgan; maqsad 20 soniya |
| T2 | Test kursi va tayyor matn: modul, keyin yangi dars yaratish | Aniq ota kurs/modul bilan saqlangan dars; noto‘g‘ri dars ustidan yozilmagan |
| T3 | T2 darsi va tayyor fayl: material biriktirish va o‘quvchi namunasini ochish | Biriktirma va ko‘rinish mos; T2+T3 birgalikda 3 daqiqa maqsad, yozish/upload kutishi chiqariladi |
| T4 | Active enrollment, hali ochilmagan aniq dars: kirish sababini aniqlash | To‘g‘ri o‘quvchi/kurs/dars va canonical sabab; maqsad 60 soniya; tuzatishning vakolatli joyi aniq |
| T5 | Pending synthetic chek: ayni o‘quvchining chekini topish va qaror ta’sirini ko‘rish | Shaxs/chek/reason/ta’sir mos; real pul qarori bajarilmaydi |
| T6 | Test design draft: rang, shakl, matnni moslash va oldin/keyin solishtirib saqlash | Oddiy tanlovdan haqiqiy saqlangan qoralama; 3 daqiqa maqsad; custom qiymat yo‘qolmagan |
| T7 | Test muhitida oldingi design version: qoralama/nashrni farqlash, tarixdan qaytish | Qaysi variant amalda ekani va readback aniq; draft tasodifan nashr qilinmagan |
| T8 | Saqlangan dars va saqlanmagan o‘zgarish: boshqa ishga o‘tish, Back/reload | Scope, tanlov, saqlangan ma’lumot saqlanadi; draft saqlangan/saqlanmagan holati rost |

Har bir urinish uchun: muhit, task, yordamsiz/yordamli/bajarilmadi, vaqt (boshlashdan yakun daliligacha), xato yo‘l, qaytish, yordam va izoh yoziladi.
Hozir T1–T8ning **vaqti va amaliy natijasi o‘lchanmagan**. Agent source auditi owner testi o‘rnini bosmaydi.
T2dagi mavjud bo‘lmagan authoring bosqichi «capability yetishmaydi» deb yoziladi, 0 soniya yoki juda uzun vaqt bilan o‘rtachaga kiritilmaydi.
Local design bilan haqiqiy durable port vaqti bir xil mahsulot bazasi deb solishtirilmaydi.
7/8 yordamsiz, kritik xato0 va bir xil bajariladigan vazifalarda 30% median yaxshilanish — taklif etilgan kelajak mezoni; natija da’vosi emas.

## Ikkinchi bosqichga aniq topshiriq

1. Alohida Boshqaruv shell va yuqoridagi nomlar; Ish stolidan uch asosiy vazifaga bevosita kirish. Ruxsatlar serverda qoladi.
2. Kurslar ro‘yxati → bitta kurs tuzilmasi → modul/dars tanlovi → mavjud editor/material. Tanlov, qoralama va qaytish konteksti yo‘qolmaydi.
3. Modul/yangi dars bo‘shlig‘ini minimal kontrakt bilan to‘ldirish: actor/course scope, ota obyekt, validation, saqlash, audit, xato va readback. Yangi yozishdan oldin admission va testlar.
4. Darsni saqlashdan guruhga ochishni aniq ajratish; mavjud release service va ta’sir tasdig‘ini ulash.
5. Bitta kurs oqimi amalda tugaguncha boshqa barcha sahifalarni bir xil qilib qayta bezamaslik. Learner/design workbench keyingi bosqichlarda.

Birinchi bosqich admission: **EXPERIMENT — canonical state yozmaydi**; KPI keyingi vazifani yordamsiz tugatish, yangi operatsion yuk yo‘q.
Schema/DB migration, provider chaqiruvi, deploy va runtime flag o‘zgarishi yo‘q. Qaytish — hujjat/namuna revisioni; real state yozilmagan.
Ownerning tuzilmani agent hal qilishi haqidagi ko‘rsatmasi asosida birinchi bosqichning loyihalash ishlari yakunlanadi. Vaqtli usability va real interfeys qabuli keyingi ishlaydigan versiya uchun ochiq qoladi.
