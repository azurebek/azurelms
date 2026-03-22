from django import forms
from django.contrib.auth.models import Group, Permission

from cohorts.models import Cohort, Enrollment
from blog.models import BlogHomeSettings, BlogTag
from courses.models import (
    Assignment,
    Certificate as CourseCertificate,
    Choice,
    Course,
    Exam,
    ExamSection,
    Lesson,
    Module,
    Question,
    Quiz,
)
from frontend.models import (
    AboutPage,
    AboutStatistic,
    AuthPageSettings,
    LandingNavItem,
    LandingPage,
    LegalPage,
    SiteSettings,
    Statistic,
    TeamMember,
    Testimonial,
)
from gamification.models import Badge, Certificate as GamificationCertificate, Level
from messenger.models import ChatRoom, Message
from subscriptions.models import Plan, PlanFeature
from users.models import CustomUser, NotificationBroadcast


class BackofficeUserUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "telegram_id",
            "telegram_username",
            "bio",
            "avatar",
            "total_xp",
            "is_active",
            "is_staff",
        )
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "telegram_id": forms.NumberInput(attrs={"class": "form-control"}),
            "telegram_username": forms.TextInput(attrs={"class": "form-control"}),
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "avatar": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "total_xp": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_staff": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_total_xp(self):
        value = self.cleaned_data.get("total_xp")
        return max(value or 0, 0)


class BackofficeUserAccessForm(forms.ModelForm):
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": "7"}),
    )
    user_permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.order_by("content_type__app_label", "codename"),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": "10"}),
    )

    class Meta:
        model = CustomUser
        fields = ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")
        widgets = {
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_staff": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_superuser": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class BackofficeBroadcastForm(forms.ModelForm):
    recipients = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.filter(is_active=True).order_by("username"),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": "6"}),
    )
    cohorts = forms.ModelMultipleChoiceField(
        queryset=Cohort.objects.select_related("course").filter(is_active=True).order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": "6"}),
    )

    class Meta:
        model = NotificationBroadcast
        fields = ("title", "message", "icon", "url", "target_type", "recipients", "cohorts")
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Masalan: Platforma yangilandi"}),
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Bildirishnoma matni"}),
            "icon": forms.TextInput(attrs={"class": "form-control", "placeholder": "megaphone"}),
            "url": forms.TextInput(attrs={"class": "form-control", "placeholder": "/users/dashboard/"}),
            "target_type": forms.Select(attrs={"class": "form-select", "id": "id_target_type"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        target_type = cleaned_data.get("target_type")
        recipients = cleaned_data.get("recipients")
        cohorts = cleaned_data.get("cohorts")

        if target_type == NotificationBroadcast.TARGET_USERS and not recipients:
            self.add_error("recipients", "Tanlangan foydalanuvchilar ro'yxati bo'sh bo'lmasligi kerak.")
        if target_type == NotificationBroadcast.TARGET_COHORTS and not cohorts:
            self.add_error("cohorts", "Tanlangan cohortlar ro'yxati bo'sh bo'lmasligi kerak.")
        return cleaned_data


class BackofficePlanForm(forms.ModelForm):
    class Meta:
        model = Plan
        fields = ("name", "price", "description", "is_popular", "button_text", "order")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "price": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "is_popular": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "button_text": forms.TextInput(attrs={"class": "form-control"}),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
        }


class BackofficePlanFeatureForm(forms.ModelForm):
    class Meta:
        model = PlanFeature
        fields = ("name", "is_included", "order")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Masalan: Barcha darslarga kirish"}),
            "is_included": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
        }


class BackofficeSiteSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = (
            "company_description",
            "contact_phone",
            "contact_email",
            "contact_address",
            "support_url",
            "payment_card_number",
            "payment_card_holder",
            "payment_provider_label",
            "payment_instruction",
            "telegram_url",
            "instagram_url",
            "youtube_url",
            "facebook_url",
        )
        widgets = {
            "company_description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "contact_phone": forms.TextInput(attrs={"class": "form-control"}),
            "contact_email": forms.EmailInput(attrs={"class": "form-control"}),
            "contact_address": forms.TextInput(attrs={"class": "form-control"}),
            "support_url": forms.URLInput(attrs={"class": "form-control"}),
            "payment_card_number": forms.TextInput(attrs={"class": "form-control"}),
            "payment_card_holder": forms.TextInput(attrs={"class": "form-control"}),
            "payment_provider_label": forms.TextInput(attrs={"class": "form-control"}),
            "payment_instruction": forms.TextInput(attrs={"class": "form-control"}),
            "telegram_url": forms.URLInput(attrs={"class": "form-control"}),
            "instagram_url": forms.URLInput(attrs={"class": "form-control"}),
            "youtube_url": forms.URLInput(attrs={"class": "form-control"}),
            "facebook_url": forms.URLInput(attrs={"class": "form-control"}),
        }


