from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Course, UserCourseProgress
from .serializers import CourseSerializer, UserCourseProgressSerializer

class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def skill_tree(self, request):
        """Get all courses formatted for the skill tree constellation with user progress"""
        courses = Course.objects.all().prefetch_related('children')
        
        # Get user's course progress
        user_progress = {}
        if request.user.is_authenticated:
            progress_records = UserCourseProgress.objects.filter(user=request.user).select_related('course')
            user_progress = {p.course.id: p for p in progress_records}
        
        # Serialize courses with progress data
        course_data = []
        for course in courses:
            serialized_course = self.get_serializer(course).data
            
            # Add user progress information
            progress = user_progress.get(course.id)
            if progress:
                serialized_course['user_status'] = progress.status
                serialized_course['user_completed_at'] = progress.completed_at.isoformat() if progress.completed_at else None
            else:
                # Default status logic: intro course is open, others are locked unless parent is complete
                if course.parent is None:
                    # This is a root/intro course - should be open by default
                    serialized_course['user_status'] = 'open'
                else:
                    # Check if parent is complete
                    parent_progress = user_progress.get(course.parent.id)
                    if parent_progress and parent_progress.status == 'complete':
                        serialized_course['user_status'] = 'open'
                    else:
                        serialized_course['user_status'] = 'locked'
                serialized_course['user_completed_at'] = None
            
            course_data.append(serialized_course)
        
        return Response(course_data)
    
    @action(detail=True, methods=['post'])
    def update_progress(self, request, pk=None):
        """Update user progress for a specific course"""
        course = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in ['locked', 'open', 'complete']:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        
        progress, created = UserCourseProgress.objects.get_or_create(
            user=request.user,
            course=course,
            defaults={'status': new_status}
        )
        
        if not created:
            progress.status = new_status
            if new_status == 'complete':
                from django.utils import timezone
                progress.completed_at = timezone.now()
            progress.save()
        
        serializer = UserCourseProgressSerializer(progress)
        return Response(serializer.data)
