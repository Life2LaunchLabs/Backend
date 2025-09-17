from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Course(models.Model):
    STATUS_CHOICES = [
        ('locked', 'Locked'),
        ('open', 'Open'),
        ('complete', 'Complete'),
    ]
    
    id = models.CharField(max_length=50, primary_key=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    
    # Chat agenda for course-specific conversations
    agenda = models.TextField(blank=True, null=True, help_text="Markdown formatted agenda for chat conversations")
    
    # Positioning for SVG constellation
    x_position = models.FloatField()
    y_position = models.FloatField()
    
    # Ordering for display
    order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.title
    
    def get_children_ids(self):
        """Return list of child course IDs"""
        return list(self.children.values_list('id', flat=True))

class UserCourseProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=Course.STATUS_CHOICES, default='locked')
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'course']
    
    def __str__(self):
        return f"{self.user.username} - {self.course.title} - {self.status}"