class BackofficeAuthPageSettingsForm(forms.ModelForm):
    class Meta:
        model = AuthPageSettings
        fields = (
            "meta_description",
            "topbar_back_label",
            "help_prompt",
            "help_link_label",
            "login_visual_kicker",
            "login_visual_title",
            "login_visual_description",
            "login_panel_badge",
            "login_panel_heading",
            "login_panel_intro",
            "login_footer_prompt",
            "login_footer_link_label",
            "register_visual_kicker",
            "register_visual_title",
            "register_visual_description",
            "register_panel_badge",
            "register_panel_heading",
            "register_panel_intro",
            "register_footer_prompt",
            "register_footer_link_label",
        )
        widgets = {
            "meta_description": forms.TextInput(attrs={"class": "form-control"}),
            "topbar_back_label": forms.TextInput(attrs={"class": "form-control"}),
            "help_prompt": forms.TextInput(attrs={"class": "form-control"}),
            "help_link_label": forms.TextInput(attrs={"class": "form-control"}),
            "login_visual_kicker": forms.TextInput(attrs={"class": "form-control"}),
            "login_visual_title": forms.TextInput(attrs={"class": "form-control"}),
            "login_visual_description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "login_panel_badge": forms.TextInput(attrs={"class": "form-control"}),
            "login_panel_heading": forms.TextInput(attrs={"class": "form-control"}),
            "login_panel_intro": forms.TextInput(attrs={"class": "form-control"}),
            "login_footer_prompt": forms.TextInput(attrs={"class": "form-control"}),
            "login_footer_link_label": forms.TextInput(attrs={"class": "form-control"}),
            "register_visual_kicker": forms.TextInput(attrs={"class": "form-control"}),
            "register_visual_title": forms.TextInput(attrs={"class": "form-control"}),
            "register_visual_description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "register_panel_badge": forms.TextInput(attrs={"class": "form-control"}),
            "register_panel_heading": forms.TextInput(attrs={"class": "form-control"}),
            "register_panel_intro": forms.TextInput(attrs={"class": "form-control"}),
            "register_footer_prompt": forms.TextInput(attrs={"class": "form-control"}),
            "register_footer_link_label": forms.TextInput(attrs={"class": "form-control"}),
        }


class BackofficeLegalPageForm(forms.ModelForm):
    class Meta:
        model = LegalPage
        fields = ("title", "content")
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 12}),
        }


class BackofficeLandingPageForm(forms.ModelForm):
    class Meta:
        model = LandingPage
        fields = (
            "hero_badge",
            "hero_title_start",
            "hero_title_highlight",
            "hero_title_end",
            "hero_subtitle",
            "hero_background_image",
            "hero_background_video",
            "hero_image",
            "hero_video",
            "how_it_works_background_image",
            "how_it_works_background_video",
            "footer_background_image",
            "footer_background_video",
            "cta_title",
            "cta_description",
        )
        widgets = {
            "hero_badge": forms.TextInput(attrs={"class": "form-control"}),
            "hero_title_start": forms.TextInput(attrs={"class": "form-control"}),
            "hero_title_highlight": forms.TextInput(attrs={"class": "form-control"}),
            "hero_title_end": forms.TextInput(attrs={"class": "form-control"}),
            "hero_subtitle": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "hero_background_image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "hero_background_video": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "hero_image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "hero_video": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "how_it_works_background_image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "how_it_works_background_video": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "footer_background_image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "footer_background_video": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "cta_title": forms.TextInput(attrs={"class": "form-control"}),
            "cta_description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }


class BackofficeStatisticForm(forms.ModelForm):
    class Meta:
        model = Statistic
        fields = ("value", "label", "order")
        widgets = {
            "value": forms.TextInput(attrs={"class": "form-control"}),
            "label": forms.TextInput(attrs={"class": "form-control"}),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
        }


class BackofficeTestimonialForm(forms.ModelForm):
    class Meta:
        model = Testimonial
        fields = ("name", "role", "text", "rating", "avatar", "is_active")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "role": forms.TextInput(attrs={"class": "form-control"}),
            "text": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "rating": forms.NumberInput(attrs={"class": "form-control", "min": "1", "max": "5"}),
            "avatar": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class BackofficeAboutPageForm(forms.ModelForm):
    class Meta:
        model = AboutPage
        fields = (
            "hero_title_start",
            "hero_title_highlight",
            "hero_subtitle",
            "mission_title",
            "mission_text",
            "vision_title",
            "vision_text",
        )
        widgets = {
            "hero_title_start": forms.TextInput(attrs={"class": "form-control"}),
            "hero_title_highlight": forms.TextInput(attrs={"class": "form-control"}),
            "hero_subtitle": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "mission_title": forms.TextInput(attrs={"class": "form-control"}),
            "mission_text": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "vision_title": forms.TextInput(attrs={"class": "form-control"}),
            "vision_text": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }


class BackofficeAboutStatisticForm(forms.ModelForm):
    class Meta:
        model = AboutStatistic
        fields = ("value", "label", "order")
        widgets = {
            "value": forms.TextInput(attrs={"class": "form-control"}),
            "label": forms.TextInput(attrs={"class": "form-control"}),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
        }


class BackofficeTeamMemberForm(forms.ModelForm):
    class Meta:
        model = TeamMember
        fields = ("name", "role_1", "role_2", "bio", "avatar", "order")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "role_1": forms.TextInput(attrs={"class": "form-control"}),
            "role_2": forms.TextInput(attrs={"class": "form-control"}),
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "avatar": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
        }


