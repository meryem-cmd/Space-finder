from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from .models import Space, TimeSlot, Booking
from .serializers import SpaceSerializer, TimeSlotSerializer, BookingSerializer
from .permissions import IsOwnerOrReadOnly, IsBookingOwner


class SpaceViewSet(viewsets.ModelViewSet):
    queryset = Space.objects.all()
    serializer_class = SpaceSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['get', 'post'])
    def timeslots(self, request, pk=None):
        space = self.get_object()

        if request.method == 'GET':
            slots = space.timeslots.all()
            serializer = TimeSlotSerializer(slots, many=True)
            return Response(serializer.data)

        elif request.method == 'POST':
            serializer = TimeSlotSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(space=space)
            return Response(serializer.data, status=status.HTTP_201_CREATED)


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated, IsBookingOwner]


    def perform_create(self, serializer):
        timeslot = serializer.validated_data['timeslot']

        if Booking.objects.filter(timeslot=timeslot, status='confirmed').exists():
            raise serializers.ValidationError({'timeslot': 'This slot is already booked.'})

        serializer.save(user=self.request.user)
        timeslot.is_booked = True
        timeslot.save()

    def perform_update(self, serializer):
        booking = serializer.save()
        if booking.status == 'cancelled':
            booking.timeslot.is_booked = False
            booking.timeslot.save()

    @action(detail=False, methods=['get'])
    def my_bookings(self, request):
        bookings = Booking.objects.filter(user=request.user)
        serializer = self.get_serializer(bookings, many=True)
        return Response(serializer.data)