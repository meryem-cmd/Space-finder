# Day 2 Notes — Models, Auth, Serializers, and Start of Viewsets

**Project:** Study Space Finder (Django REST Framework + React)
**Goal of this session:** Build the `Space`, `TimeSlot`, and `Booking` models, set up token authentication, write serializers, and start building the API viewsets.

**Progress at end of session:** Steps 2–6 fully done. Step 7 (viewsets) in progress — `SpaceViewSet` written, URL routing + `TimeSlotViewSet`/`BookingViewSet` still to do.

---

## 1. Big Picture — What Was Built Today

- Created the `spaces` Django app (first real app in the project).
- Built three models: `Space`, `TimeSlot`, `Booking` — with a database-level double-booking safety net.
- Set up DRF Token Authentication (login endpoint returns a token).
- Wrote serializers to convert models ↔ JSON.
- Started building the API layer (`SpaceViewSet`), including automatic ownership assignment.

**Interview one-liner:**
> "I built out the core data models for a booking app — spaces, time slots, and bookings — with a database-level uniqueness constraint to prevent double-booking, then added token-based authentication and started building the DRF API layer using ModelViewSets."

---

## 2. Django App vs Project (recap from Day 1, now applied)

- Ran `python manage.py startapp spaces` to create the first actual Django **app**.
- Registered it in `config/settings.py`'s `INSTALLED_APPS`.
- Everything specific to "spaces" (models, admin, views, serializers) lives inside this one app folder — keeping the project modular.

---

## 3. The Models

### `Space` model
```python
class Space(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='spaces')
    name = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=255)
    capacity = models.PositiveIntegerField()
    amenities = models.CharField(max_length=500, blank=True)
    image = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

**Key design decisions:**
- `location` is a plain `CharField`, not lat/long — no map feature is in the build order, so geocoding would be unnecessary scope creep.
- `image` is a `URLField`, not a real file upload — avoids pulling in `Pillow` + media file config for something that isn't a flagged "hard concept."
- `amenities` is a comma-separated `CharField`, not a separate `Amenity` model with a many-to-many relationship — simpler, and sufficient for this project's scope.
- `owner` is a `ForeignKey` to Django's built-in `User`, added early (in Step 2, not later) because retrofitting a required FK onto a table that already has data is a much bigger migration headache than adding it upfront.

**ForeignKey + `on_delete=models.CASCADE` (interview explanation):**
> A ForeignKey links one model to another — here, each `Space` points to the `User` who owns it, and one user can own many spaces. `on_delete=models.CASCADE` means if that user's account is deleted, all the spaces they own get deleted too, instead of being left orphaned with no owner. The whole related row gets deleted, not just one field on it.

### `TimeSlot` model
```python
class TimeSlot(models.Model):
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='timeslots')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_booked = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.space} | {self.start_time} - {self.end_time}"
```

**Bug caught during practice exercise:** initially had `space = models.ForeignKey(User, ...)` — pointing to the wrong model. A ForeignKey's *first argument* determines what it links to; Django doesn't infer that from the field's name (`space`). Fixed to point at `Space`.

### `Booking` model
```python
class Booking(models.Model):
    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    timeslot = models.OneToOneField(TimeSlot, on_delete=models.CASCADE, related_name='booking')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    created_at = models.DateTimeField(auto_now_add=True)
