from rest_framework import serializers
from .models import Course, UserCourseProgress

class CourseSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    user_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'parent', 'x_position', 'y_position', 'order', 'children', 'user_status']
    
    def get_children(self, obj):
        return obj.get_children_ids()
    
    def get_user_status(self, obj):
        """Get user-specific status for this course"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                progress = UserCourseProgress.objects.get(user=request.user, course=obj)
                return progress.status
            except UserCourseProgress.DoesNotExist:
                # Default status logic: intro course is open, others are locked unless parent is complete
                if obj.parent is None:
                    # This is a root/intro course - should be open by default
                    return 'open'
                else:
                    # Check if parent is complete
                    try:
                        parent_progress = UserCourseProgress.objects.get(user=request.user, course=obj.parent)
                        if parent_progress.status == 'complete':
                            return 'open'
                        else:
                            return 'locked'
                    except UserCourseProgress.DoesNotExist:
                        return 'locked'
        return 'locked'

class UserCourseProgressSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    
    class Meta:
        model = UserCourseProgress
        fields = ['user', 'course', 'status', 'completed_at', 'course_title']