class BackofficeLandingNavItemForm(forms.ModelForm):
    class Meta:
        model = LandingNavItem
        fields = ("label", "is_visible", "order")
        widgets = {
            "label": forms.TextInput(attrs={"class": "form-control"}),
            "is_visible": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
        }


class BackofficeBlogHomeSettingsForm(forms.ModelForm):
    class Meta:
        model = BlogHomeSettings
        fields = (
            "hero_kicker",
            "hero_title",
            "hero_description",
            "search_label",
            "search_placeholder",
            "carousel_kicker",
            "carousel_title",
            "stories_kicker",
            "stories_title",
            "stories_description",
        )
        widgets = {
            "hero_kicker": forms.TextInput(attrs={"class": "form-control"}),
            "hero_title": forms.TextInput(attrs={"class": "form-control"}),
            "hero_description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "search_label": forms.TextInput(attrs={"class": "form-control"}),
            "search_placeholder": forms.TextInput(attrs={"class": "form-control"}),
            "carousel_kicker": forms.TextInput(attrs={"class": "form-control"}),
            "carousel_title": forms.TextInput(attrs={"class": "form-control"}),
            "stories_kicker": forms.TextInput(attrs={"class": "form-control"}),
            "stories_title": forms.TextInput(attrs={"class": "form-control"}),
            "stories_description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class BackofficeBlogTagForm(forms.ModelForm):
    class Meta:
        model = BlogTag
        fields = ("name", "slug")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "slug": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["slug"].required = False


class BackofficeChatRoomForm(forms.ModelForm):
    participants = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.filter(is_active=True).order_by("username"),
        required=True,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": "7"}),
    )

    class Meta:
        model = ChatRoom
        fields = ("room_type", "name", "cohort", "participants")
        widgets = {
            "room_type": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "cohort": forms.Select(attrs={"class": "form-select"}),
        }

    def save(self, commit=True):
        participants = self.cleaned_data.pop("participants", [])
        room = super().save(commit=commit)
        if commit:
            room.participants.set(participants)
        return room


class BackofficeMessageCreateForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ("sender", "text", "is_ai_response", "context_lesson")
        widgets = {
            "sender": forms.Select(attrs={"class": "form-select"}),
            "text": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "is_ai_response": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "context_lesson": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        room = kwargs.pop("room", None)
        super().__init__(*args, **kwargs)
        self.fields["sender"].required = False
        self.fields["context_lesson"].required = False
        self.fields["sender"].queryset = CustomUser.objects.filter(is_active=True).order_by("username")
        if room and room.cohort_id:
            self.fields["context_lesson"].queryset = Lesson.objects.filter(module__course=room.cohort.course).order_by(
                "module__order",
                "order",
            )
        else:
            self.fields["context_lesson"].queryset = Lesson.objects.order_by("-id")

    def clean(self):
        cleaned_data = super().clean()
        sender = cleaned_data.get("sender")
        is_ai_response = cleaned_data.get("is_ai_response")
        if not is_ai_response and not sender:
            self.add_error("sender", "AI javobi bo'lmasa yuboruvchi tanlanishi kerak.")
        return cleaned_data


class BackofficeLevelForm(forms.ModelForm):
    class Meta:
        model = Level
        fields = ("name", "min_xp", "badge_image")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "min_xp": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "badge_image": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class BackofficeBadgeForm(forms.ModelForm):
    class Meta:
        model = Badge
        fields = ("name", "description", "icon_source", "google_icon_name", "google_icon_style", "icon")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "icon_source": forms.Select(attrs={"class": "form-select"}),
            "google_icon_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "workspace_premium"}
            ),
            "google_icon_style": forms.Select(attrs={"class": "form-select"}),
            "icon": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["icon_source"].required = False
        self.fields["google_icon_style"].required = False
        self.fields["icon_source"].initial = getattr(
            self.instance,
            "icon_source",
            Badge.ICON_SOURCE_UPLOAD,
        ) or Badge.ICON_SOURCE_UPLOAD
        self.fields["google_icon_style"].initial = getattr(
            self.instance,
            "google_icon_style",
            Badge.GOOGLE_STYLE_OUTLINED,
        ) or Badge.GOOGLE_STYLE_OUTLINED

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("icon_source"):
            cleaned_data["icon_source"] = (
                getattr(self.instance, "icon_source", Badge.ICON_SOURCE_UPLOAD)
                or Badge.ICON_SOURCE_UPLOAD
            )
        if not cleaned_data.get("google_icon_style"):
            cleaned_data["google_icon_style"] = (
                getattr(self.instance, "google_icon_style", Badge.GOOGLE_STYLE_OUTLINED)
                or Badge.GOOGLE_STYLE_OUTLINED
            )
        return cleaned_data


