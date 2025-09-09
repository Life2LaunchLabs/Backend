from django.contrib import admin
from .models import Course, UserCourseProgress

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'parent', 'order', 'x_position', 'y_position']
    list_filter = ['parent']
    search_fields = ['title', 'description']
    ordering = ['order']

@admin.register(UserCourseProgress)
class UserCourseProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'status', 'completed_at']
    list_filter = ['status', 'completed_at']
    search_fields = ['user__username', 'course__title']
