import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Camera, CheckCircle2, Flame } from "lucide-react";
import { HOUSEHOLD_CATEGORIES, UNITS, WIZARD_STEPS } from "../../constants/donations";
import { Button } from "../../components/ui/Button";
import { Input, Select, Textarea } from "../../components/ui/Field";
import { ChoiceChips } from "../../components/ui/ChoiceChips";
import { FoodChecks, rowsFor } from "../../components/food/FoodChecks";
import { CategoryTiles } from "../../components/ui/CategoryTiles";
import { ProgressIndicator } from "../../components/ui/States";
import { LocationPicker, type ConfirmedLocation } from "../../components/map/LocationPicker";
import { createDonation, uploadDonationPhoto } from "../../services/donations";
import { recommendDestinations, type DestinationOption } from "../../services/destinations";
import { analyzeFoodPhoto, type PhotoCheck } from "../../services/photoCheck";
import { readApiError } from "../../services/auth";
import { DonationCategory, UserRole, type Donation } from "../../types/models";
import { donationDetailPath, homePath } from "../../constants/roles";
import { useAuth } from "../../providers/AuthProvider";
import { clearDonateDraft, peekDonateDraft, saveDonateDraft } from "./donateDraft";

const GOODS_QUALITY = [
  { key: "clean_usable", title: "Clean and usable" },
  { key: "appropriately_packed", title: "Packed to move" },
] as const;

const SOURCE_OPTIONS = [
  { value: "HOME", label: "Home" },
  { value: "RESTAURANT", label: "Restaurant" },
  { value: "WEDDING", label: "Wedding" },
  { value: "EVENT", label: "Event" },
  { value: "OFFICE", label: "Office" },
  { value: "HOSTEL", label: "Hostel" },
  { value: "OTHER", label: "Other" },
] as const;

const TIMING_OPTIONS = [
  { value: "ASAP", label: "ASAP" },
  { value: "TODAY_EVENING", label: "Today evening" },
  { value: "TOMORROW_MORNING", label: "Tomorrow morning" },
  { value: "CUSTOM", label: "Custom" },
] as const;

const PICKUP_SLOTS = [
  { value: "MORNING", label: "Morning", start: "08:00", end: "12:00" },
  { value: "AFTERNOON", label: "Afternoon", start: "12:00", end: "17:00" },
  { value: "EVENING", label: "Evening", start: "17:00", end: "20:00" },
] as const;

function todayInIst() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(new Date());
}

function slotBounds(date: string, slot: (typeof PICKUP_SLOTS)[number]) {
  return {
    start: new Date(`${date}T${slot.start}:00+05:30`),
    end: new Date(`${date}T${slot.end}:00+05:30`),
  };
}

function canContinueLocation(location: ConfirmedLocation) {
  const address = location.address.trim();
  const point = location.point;
  const hasPoint =
    point != null &&
    Number.isFinite(point.lat) &&
    Number.isFinite(point.lng) &&
    !(point.lat === 0 && point.lng === 0);
  if (!location.confirmed) return false;
  return Boolean(address || hasPoint);
}