class BackofficeAwardBadgeForm(forms.Form):
    TARGET_USERS = "users"
    TARGET_COHORT = "cohort"
    TARGET_CHOICES = (
        (TARGET_USERS, "Tanlangan foydalanuvchilarga"),
        (TARGET_COHORT, "Tanlangan cohortdagi aktiv userlarga"),
    )

    badge = forms.ModelChoiceField(
        queryset=Badge.objects.order_by("name"),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    target_type = forms.ChoiceField(
        choices=TARGET_CHOICES,
        initial=TARGET_USERS,
        widget=forms.Select(attrs={"class": "form-select", "id": "id_award_target_type"}),
    )
    students = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.filter(is_active=True, is_staff=False, is_superuser=False).order_by("username"),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": "7", "id": "id_award_students"}),
    )
    cohort = forms.ModelChoiceField(
        queryset=Cohort.objects.filter(is_active=True).select_related("course").order_by("name"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select", "id": "id_award_cohort"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        target_type = cleaned_data.get("target_type")
        students = cleaned_data.get("students")
        cohort = cleaned_data.get("cohort")

        if target_type == self.TARGET_USERS and not students:
            self.add_error("students", "Kamida bitta foydalanuvchini tanlang.")
        if target_type == self.TARGET_COHORT and not cohort:
            self.add_error("cohort", "Cohort tanlang.")
        return cleaned_data


class BackofficeGamificationCertificateForm(forms.ModelForm):
    class Meta:
        model = GamificationCertificate
        fields = ("student", "course", "file")
        widgets = {
            "student": forms.Select(attrs={"class": "form-select"}),
            "course": forms.Select(attrs={"class": "form-select"}),
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["student"].queryset = CustomUser.objects.filter(is_active=True).order_by("username")
        self.fields["course"].queryset = Course.objects.filter(is_active=True).order_by("title")


class BackofficeCourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = (
            "title",
            "description",
            "instructor",
            "level",
            "duration",
            "price",
            "cover_mode",
            "gradient_preset",
            "gradient_cover_title",
            "gradient_cover_label",
            "thumbnail",
            "preview_video",
            "is_active",
        )
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "instructor": forms.Select(attrs={"class": "form-select"}),
            "level": forms.Select(attrs={"class": "form-select"}),
            "duration": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "price": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "cover_mode": forms.Select(attrs={"class": "form-select"}),
            "gradient_preset": forms.Select(attrs={"class": "form-select"}),
            "gradient_cover_title": forms.TextInput(attrs={"class": "form-control"}),
            "gradient_cover_label": forms.TextInput(attrs={"class": "form-control"}),
            "thumbnail": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "preview_video": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["instructor"].queryset = CustomUser.objects.filter(is_active=True).order_by("username")


class BackofficeExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ("course", "title", "exam_type", "weight_percentage", "passing_score")
        widgets = {
            "course": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "exam_type": forms.Select(attrs={"class": "form-select"}),
            "weight_percentage": forms.NumberInput(attrs={"class": "form-control", "min": "0", "max": "100"}),
            "passing_score": forms.NumberInput(attrs={"class": "form-control", "min": "0", "max": "100"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["course"].queryset = Course.objects.order_by("title")


class BackofficeExamSectionForm(forms.ModelForm):
    class Meta:
        model = ExamSection
        fields = (
            "exam",
            "title",
            "section_type",
            "instructions",
            "reading_text",
            "media_url",
            "max_score",
            "time_limit_minutes",
            "order",
        )
        widgets = {
            "exam": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "section_type": forms.Select(attrs={"class": "form-select"}),
            "media_url": forms.URLInput(attrs={"class": "form-control"}),
            "max_score": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "time_limit_minutes": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["exam"].queryset = Exam.objects.select_related("course").order_by("course__title", "title")


class BackofficeQuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ("title", "lesson", "exam_section", "xp_reward")
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "lesson": forms.Select(attrs={"class": "form-select"}),
            "exam_section": forms.Select(attrs={"class": "form-select"}),
            "xp_reward": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["lesson"].required = False
        self.fields["exam_section"].required = False
        self.fields["lesson"].queryset = Lesson.objects.select_related("module__course").order_by(
            "module__course__title",
            "module__order",
            "order",
        )
        self.fields["exam_section"].queryset = ExamSection.objects.select_related("exam", "exam__course").order_by(
            "exam__course__title",
            "exam__title",
            "order",
        )

    def clean(self):
        cleaned_data = super().clean()
        lesson = cleaned_data.get("lesson")
        exam_section = cleaned_data.get("exam_section")
        if bool(lesson) == bool(exam_section):
            raise forms.ValidationError("Quiz faqat bitta kontekstga birikadi: lesson yoki exam section.")
        return cleaned_data


class BackofficeQuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ("quiz", "exam_section", "text", "points")
        widgets = {
            "quiz": forms.Select(attrs={"class": "form-select"}),
            "exam_section": forms.Select(attrs={"class": "form-select"}),
            "points": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["quiz"].required = False
        self.fields["exam_section"].required = False
        self.fields["quiz"].queryset = Quiz.objects.select_related("lesson", "exam_section").order_by("title")
        self.fields["exam_section"].queryset = ExamSection.objects.select_related("exam", "exam__course").order_by(
            "exam__course__title",
            "exam__title",
            "order",
        )

    def clean(self):
        cleaned_data = super().clean()
        quiz = cleaned_data.get("quiz")
        exam_section = cleaned_data.get("exam_section")
        if bool(quiz) == bool(exam_section):
            raise forms.ValidationError("Savol faqat bitta joyga bog'lanadi: quiz yoki exam section.")
        return cleaned_data


class BackofficeChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ("question", "text", "is_correct")
        widgets = {
            "question": forms.Select(attrs={"class": "form-select"}),
            "text": forms.TextInput(attrs={"class": "form-control"}),
            "is_correct": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["question"].queryset = Question.objects.select_related("quiz", "exam_section").order_by("-id")


class BackofficeCourseCertificateForm(forms.ModelForm):
    class Meta:
        model = CourseCertificate
        fields = ("student", "course", "certificate_id", "final_score")
        widgets = {
            "student": forms.Select(attrs={"class": "form-select"}),
            "course": forms.Select(attrs={"class": "form-select"}),
            "certificate_id": forms.TextInput(attrs={"class": "form-control"}),
            "final_score": forms.NumberInput(attrs={"class": "form-control", "min": "0", "max": "100"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["student"].queryset = CustomUser.objects.filter(is_active=True).order_by("username")
        self.fields["course"].queryset = Course.objects.order_by("title")


class BackofficeModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ("title", "order")
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
        }


class BackofficeLessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ("title", "video_url", "content", "order", "xp_reward")
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "video_url": forms.URLInput(attrs={"class": "form-control"}),
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "xp_reward": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
        }


class BackofficeAssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ("title", "description", "max_xp")
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "max_xp": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
        }


class BackofficeCohortForm(forms.ModelForm):
    class Meta:
        model = Cohort
        fields = ("name", "course", "start_date", "telegram_group_link", "is_active")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "course": forms.Select(attrs={"class": "form-select"}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "telegram_group_link": forms.URLInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["course"].queryset = Course.objects.order_by("title")


class BackofficeEnrollmentCreateForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ("student", "plan", "status", "last_payment_date", "next_payment_deadline")
        widgets = {
            "student": forms.Select(attrs={"class": "form-select"}),
            "plan": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "last_payment_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "next_payment_deadline": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["student"].queryset = (
            CustomUser.objects.filter(is_active=True, is_staff=False, is_superuser=False).order_by("username")
        )
        self.fields["plan"].queryset = Plan.objects.order_by("order", "id")
        self.fields["plan"].required = False
        self.fields["last_payment_date"].required = False
        self.fields["next_payment_deadline"].required = False