```

**Why `OneToOneField` instead of `ForeignKey` for `timeslot`:** a regular `ForeignKey` would allow many `Booking` rows to point at the same `TimeSlot` — exactly what we don't want. `OneToOneField` is a `ForeignKey` with a `unique=True` constraint baked in, so at most one `Booking` can ever exist per `TimeSlot`. The database itself rejects a second attempt with an `IntegrityError`.

**STATUS_CHOICES:** restricts `status` to only `'confirmed'` or `'cancelled'` at the database/form level, preventing invalid values like `'banana'` from being saved.

---

## 4. Flagged Hard Concept — Preventing Double-Booking

Two complementary layers, discussed and applied:

1. **Database-level constraint** (`OneToOneField` on `Booking.timeslot`) — the real safety net. Guarantees uniqueness even under concurrent/simultaneous requests (a "race condition"), because the database enforces it, not just application code.
2. **Application-level check** (planned for the viewset in Step 7) — before saving a new booking, explicitly check "is this timeslot already booked?" so the client gets a clean, friendly `400 Bad Request` error instead of a raw `500 IntegrityError`.

**Interview explanation:**
> I used a `OneToOneField` from `Booking` to `TimeSlot` instead of a regular `ForeignKey`. This enforces a unique constraint at the database level, so at most one `Booking` can ever exist for a given `TimeSlot` — the database itself rejects a second attempt, not just application code. This matters because relying only on an application-level check is vulnerable to race conditions, where two near-simultaneous requests could both pass the check before either actually saves. In the view layer, I also plan to add an explicit check so users get a clean error message instead of a raw database error.

---

## 5. Flagged Hard Concept — Authentication (Token-Based)

**Session-based auth (Django default) vs token-based auth — why token was chosen:**
- Session auth relies on server-side sessions + browser cookies. Awkward for a separate React frontend (different origin, CORS/CSRF complications).
- Token auth: login returns a token string; the frontend attaches it to every request's `Authorization` header instead of relying on cookies. Standard pattern for APIs consumed by a separate frontend.

**DRF Token Auth vs JWT — why DRF Token Auth first:**
- DRF Token Auth: simple, one token per user, stored in a DB table, checked on each request via a DB lookup.
- JWT: self-contained, signed token with built-in expiry; no DB lookup needed to validate, but requires access + refresh token handling.
- Decision: start with DRF Token Auth to solidify the core concept (stateless-ish, header-based auth) without JWT's extra moving parts. Planned as a deliberate future upgrade — a good interview story ("started simple, migrated once I understood the tradeoffs").

**Setup steps:**
1. Added `'rest_framework.authtoken'` to `INSTALLED_APPS`.
2. Configured `REST_FRAMEWORK` settings:
   ```python
   REST_FRAMEWORK = {
       'DEFAULT_AUTHENTICATION_CLASSES': [
           'rest_framework.authentication.TokenAuthentication',
           'rest_framework.authentication.SessionAuthentication',
       ],
       'DEFAULT_PERMISSION_CLASSES': [
           'rest_framework.permissions.IsAuthenticated',
       ],
   }
   ```
   (Correction made here: `TokenAuthentication` lives at `rest_framework.authentication`, **not** `rest_framework.authtoken.authentication` — a module path bug that caused a `ModuleNotFoundError` on startup, fixed during this session.)
3. Ran `makemigrations` / `migrate` (authtoken has its own DB table for storing tokens).
4. Added the built-in login view to `config/urls.py`:
   ```python
   from rest_framework.authtoken.views import obtain_auth_token
   path('api/auth/login/', obtain_auth_token, name='api_login'),
   ```
5. Tested via Postman: POST to `/api/auth/login/` with `x-www-form-urlencoded` body (`username`, `password`) → returned `{"token": "..."}"`.

**Interview explanation:**
> Instead of Django's default cookie/session auth, I used DRF's `TokenAuthentication`. On login, the server returns a unique token tied to the user; the frontend stores it and sends it in the `Authorization: Token <key>` header on every subsequent request. This is the standard approach for APIs consumed by a separate frontend, since cookie-based sessions don't play well across different origins. Note: DRF's token prefix is `Token`, not `Bearer` — `Bearer` is the JWT convention, an easy detail to mix up.

**Debugging lesson from today:** a `ModuleNotFoundError` pointing at a *string* referenced inside `settings.py` (not a normal Python `import` line) usually means a config/path typo — the class may exist, just not at the path written. Also: hitting a POST-only endpoint with a browser GET (typing the URL in the address bar) will always 404/fail — auth token endpoints need an actual POST request (via curl or Postman), not a browser visit.

---

## 6. Serializers

**What a serializer does:** translates between Django model objects and JSON — model → JSON for API responses ("serializing"), JSON → model for incoming data ("deserializing").

**`ModelSerializer` vs plain `Serializer`:** chose `ModelSerializer` since it auto-generates fields from the model and provides working `create()`/`update()` methods for free — the right call for straightforward models without unusual validation needs.

```python
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
```

