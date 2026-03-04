"""
WebSocket URL routing for sessions.
"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/students/(?P<student_id>\d+)/$', consumers.StudentEditConsumer.as_asgi()),
    re_path(r'ws/employees/(?P<employee_id>\d+)/$', consumers.EmployeeEditConsumer.as_asgi()),
    re_path(r'ws/sessions/(?P<session_id>\d+)/$', consumers.SessionConsumer.as_asgi()),
]