function newIdempotencyKey() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `donate-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function Donate() {
  const { user } = useAuth();
  const [params] = useSearchParams();
  const initial = (params.get("category") as DonationCategory | null) || null;
  const validInitial = HOUSEHOLD_CATEGORIES.some((item) => item.id === initial) ? initial : null;
  const navigate = useNavigate();
  const saved = user ? peekDonateDraft(user.id) : null;

  const [step, setStep] = useState(saved?.step ?? (validInitial ? 1 : 0));
  const [category, setCategory] = useState<DonationCategory | null>(saved?.category ?? validInitial);
  const [quantity, setQuantity] = useState(saved?.quantity ?? "5");
  const [unit, setUnit] = useState(saved?.unit ?? UNITS[(saved?.category ?? validInitial) || DonationCategory.FOOD][0]);
  const [notes, setNotes] = useState(saved?.notes ?? "");
  const [householdScale, setHouseholdScale] = useState<"COOKED_LEFTOVERS" | "DRY_RATIONS" | "PRIVATE_FUNCTION">(
    saved?.householdScale ?? "DRY_RATIONS",
  );
  const [catererName, setCatererName] = useState(saved?.catererName ?? "");
  const [photoCheck, setPhotoCheck] = useState<PhotoCheck | null>(null);
  const [checkingPhoto, setCheckingPhoto] = useState(false);
  const [foodSource, setFoodSource] = useState<(typeof SOURCE_OPTIONS)[number]["value"]>(
    (saved?.foodSource as (typeof SOURCE_OPTIONS)[number]["value"]) || "HOME",
  );
  const [packaging, setPackaging] = useState<"PACKED" | "UNPACKED">(saved?.packaging ?? "PACKED");
  const [timing, setTiming] = useState<(typeof TIMING_OPTIONS)[number]["value"]>(
    (saved?.timing as (typeof TIMING_OPTIONS)[number]["value"]) || "ASAP",
  );
  const [customPickup, setCustomPickup] = useState(saved?.customPickup ?? "");
  const [condition, setCondition] = useState<"GOOD" | "FAIR">(saved?.condition ?? "GOOD");
  const [pickupDate, setPickupDate] = useState(saved?.pickupDate ?? "");
  const [pickupSlot, setPickupSlot] = useState<(typeof PICKUP_SLOTS)[number]["value"] | "">(
    (saved?.pickupSlot as (typeof PICKUP_SLOTS)[number]["value"]) || "",
  );
  const [checks, setChecks] = useState<Record<string, string>>(saved?.checks ?? {});
  const [photos, setPhotos] = useState<File[]>(saved?.photos ?? []);
  const [previews, setPreviews] = useState<string[]>(saved?.previews ?? []);
  const [missing, setMissing] = useState<string[]>([]);
  const missingRef = useRef<HTMLDivElement>(null);
  const [location, setLocation] = useState<ConfirmedLocation>(
    saved?.location ?? {
      address: "",
      point: null,
      approximate: false,
      confirmed: false,
    },
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState<Donation | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);
  const [idempotencyKey] = useState(newIdempotencyKey);
  const [nearby, setNearby] = useState<DestinationOption[]>([]);
  const [nearbyNote, setNearbyNote] = useState("");
  const [preferredCentreId, setPreferredCentreId] = useState("");

  useEffect(() => {
    if (!user || submitted) return;
    saveDonateDraft({
      userId: user.id,
      step,
      category,
      quantity,
      unit,
      notes,
      householdScale,
      catererName,
      foodSource,
      packaging,
      timing,
      customPickup,
      condition,
      pickupDate,
      pickupSlot,
      checks,
      location,
      photos,
      previews,
    });
  }, [
    user,
    submitted,
    step,
    category,
    quantity,
    unit,
    notes,
    householdScale,
    catererName,
    foodSource,
    packaging,
    timing,
    customPickup,
    condition,
    pickupDate,
    pickupSlot,
    checks,
    location,
    photos,
    previews,
  ]);

  useEffect(() => {
    if (step !== 3 || !category || !location.point) {
      return;
    }
    let cancelled = false;
    recommendDestinations(location.point.lat, location.point.lng, category, 3)
      .then((row) => {
        if (cancelled) return;
        setNearby(row.options);
        setNearbyNote(
          row.options.length
            ? row.note
            : "No facility with saved coordinates is eligible for this category in the current directory.",
        );
      })
      .catch(() => {
        if (!cancelled) setNearbyNote("Nearby facilities could not be loaded.");
      });
    return () => {
      cancelled = true;
    };
  }, [step, category, location.point?.lat, location.point?.lng]);

  const units = useMemo(() => (category ? UNITS[category] : []), [category]);
  const isFood = category === DonationCategory.FOOD;
  const cookedBlocked = isFood && householdScale === "COOKED_LEFTOVERS";
  const foodRows = isFood ? rowsFor("donor", householdScale) : [];
  const checklistOk = isFood
    ? foodRows.every((row) => Boolean(checks[row.key])) && checks.freshly_prepared !== "NO" && checks.covered !== "NO" && checks.stored_safely !== "NO" && checks.time_since_cooking !== "OVER_4H"
    : GOODS_QUALITY.every((item) => checks[item.key] === "YES");

  const autoDescription = useMemo(() => {
    if (!category) return "";
    if (isFood) {
      return [
        "Food",
        foodSource.toLowerCase().replace("_", " "),
        packaging === "PACKED" ? "packed" : "unpacked",
        householdScale === "PRIVATE_FUNCTION" ? "private function" : householdScale === "DRY_RATIONS" ? "dry rations" : "cooked leftovers",
        timing.replace("_", " ").toLowerCase(),
      ].join(" · ");
    }
    const slot = PICKUP_SLOTS.find((item) => item.value === pickupSlot);
    const when = pickupDate && slot ? `${pickupDate} ${slot.label.toLowerCase()}` : "scheduled pickup";
    return `${category.toLowerCase()} · ${condition.toLowerCase()} · ${when}`;
  }, [category, isFood, foodSource, packaging, householdScale, timing, condition, pickupDate, pickupSlot]);

  function choose(next: DonationCategory) {
    setCategory(next);
    setUnit(UNITS[next][0]);
    setChecks({});
    setPhotoCheck(null);
    setStep(1);
  }

  function setChecksNext(next: Record<string, string>) {
    setChecks(next);
    if (next.packaging === "PACKED" || next.packaging === "UNPACKED") {
      setPackaging(next.packaging);
    }
  }

  function problemsOnThisStep() {
    const gaps: string[] = [];
    if (step === 1) {
      if (!quantity || Number(quantity) <= 0) gaps.push("Enter a quantity.");
      if (cookedBlocked) gaps.push("Cooked leftovers cannot be accepted. Choose sealed dry rations or a private function.");
      if (isFood && householdScale === "PRIVATE_FUNCTION" && catererName.trim().length < 2) {
        gaps.push("Enter the catering service or cloud kitchen name.");
      }
      if (isFood && timing === "CUSTOM" && !customPickup.trim()) gaps.push("Enter a custom pickup time.");
      if (isFood) {
        for (const row of foodRows) {
          if (!checks[row.key]) gaps.push(`Answer “${row.label.replace("?", "")}”.`);
        }
        if (checks.freshly_prepared === "NO" || checks.covered === "NO" || checks.stored_safely === "NO") {
          gaps.push("A No on a food check means this food cannot be shared.");
        }
        if (checks.time_since_cooking === "OVER_4H") gaps.push("Food cooked more than 4 hours ago cannot be shared.");
      } else if (!checklistOk) {
        gaps.push("Answer the condition checks.");
      }
      if (!isFood) {
        const slot = PICKUP_SLOTS.find((item) => item.value === pickupSlot);
        if (!pickupDate || !slot) {
          gaps.push("Choose a future pickup date and time window.");
        } else if (!(slotBounds(pickupDate, slot).start.getTime() > Date.now())) {
          gaps.push("That pickup window is in the past. Choose a later one.");
        }
      }
      if (photoCheck?.blocked) gaps.push(photoCheck.guidance);
    }
    if (step === 2 && !canContinueLocation(location)) {
      gaps.push("Confirm the pickup pin before continuing.");
    }
    return gaps;
  }

  function goNext(next: number) {
    const gaps = problemsOnThisStep();
    if (gaps.length) {
      setMissing(gaps);
      window.requestAnimationFrame(() => missingRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
      return;
    }
    setMissing([]);
    setStep(next);
  }

  async function onPhotos(files: FileList | null) {
    const file = files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    setPhotos((current) => [...current, file]);
    setPreviews((current) => [...current, url]);
    if (!isFood) return;
    setCheckingPhoto(true);
    try {
      setPhotoCheck(await analyzeFoodPhoto(file));
    } finally {
      setCheckingPhoto(false);
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!category || !checklistOk || !canContinueLocation(location)) return;
    if (!isFood && (!pickupDate || !pickupSlot)) {
      setMissing(["Choose a future pickup date and time window."]);
      return;
    }
    setBusy(true);
    setError("");
    try {
      const urgency = timing === "ASAP" ? "HIGH" : "NORMAL";
      const source = householdScale === "PRIVATE_FUNCTION" || foodSource === "WEDDING" ? "FUNCTION_HALL" : foodSource;
      const slot = PICKUP_SLOTS.find((item) => item.value === pickupSlot);
      const scheduled = !isFood && pickupDate && slot ? slotBounds(pickupDate, slot) : null;
      if (!isFood && !scheduled) return;
      const created = await createDonation({
        category,
        quantity: Number(quantity),
        unit,
        description: autoDescription,
        notes: [notes, timing === "CUSTOM" && customPickup.trim() ? `Pickup: ${customPickup.trim()}` : ""]
          .filter(Boolean)
          .join("\n") || undefined,
        condition: isFood ? undefined : condition,
        pickup_address: location.address || undefined,
        pickup_latitude: location.point?.lat,
        pickup_longitude: location.point?.lng,
        pickup_pincode: location.pincode || undefined,
        location_accuracy_m:
          location.source === "device" && location.point?.accuracy != null
            ? Math.round(location.point.accuracy)
            : undefined,
        location_source:
          location.source === "device"
            ? "DEVICE_GEOLOCATION"
            : location.source === "search"
              ? "OSM_SEARCH"
              : location.source === "map"
                ? "MANUAL_PIN"
                : "MANUAL_ADDRESS",
        location_provider: location.provider,
        mappls_pin: location.mappls_pin || undefined,
        geocode_precision: location.precision || undefined,
        location_captured_at: location.source === "device" ? location.point?.capturedAt : undefined,
        location_confirmed_at: new Date().toISOString(),
        pickup_landmark: location.landmark?.trim() || undefined,
        food_source: isFood ? source : undefined,
        diet_type: isFood ? householdScale : undefined,
        packaging_state: isFood ? packaging : undefined,
        urgency: isFood ? urgency : "SCHEDULED",
        pickup_deadline: scheduled ? scheduled.end.toISOString() : undefined,
        quality_checklist: isFood
          ? checks
          : Object.fromEntries(GOODS_QUALITY.map((item) => [item.key, checks[item.key] === "YES"])),
        idempotency_key: idempotencyKey,
        preferred_centre_id: preferredCentreId || undefined,
        cluster_window: scheduled
          ? `${pickupDate} ${slot?.label} ${slot?.start}–${slot?.end} IST`
          : timing === "CUSTOM"
            ? "CUSTOM"
            : timing,
        commercial: scheduled
          ? {
              pickup_window_start: scheduled.start.toISOString(),
              pickup_window_end: scheduled.end.toISOString(),
            }
          : isFood && householdScale === "PRIVATE_FUNCTION"
            ? {
                event_type: catererName.trim(),
                packaging_state: packaging,
              }
            : undefined,
      });
      for (const file of photos) {
        await uploadDonationPhoto(created.id, file);
      }
      clearDonateDraft();
      setSubmitted(created);
      setShowSuccess(true);
      setStep(4);
    } catch (err) {
      setError(readApiError(err));
    } finally {
      setBusy(false);
    }
  }

  if (step === 4 && submitted && showSuccess) {
    return (
      <section className="wizard-panel success-overlay page-enter" role="status" aria-live="polite">
        <div className="success-burst" aria-hidden>
          <CheckCircle2 size={56} />
        </div>
        <p className="eyebrow">Submitted</p>
        <h1>Your donation has been submitted</h1>
        <p className="muted">
          Reference <strong>{submitted.reference_code}</strong>. Eligible volunteers may get a short timed offer.
          This is not yet collected or delivered.
        </p>
        <dl className="review">
          <div>
            <dt>What</dt>
            <dd>{autoDescription}</dd>
          </div>
          <div>
            <dt>Quantity</dt>
            <dd>
              {submitted.quantity} {submitted.unit}
            </dd>
          </div>
          <div>
            <dt>Pickup</dt>
            <dd>{submitted.pickup_address || "Confirmed pin"}</dd>
          </div>
          <div>
            <dt>Status</dt>
            <dd>{submitted.status_label}</dd>
          </div>
        </dl>
        <div className="row-actions" style={{ justifyContent: "center" }}>
          <Button
            type="button"
            onClick={() => navigate(donationDetailPath(user?.role || UserRole.DONOR, submitted.id))}
          >
            View donation
          </Button>
          <Link to={homePath(user?.role || UserRole.DONOR)} className="btn btn-secondary">
            {user?.role === UserRole.VOLUNTEER ? "My pickups" : "Dashboard"}
          </Link>
        </div>
      </section>
    );
  }

  return (
    <form className="wizard-panel donate-mcq" onSubmit={onSubmit}>
      <div ref={missingRef}>
        {missing.length ? (
          <div className="missing-banner" role="alert">
            <strong>Still needed</strong>
            <ul>
              {missing.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
      <p className="eyebrow">Donate</p>
      <h1>What, where, and when.</h1>
      <ProgressIndicator steps={WIZARD_STEPS} current={Math.min(step, 3)} />

      {step === 0 ? (
        <section className="page-enter">
          <h2>What are you giving?</h2>
          <p className="muted" style={{ margin: "8px 0 18px" }}>
            Tap one. Food is prioritised. Books, clothes and toys use scheduled pickups.
          </p>
          <CategoryTiles selected={category} onSelect={choose} />
        </section>
      ) : null}

      {step === 1 && category ? (
        <section className="page-enter details-split">
          <div className="details-col stack">
            <h2>{isFood ? "Food details" : "Item details"}</h2>
            <p className="muted">Quantity, source, and when it can be picked up.</p>
            <div className="split">
              <Input
                label={isFood ? "Quantity / portions" : "Quantity"}
                type="number"
                min="0.1"
                step="0.1"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                required
              />
              <Select label="Unit" value={unit} onChange={(e) => setUnit(e.target.value)}>
                {units.map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </Select>
            </div>

            {isFood ? (
              <>
                <div className="gate-card">
                  <p className="gate-title">Standard leftovers or a private home function for 25+?</p>
                  <ChoiceChips
                    label="Household scale"
                    value={householdScale}
                    onChange={setHouseholdScale}
                    columns={3}
                    options={[
                      { value: "COOKED_LEFTOVERS", label: "Cooked leftovers" },
                      { value: "DRY_RATIONS", label: "Sealed dry rations" },
                      { value: "PRIVATE_FUNCTION", label: "Private function (25+)" },
                    ]}
                  />
                </div>
                <ChoiceChips
                  label="Where is this food from?"
                  value={foodSource}
                  onChange={setFoodSource}
                  columns={4}
                  required
                  options={[...SOURCE_OPTIONS]}
                />
                <ChoiceChips
                  label="When should we pick up?"
                  value={timing}
                  onChange={setTiming}
                  columns={4}
                  required
                  options={[...TIMING_OPTIONS]}
                />
                {timing === "CUSTOM" ? (
                  <Input
                    label="Custom pickup time"
                    value={customPickup}
                    onChange={(e) => setCustomPickup(e.target.value)}
                    placeholder="Day and time"
                    required
                  />
                ) : null}
                {cookedBlocked ? (
                  <p className="field-error">
                    Cooked leftovers cannot be accepted. Offer sealed dry rations such as rice or dal, or a private catered function for 25 or more people.
                  </p>
                ) : null}
                {householdScale === "PRIVATE_FUNCTION" ? (
                  <Input
                    label="Catering service or cloud kitchen"
                    value={catererName}
                    onChange={(e) => setCatererName(e.target.value)}
                    required
                  />
                ) : null}
              </>
            ) : (
              <>
                <ChoiceChips
                  label="Condition"
                  value={condition}
                  onChange={setCondition}
                  columns={2}
                  required
                  options={[
                    { value: "GOOD", label: "Good" },
                    { value: "FAIR", label: "Fair but usable" },
                  ]}
                />
                <Input
                  label="Pickup date"
                  type="date"
                  min={todayInIst()}
                  value={pickupDate}
                  onChange={(e) => setPickupDate(e.target.value)}
                  required
                />
                <ChoiceChips
                  label="Pickup time window"
                  value={pickupSlot}
                  onChange={setPickupSlot}
                  columns={3}
                  required
                  options={PICKUP_SLOTS.map((item) => ({
                    value: item.value,
                    label: `${item.label} ${item.start}–${item.end}`,
                  }))}
                />
                <p className="field-hint">Books, clothes, toys, and miscellaneous items are scheduled pickups. ASAP is not available.</p>
              </>
            )}
          </div>

          <aside className="quality-panel stack">
            {isFood ? (
              <FoodChecks role="donor" handling={householdScale} value={checks} onChange={setChecksNext} />
            ) : (
              GOODS_QUALITY.map((item) => (
                <ChoiceChips
                  key={item.key}
                  label={item.title}
                  value={checks[item.key]}
                  onChange={(v) => setChecks((prev) => ({ ...prev, [item.key]: v }))}
                  columns={2}
                  options={[
                    { value: "YES", label: "Yes" },
                    { value: "NO", label: "No" },
                  ]}
                />
              ))
            )}
            <p className="field-hint">These answers are a declaration, not proof the food is safe. Not sure is kept as unsure.</p>

            {photoCheck ? <p className={photoCheck.blocked ? "field-error" : "field-hint"}>{photoCheck.guidance}</p> : null}
            {checkingPhoto ? <p className="muted">Checking the photo…</p> : null}
            {previews.length ? (
              <div className="photo-previews">
                {previews.map((src) => (
                  <img key={src} src={src} alt="Donation photo" />
                ))}
              </div>
            ) : null}
            <label className="btn btn-secondary file-chip">
              <Camera size={16} aria-hidden />
              Take photo
              <input
                type="file"
                accept="image/*"
                capture="environment"
                hidden
                onChange={(e) => {
                  void onPhotos(e.target.files);
                  e.target.value = "";
                }}
              />
            </label>
            <Textarea
              label="Notes for volunteers"
              optional
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Gate code, floor, contact tip…"
            />
          </aside>

          <div className="row-actions details-actions">
            <Button type="button" variant="secondary" onClick={() => setStep(0)}>
              Back
            </Button>
            <Button type="button" onClick={() => goNext(2)}>
              Continue
            </Button>
          </div>
        </section>
      ) : null}

      {step === 2 ? (
        <section className="stack page-enter">
          <h2>Pickup location</h2>
          <p className="muted">Use GPS, enter a PIN, or drag the house pin. Confirm the real pickup point.</p>
          <LocationPicker value={location} onChange={setLocation} height={420} layout="pickup" />
          {error ? <p className="field-error">{error}</p> : null}
          <div className="row-actions">
            <Button type="button" variant="secondary" onClick={() => setStep(1)}>
              Back
            </Button>
            <Button type="button" onClick={() => goNext(3)}>
              Continue
            </Button>
          </div>
        </section>
      ) : null}

      {step === 3 && category ? (
        <section className="stack page-enter">
          <h2>Review</h2>
          <p className="muted">Tap Back to change a choice. Submit only when this looks right.</p>
          <dl className="review chip-review">
            <div>
              <dt>Summary</dt>
              <dd>{autoDescription}</dd>
            </div>
            <div>
              <dt>Quantity</dt>
              <dd>
                {quantity} {unit}
              </dd>
            </div>
            <div>
              <dt>Pickup</dt>
              <dd>{location.address || "Confirmed map pin"}</dd>
            </div>
            {location.landmark ? (
              <div>
                <dt>Landmark</dt>
                <dd>{location.landmark}</dd>
              </div>
            ) : null}
            {isFood && timing === "ASAP" ? (
              <div>
                <dt>Priority</dt>
                <dd>
                  <Flame size={14} aria-hidden /> Food · ASAP
                  {foodSource === "WEDDING" || householdScale === "PRIVATE_FUNCTION" ? " · function / wedding boost" : ""}
                </dd>
              </div>
            ) : null}
            {!isFood && pickupDate && pickupSlot ? (
              <div>
                <dt>Pickup schedule</dt>
                <dd>
                  {pickupDate} · {PICKUP_SLOTS.find((item) => item.value === pickupSlot)?.label}{" "}
                  {PICKUP_SLOTS.find((item) => item.value === pickupSlot)?.start}–
                  {PICKUP_SLOTS.find((item) => item.value === pickupSlot)?.end} IST
                </dd>
              </div>
            ) : null}
          </dl>
          <section className="stack">
            <h3>Nearby organisations</h3>
            <p className="muted">
              Choose a preference. The final destination may differ depending on availability and pickup coordination.
            </p>
            {nearbyNote ? <p className="field-hint">{nearbyNote}</p> : null}
            {nearby.map((item) => (
              <label key={item.id} className="surface-card stack">
                <span>
                  <input
                    type="radio"
                    name="preferred-centre"
                    checked={preferredCentreId === item.id}
                    onChange={() => setPreferredCentreId(item.id)}
                  />{" "}
                  <strong>{item.name}</strong>
                </span>
                <span className="muted">
                  {item.facility_type || "Facility"} · {item.locality || item.address || "Address on file"} · about{" "}
                  {item.distance_km} km straight-line
                </span>
                <span className="field-hint">Research listing, not a confirmed destination.</span>
              </label>
            ))}
            <p className="field-hint">
              Your preference helps us coordinate the donation. The final destination may change if another eligible
              organisation is more practical or the preferred organisation cannot accept it.
            </p>
          </section>
          {error ? <p className="field-error">{error}</p> : null}
          <div className="row-actions">
            <Button type="button" variant="secondary" onClick={() => setStep(2)}>
              Back
            </Button>
            <Button type="submit" disabled={busy || !checklistOk}>
              {busy ? "Submitting…" : "Submit donation"}
            </Button>
          </div>
        </section>
      ) : null}
    </form>
  );
}
