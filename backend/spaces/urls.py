from rest_framework.routers import DefaultRouter
from .views import SpaceViewSet, BookingViewSet

router = DefaultRouter()
router.register(r'spaces', SpaceViewSet, basename='space')
router.register(r'bookings', BookingViewSet, basename='booking')


urlpatterns = router.urls