from django.urls import path

from . import views


app_name = "classbook"

urlpatterns = [
    path("teacher/", views.teacher_home, name="teacher_home"),
    path("teacher/exercises/", views.exercise_list, name="exercise_list"),
    path("teacher/exercises/new/", views.exercise_edit, name="exercise_create"),
    path("teacher/exercises/<int:exercise_id>/", views.exercise_edit, name="exercise_edit"),
    path("teacher/playbook/<int:cohort_id>/<int:lesson_id>/", views.playbook_edit, name="playbook_edit"),
    path("teacher/playbook/<int:playbook_id>/add/", views.playbook_add_exercise, name="playbook_add_exercise"),
    path("teacher/playbook/step/<int:step_id>/remove/", views.playbook_remove_exercise, name="playbook_remove_exercise"),
    path(
        "teacher/playbook/step/<int:step_id>/<str:direction>/",
        views.playbook_move_exercise,
        name="playbook_move_exercise",
    ),
    path("teacher/session/start/<int:cohort_id>/<int:lesson_id>/", views.session_start, name="session_start"),
    path("teacher/session/<int:session_id>/", views.teacher_session, name="teacher_session"),
    path("teacher/session/<int:session_id>/state/", views.teacher_session_state, name="teacher_session_state"),
    path("teacher/session/<int:session_id>/export/", views.teacher_session_export, name="teacher_session_export"),
    path("teacher/session/<int:session_id>/finish/", views.session_finish, name="session_finish"),
    path("teacher/activity/<int:activity_id>/open/", views.activity_open, name="activity_open"),
    path("teacher/activity/<int:activity_id>/close/", views.activity_close, name="activity_close"),
    path("teacher/activity/<int:activity_id>/results/", views.teacher_activity_result, name="teacher_activity_result"),
    path("teacher/activity/<int:activity_id>/export/", views.teacher_activity_export, name="teacher_activity_export"),
    path("live/", views.live_home, name="live_home"),
    path("live/<int:session_id>/", views.live_session, name="live_session"),
    path("live/<int:session_id>/state/", views.live_session_state, name="live_session_state"),
    path("live/activity/<int:activity_id>/", views.live_activity, name="live_activity"),
    path("live/activity/<int:activity_id>/state/", views.live_activity_state, name="live_activity_state"),
    path("live/activity/<int:activity_id>/submit/", views.live_activity_submit, name="live_activity_submit"),
    path("live/activity/<int:activity_id>/result/", views.activity_result, name="activity_result"),
    path("live/activity/<int:activity_id>/media/", views.activity_media, name="activity_media"),
]
