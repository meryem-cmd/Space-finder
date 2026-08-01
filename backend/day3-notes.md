# Day 3 Notes — Finishing Viewsets, Nested Routing, and Permissions

**Project:** Study Space Finder (Django REST Framework + React)
**Goal of this session:** Finish Step 7 (URL routing, nested TimeSlot endpoint, full BookingViewSet with double-booking rejection) and complete Step 8 (object-level permissions).

**Progress at end of session:** Backend (Steps 1–8) fully complete and verified.

---

## 1. Big Picture — What Was Built Today

- Wired `SpaceViewSet` up to real URLs using a DRF `Router`.
- Built a **nested** endpoint (`/api/spaces/<id>/timeslots/`) using a custom `@action`, instead of a separate top-level `TimeSlotViewSet` — chosen deliberately for REST-design practice.
- Built the full `BookingViewSet`: create (with double-booking rejection), cancel logic, and a custom `my_bookings` action.
- Added object-level permissions so only a space's owner can edit/delete it, and only a booking's owner can touch it.
- Verified all of this against a second test user, confirming cross-user edits are correctly blocked with `403 Forbidden`.

**Interview one-liner:**
> "I finished the DRF API layer — nested resource routing for time slots, a booking endpoint with database-backed double-booking prevention and clean error handling, and custom object-level permissions so only resource owners can modify their own data."

---

## 2. URL Routing (DRF Router)

**`spaces/urls.py`:**
```python
from rest_framework.routers import DefaultRouter
from .views import SpaceViewSet, BookingViewSet

router = DefaultRouter()
router.register(r'spaces', SpaceViewSet, basename='space')
router.register(r'bookings', BookingViewSet, basename='booking')

urlpatterns = router.urls
```

**`config/urls.py`:**
```python
from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/login/', obtain_auth_token, name='api_login'),
    path('api/', include('spaces.urls')),
]
```

**Key concepts:**
- `router.register(r'spaces', SpaceViewSet, basename='space')` auto-generates all standard CRUD URLs (list/create/retrieve/update/delete) from one line, instead of writing each `path()` manually.
- `include('spaces.urls')` keeps URL config modular — each app owns its own `urls.py`; the root `config/urls.py` just delegates. Combined with the `api/` prefix, `spaces/` becomes `api/spaces/`.

**Verified:** `GET /api/spaces/` works without auth (read-only open); `POST /api/spaces/` with a token correctly auto-assigns `owner` server-side, ignoring any `owner` value the client might send.

---

## 3. Flagged Concept — Nested Routing via Custom `@action`

**Design decision made today:** chose **nested** URLs (`/api/spaces/<id>/timeslots/`) over a simpler top-level `/api/timeslots/?space=1` approach, specifically for REST-design learning value, even though the top-level+filter approach would have been simpler and arguably more broadly reusable (query param filtering comes up again in Step 12).

**Implementation — added to `SpaceViewSet` in `spaces/views.py`:**
```python
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
```

**Key concepts:**
- `@action(detail=True, ...)` adds a custom endpoint scoped to a *specific* object (identified by ID in the URL), as opposed to `detail=False` for list-level actions. Since it's attached to an already-registered viewset, the router auto-generates its URL — no manual `urls.py` changes needed.
- `self.get_object()` fetches the specific `Space` by the ID in the URL, and automatically 404s if it doesn't exist.
- `space.timeslots.all()` — works because of `related_name='timeslots'` set on `TimeSlot.space` back in Step 3, letting you traverse from a `Space` to its related `TimeSlot`s without a manual filter query.
- `serializer.save(space=space)` — same "don't trust the client" pattern as `owner`: the URL already unambiguously identifies the space, so it's injected server-side rather than trusted from the request body.

