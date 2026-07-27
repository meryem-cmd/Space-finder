from django.contrib import admin
from .models import Space, TimeSlot, Booking

admin.site.register(Space)
admin.site.register(TimeSlot)
admin.site.register(Booking)