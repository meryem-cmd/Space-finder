from django.db import models
from django.contrib.auth.models import User

class Space(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='spaces')
    name = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=255)
    capacity = models.PositiveIntegerField()
    amenities = models.CharField(max_length=500, blank=True)
    image = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name







 
class TimeSlot(models.Model):
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='timeslots')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_booked = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.space} | {self.start_time} - {self.end_time}"





class Booking(models.Model):
    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    timeslot = models.OneToOneField(TimeSlot, on_delete=models.CASCADE, related_name='booking')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.timeslot} ({self.status})"