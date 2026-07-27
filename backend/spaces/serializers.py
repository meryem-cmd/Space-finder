from rest_framework import serializers
from .models import Space, TimeSlot, Booking


class SpaceSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')

    class Meta:
        model = Space
        fields = ['id', 'owner', 'name', 'description', 'location', 'capacity', 'amenities', 'image', 'created_at']


class TimeSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeSlot
        fields = ['id', 'space', 'start_time', 'end_time', 'is_booked']


class BookingSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = Booking
        fields = ['id', 'user', 'timeslot', 'status', 'created_at']