**Key details:**
- `fields = [...]` is an explicit whitelist — safer than `fields = '__all__'`, since new/sensitive model fields won't automatically leak into the API.
- `owner = serializers.ReadOnlyField(source='owner.username')` — without this, `owner` would just serialize as a raw user ID. `source='owner.username'` pulls the related user's username instead. `ReadOnlyField` means it shows in responses but can't be set via incoming POST data.
- Same pattern applied to `user` on `BookingSerializer`.
- `TimeSlotSerializer.space` is left as a raw ID for now (no nested serializer) — kept simple; could nest `SpaceSerializer` later if needed.

---

## 7. Flagged Hard Concept — Ownership Assignment in Viewsets (Step 7, started)

**`ViewSet` + `Router` vs function-based views:** chose `ModelViewSet` — DRF auto-generates the standard CRUD operations (list, create, retrieve, update, delete) from one class, avoiding repetitive boilerplate. Standard pattern for typical CRUD resources like `Space` and `Booking`.

```python
class SpaceViewSet(viewsets.ModelViewSet):
    queryset = Space.objects.all()
    serializer_class = SpaceSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
```

**Key details:**
- `permission_classes = [IsAuthenticatedOrReadOnly]` overrides the global `IsAuthenticated` default — anyone (even logged-out users) can read/browse spaces (`GET`), but must be logged in to create/edit/delete (`POST`/`PUT`/`DELETE`).
- `perform_create` — a hook DRF calls right before saving a new object. Used here to automatically set `owner=self.request.user` (the authenticated user, from their verified token) rather than trusting any `owner` value the client might submit.

**Why the client can't be trusted to submit `owner` directly (interview explanation):**
> If the serializer allowed a client to submit `owner` directly, anyone logged in as one user could include a different user's ID in their request body — effectively assigning ownership of a new space to someone else without their knowledge or consent. This is an ownership-spoofing/impersonation risk. The fix is to ignore any `owner` value from the request body entirely and always derive it server-side from `self.request.user`, which comes from the verified auth token and can't be faked by the client.

---

## 8. Commands Used Today (reference)

```bash
# Create the spaces app
python manage.py startapp spaces

# After adding/editing models
python manage.py makemigrations
python manage.py migrate

# Run dev server
python manage.py runserver

# Create a superuser (for admin panel + testing auth)
python manage.py createsuperuser
```

```bash
# Test the login endpoint (curl alternative to Postman)
curl -X POST http://127.0.0.1:8000/api/auth/login/ -d "username=youruser&password=yourpassword"
```

---

## 9. Things I Should Be Able to Explain Out Loud (self-check)

- [ ] What a ForeignKey is, and what `on_delete=models.CASCADE` does
- [ ] Why `TimeSlot.space` had to point to `Space`, not `User` — and why Django doesn't infer this from field names
- [ ] Why `OneToOneField` (not `ForeignKey`) is used for `Booking.timeslot`, and how it prevents double-booking at the database level
- [ ] Why a database-level constraint is needed in addition to an application-level check (race conditions)
- [ ] The difference between session-based auth and token-based auth, and why token auth suits a React frontend
- [ ] The difference between DRF Token Auth and JWT, and why DRF Token Auth was chosen first
- [ ] What a serializer does, and why `ModelSerializer` was chosen over a plain `Serializer`
- [ ] Why `owner`/`user` fields are `ReadOnlyField` with a `source=` lookup, instead of writable
- [ ] Why the client can't be trusted to submit `owner` directly, and how `perform_create` fixes that
- [ ] What `IsAuthenticatedOrReadOnly` allows vs `IsAuthenticated`

---

## 10. What's Next — Rest of Step 7

- URL routing: hook `SpaceViewSet` up to `/api/spaces/` via a DRF `Router`
- Test creating a `Space` via Postman using the auth token in the `Authorization` header
- Build `TimeSlotViewSet` and `BookingViewSet`
- Add explicit double-booking check in the booking-creation view logic
- Add "cancel booking" and "my bookings" endpoints

Then **Step 8: Permissions** (only space owners can edit their space; only a booking's owner can cancel it) — the last backend step before moving to the React frontend (Step 9 onward).