**Bug caught and fixed during testing:** `TimeSlotSerializer.space` was originally a plain field in `fields = [...]`, so the serializer required it in the POST body — even though we were deliberately not sending it (injecting it server-side instead). Fixed by making it explicitly read-only:
```python
class TimeSlotSerializer(serializers.ModelSerializer):
    space = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = TimeSlot
        fields = ['id', 'space', 'start_time', 'end_time', 'is_booked']
```
`PrimaryKeyRelatedField(read_only=True)` is DRF's proper tool for read-only *relational* fields (serializes as the related object's ID), as opposed to plain `ReadOnlyField`, which is more for simple computed/derived values.

**Verified:** `GET`/`POST` to `/api/spaces/1/timeslots/` correctly scoped to that space; `space` came back correctly in the response without ever being sent by the client.

---

## 4. Flagged Concept — `BookingViewSet` (double-booking rejection, cancel, my_bookings)

```python
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
```

**Key concepts:**
- `permission_classes = [IsAuthenticated, IsBookingOwner]` — unlike `Space`, bookings have no anonymous-read use case, so *every* action requires login.
- `serializer.validated_data['timeslot']` — after DRF validates incoming JSON, the cleaned Python data (not raw JSON) lives in `validated_data`.
- **Double-booking check:** `Booking.objects.filter(timeslot=timeslot, status='confirmed').exists()` — a fast yes/no existence check. If a confirmed booking already exists for the timeslot, raises `serializers.ValidationError`, which DRF turns into a clean `400 Bad Request` with a custom message, instead of letting a raw `IntegrityError` (from the `OneToOneField` constraint) crash through as a `500`.
- **Application-level sync of `is_booked`:** creating/cancelling a `Booking` doesn't automatically update the related `TimeSlot.is_booked` flag — Django doesn't infer that relationship. So `perform_create` sets `is_booked = True` on success, and `perform_update` sets it back to `False` when a booking's status becomes `'cancelled'`. Self-identified this cancel-side logic correctly before being shown the code, based on the symmetry with the create-side logic.
- `@action(detail=False, methods=['get'])` for `my_bookings` — `detail=False` means it's a list-level action, not scoped to one object by ID. Auto-generates `/api/bookings/my_bookings/`.
- `self.get_serializer(...)` — DRF helper returning an already-configured instance of the viewset's `serializer_class`, slightly cleaner than importing/instantiating the serializer directly.

**Interview explanation (double-booking, full version):**
> I used a `OneToOneField` from `Booking` to `TimeSlot` as the database-level safety net — it guarantees at most one booking can exist per timeslot even under race conditions, since the database itself enforces uniqueness. On top of that, in the view layer I added an explicit check before saving: if a confirmed booking already exists for that timeslot, I raise a `ValidationError` that DRF turns into a clean 400 response with a helpful message, rather than letting a raw database IntegrityError surface as an ugly 500 error. Both layers matter — the application check gives good UX, the database constraint is the actual guarantee.

**Verified:**
- `POST /api/bookings/` successfully created a booking.
- Attempting to book the same timeslot again correctly returned a clean `400` with `{"timeslot": "This slot is already booked."}`.
- `GET /api/bookings/my_bookings/` correctly listed only the logged-in user's bookings.

---

## 5. Flagged Concept — Step 8: Object-Level Permissions

**Authentication vs Permission (interview-relevant distinction):**
- **Authentication** = "who are you?" (Step 5 — verifying the token)
- **Permission** = "are you allowed to do *this specific thing*?" (Step 8 — e.g. are you allowed to edit *this particular* space?)
DRF deliberately separates these — you can be authenticated but still not permitted to do something.

**`spaces/permissions.py`** (new file):
```python
from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.owner == request.user


class IsBookingOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user
```

**Wired into the viewsets:**
```python
class SpaceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    ...

class BookingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsBookingOwner]
    ...
```

