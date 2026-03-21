from django import forms

from cohorts.models import Cohort
from blog.models import BlogHomeSettings, BlogTag
from courses.models import Assignment, Course, Lesson, Module
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
            "total_xp": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_staff": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_total_xp(self):
        value = self.cleaned_data.get("total_xp")
        return max(value or 0, 0)


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
        fields = ("name", "description", "icon")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "icon": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


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