**Key concepts:**
- `has_object_permission(self, request, view, obj)` — DRF calls this automatically for actions on a *specific* object (retrieve/update/delete). It's a second, more specific layer, running after the more basic `has_permission` check that `IsAuthenticated` uses.
- `permissions.SAFE_METHODS` — DRF's built-in constant for `GET`/`HEAD`/`OPTIONS` (read-only methods). Returning `True` for these means "anyone can view," and the ownership check only applies to write operations.
- `obj.owner == request.user` — the actual ownership check: does the object's owner match the currently logged-in user? If not, DRF returns `403 Forbidden`.
- `IsBookingOwner` has no `SAFE_METHODS` exception, unlike `IsOwnerOrReadOnly` — there's no "anyone can view any booking" use case, so it restricts *all* access to the booking's own user.
- `permission_classes` is a list — DRF requires **all** listed permissions to pass (AND logic), not just one.

**Testing methodology:** created a second test user (`testuser2`) via Django admin, logged in separately to get a second auth token, then attempted a `PATCH` on one of the first user's spaces using `testuser2`'s token.

**Result — confirmed working:**
```json
{"detail": "You do not have permission to perform this action."}
```
Clean `403 Forbidden`, not a crash or silent success — proving `IsOwnerOrReadOnly` correctly blocks cross-user edits.

**Interview explanation:**
> DRF separates authentication ("who are you") from permissions ("are you allowed to do this specific thing"). I wrote custom permission classes using `has_object_permission`, which DRF calls for actions on a specific object. `IsOwnerOrReadOnly` lets anyone read a space, but only its owner can edit or delete it, checked via `obj.owner == request.user`. `IsBookingOwner` similarly restricts booking access to only the user who made it. This is enforced server-side based on the authenticated user's identity — not anything the client could fake in a request.

---

## 6. Backend Complete — Self-Assessment (discussed today)

**Resume value:** Considered strong — a real CRUD API with authentication, relational modeling, and enforced business logic (database-backed double-booking prevention, object-level ownership permissions), not just a tutorial-following CRUD app.

**Concepts demonstrated across the whole backend build:**
- Relational modeling (FK, OneToOne, `related_name`, `CASCADE`)
- Database-level vs application-level constraints, and why both matter (race conditions)
- Token auth vs session auth vs JWT tradeoffs
- Serialization, read-only fields, "never trust the client" pattern (owner/user/space all server-injected)
- ViewSets + routers, nested resource design via custom actions
- Authentication vs authorization as distinct concerns; object-level permissions

**Honest gaps flagged for future improvement:**
- No automated tests yet — everything verified manually via Postman. Worth adding a few `pytest`/Django `TestCase` tests, since "how did you test this" is a likely interview follow-up.
- No pagination on list endpoints yet.
- JWT deferred as a known, deliberate gap (reasoning for the tradeoff is documented in Day 2 notes) — worth mentioning proactively if asked "would you use this in production as-is?"

---

## 7. Things I Should Be Able to Explain Out Loud (self-check)

- [ ] How a DRF `Router` auto-generates URLs from a `ViewSet`, and what `include()` does for modular URL config
- [ ] Why nested routing (`/api/spaces/<id>/timeslots/`) was implemented via a custom `@action` instead of a separate viewset or a third-party package
- [ ] The difference between `detail=True` and `detail=False` on `@action`
- [ ] Why `TimeSlotSerializer.space` had to be made explicitly read-only, and what error appeared before that fix
- [ ] The two layers of double-booking prevention (DB constraint + application check) and why both are needed
- [ ] Why `is_booked` has to be manually synced in `perform_create`/`perform_update`, rather than happening automatically
- [ ] The difference between authentication and permissions
- [ ] How `has_object_permission` and `SAFE_METHODS` work together in `IsOwnerOrReadOnly`
- [ ] Why `permission_classes` as a list means AND logic, not OR

---

## 8. What's Next — Step 9

**Step 9: React frontend — project setup + routing structure** (pages: Browse, Space Detail, My Bookings, Login/Signup). First frontend step; backend (Steps 1–8) is now fully complete and verified.

**Outstanding non-blocking item:** git repo setup — `.gitignore` lives at the project root but `git init` was run inside `backend/`, so it isn't being respected yet (`venv/` and `.env` currently show as untracked/stageable). Needs fixing before the first commit/push to GitHub.