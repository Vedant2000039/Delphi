/**
 * Delphi AI - Context Builder
 * ----------------------------------------------------------------------------
 * Enterprise onboarding wizard that collects product/service-specific
 * targeting context (product, geography, industry, category, target audience)
 * before the user reaches the Intelligence Dashboard.
 *
 * Location: frontend/src/components/Onboarding/context_builder.js
 * ----------------------------------------------------------------------------
 */

import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import {
  ChevronLeft,
  ChevronRight,
  Search,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Package,
  Globe2,
  Building2,
  LayoutGrid,
  Users,
} from "lucide-react";
import "./context_builder.css";

// ----------------------------------------------------------------------------
// Config
// ----------------------------------------------------------------------------

const API_BASE_URL = process.env.REACT_APP_API_DOMAIN || "http://localhost:8000";

const STEP_META = [
  { key: "product", label: "Product", icon: Package },
  { key: "geography", label: "Geography", icon: Globe2 },
  { key: "industry", label: "Industry", icon: Building2 },
  { key: "category", label: "Category", icon: LayoutGrid },
  { key: "audience", label: "Audience", icon: Users },
];

const TOTAL_STEPS = STEP_META.length;

// ----------------------------------------------------------------------------
// Axios instance
// ----------------------------------------------------------------------------

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

/**
 * Safely extracts a human-readable error message from an Axios/FastAPI error.
 * FastAPI's `detail` can be:
 *   - a plain string (HTTPException(detail="..."))
 *   - an array of Pydantic validation error objects: [{type, loc, msg, input}, ...]
 *   - missing entirely (network error, timeout, etc.)
 * Never return a raw object/array here - React cannot render those as children.
 */
function getApiErrorMessage(err, fallback) {
  const detail = err?.response?.data?.detail;

  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object") {
          const field = Array.isArray(item.loc) ? item.loc.at(-1) : item.loc;
          return field ? `${field}: ${item.msg}` : item.msg;
        }
        return null;
      })
      .filter(Boolean);
    if (messages.length) return messages.join(", ");
  }

  if (typeof err?.response?.data?.message === "string") {
    return err.response.data.message;
  }

  if (err?.response?.status) {
    return `${fallback} (Error ${err.response.status})`;
  }

  if (err?.request) {
    return "Could not reach the server. Please check your connection and try again.";
  }

  return fallback;
}

// ----------------------------------------------------------------------------
// Small reusable UI primitives
// ----------------------------------------------------------------------------

/** Progress bar + step indicator shown at the top of the wizard */
function ProgressHeader({ currentStep }) {
  const percent = Math.round((currentStep / TOTAL_STEPS) * 100);

  return (
    <div className="cb-progress-header">
      <div className="cb-progress-top-row">
        <span className="cb-progress-step-label">
          Step {currentStep} of {TOTAL_STEPS}
        </span>
        <span className="cb-progress-percent">{percent}%</span>
      </div>
      <div className="cb-progress-track">
        <div
          className="cb-progress-fill"
          style={{ width: `${percent}%` }}
          role="progressbar"
          aria-valuenow={percent}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
      <div className="cb-progress-dots">
        {STEP_META.map((step, idx) => {
          const stepNumber = idx + 1;
          const Icon = step.icon;
          const state =
            stepNumber < currentStep
              ? "done"
              : stepNumber === currentStep
              ? "active"
              : "pending";
          return (
            <div key={step.key} className={`cb-dot cb-dot-${state}`}>
              <div className="cb-dot-circle">
                {state === "done" ? (
                  <CheckCircle2 size={16} />
                ) : (
                  <Icon size={16} />
                )}
              </div>
              <span className="cb-dot-label">{step.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/** Inline error / alert banner */
function ErrorBanner({ message, onRetry }) {
  if (!message) return null;
  return (
    <div className="cb-error-banner" role="alert">
      <AlertTriangle size={18} />
      <span>{message}</span>
      {onRetry && (
        <button type="button" className="cb-retry-btn" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

/** Centered loading spinner used while fetching data for a step */
function LoadingState({ label = "Loading..." }) {
  return (
    <div className="cb-loading-state">
      <Loader2 className="cb-spin" size={28} />
      <span>{label}</span>
    </div>
  );
}

/** Single-select card grid (used in Step 1: Product/Service) */
function SingleSelectCards({ items, selected, onSelect }) {
  if (!items || items.length === 0) {
    return (
      <div className="cb-empty-state">
        No products or services found for your account. Please contact your
        administrator.
      </div>
    );
  }

  return (
    <div className="cb-card-grid">
      {items.map((item) => {
        const isActive = selected === item;
        return (
          <button
            type="button"
            key={item}
            className={`cb-select-card ${isActive ? "cb-select-card-active" : ""}`}
            onClick={() => onSelect(item)}
            aria-pressed={isActive}
          >
            <span className="cb-select-card-label">{item}</span>
            {isActive && (
              <span className="cb-select-card-check">
                <CheckCircle2 size={18} />
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

/** Searchable multi-select list (used in Steps 2-5) */
function SearchableMultiSelect({
  items,
  selectedItems,
  onToggle,
  placeholder,
  emptyMessage,
  labelKey,
  valueKey,
}) {
  const [query, setQuery] = useState("");

  const normalizedItems = useMemo(
    () =>
      (items || []).map((it) =>
        typeof it === "string" ? { label: it, value: it } : { label: it[labelKey], value: it[valueKey] }
      ),
    [items, labelKey, valueKey]
  );

  const filteredItems = useMemo(() => {
    if (!query.trim()) return normalizedItems;
    const q = query.trim().toLowerCase();
    return normalizedItems.filter((it) => it.label.toLowerCase().includes(q));
  }, [normalizedItems, query]);

  return (
    <div className="cb-multiselect">
      <div className="cb-search-box">
        <Search size={16} className="cb-search-icon" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder}
          className="cb-search-input"
          aria-label={placeholder}
        />
      </div>

      {selectedItems.length > 0 && (
        <div className="cb-selected-chips">
          {selectedItems.map((val) => {
            const match = normalizedItems.find((it) => it.value === val);
            return (
              <span key={val} className="cb-chip">
                {match ? match.label : val}
                <button
                  type="button"
                  className="cb-chip-remove"
                  onClick={() => onToggle(val)}
                  aria-label={`Remove ${match ? match.label : val}`}
                >
                  &times;
                </button>
              </span>
            );
          })}
        </div>
      )}

      <div className="cb-multiselect-list">
        {filteredItems.length === 0 ? (
          <div className="cb-empty-state">{emptyMessage}</div>
        ) : (
          filteredItems.map((it) => {
            const checked = selectedItems.includes(it.value);
            return (
              <label
                key={it.value}
                className={`cb-multiselect-item ${checked ? "cb-multiselect-item-active" : ""}`}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => onToggle(it.value)}
                />
                <span>{it.label}</span>
                {checked && <CheckCircle2 size={16} className="cb-item-check" />}
              </label>
            );
          })
        )}
      </div>
    </div>
  );
}

// ----------------------------------------------------------------------------
// Main Component
// ----------------------------------------------------------------------------

/**
 * Resolves the current user's id.
 * Prefers the explicit `userId` prop; falls back to what the Otp.js flow
 * actually persists to localStorage, which is a single JSON-stringified
 * object under the key "user" (e.g. `{ user_id, email, full_name, ... }`),
 * not a flat "user_id" / "userId" key. We also keep a couple of legacy flat
 * key fallbacks in case another part of the app writes them directly.
 */
function resolveUserId(userIdProp) {
  if (userIdProp !== undefined && userIdProp !== null && userIdProp !== "") {
    return userIdProp;
  }
  if (typeof window === "undefined") return null;

  // Primary source: the nested "user" object stored by Otp.js after
  // OTP verification.
  try {
    const rawUser = window.localStorage.getItem("user");
    if (rawUser) {
      const parsedUser = JSON.parse(rawUser);
      if (parsedUser && parsedUser.user_id !== undefined && parsedUser.user_id !== null) {
        return parsedUser.user_id;
      }
    }
  } catch (e) {
    // Malformed JSON in localStorage — ignore and fall through to legacy keys.
  }

  // Legacy / defensive fallback keys, in case something else in the app
  // ever writes a flat value directly.
  const fallbackKeys = ["user_id", "userId", "delphi_user_id"];
  for (const key of fallbackKeys) {
    const value = window.localStorage.getItem(key);
    if (value) return value;
  }

  return null;
}

export default function ContextBuilder({ userId: userIdProp, onComplete }) {
  const navigate = useNavigate();
  const userId = resolveUserId(userIdProp);
  const [currentStep, setCurrentStep] = useState(1);

  // Data returned from backend
  const [companyType, setCompanyType] = useState(null); // "Product Based Company" | "Service Based Company"
  const [productItems, setProductItems] = useState([]);
  const [countries, setCountries] = useState([]);
  const [industries, setIndustries] = useState([]);
  const [categories, setCategories] = useState([]);
  const [domains, setDomains] = useState([]);

  // User selections
  const [selectedItem, setSelectedItem] = useState(null); // product or service name
  const [selectedGeographies, setSelectedGeographies] = useState([]);
  const [selectedIndustries, setSelectedIndustries] = useState([]);
  const [selectedCategories, setSelectedCategories] = useState([]);
  const [selectedDomains, setSelectedDomains] = useState([]);

  // Loading / error states, keyed per step so each step manages its own fetch lifecycle
  const [loadingStep, setLoadingStep] = useState(false);
  const [stepError, setStepError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");

  const isServiceBased = companyType === "Service Based Company";

  // --------------------------------------------------------------------
  // Fetchers
  // --------------------------------------------------------------------

  const fetchProductItems = useCallback(async () => {
    if (!userId) {
      setStepError(
        "We couldn't identify your account. Please log in again to continue."
      );
      return;
    }
    setLoadingStep(true);
    setStepError("");
    try {
      const { data } = await api.get(`/context-builder/items/${userId}`);
      setCompanyType(data.company_type);
      setProductItems(data.items || []);
    } catch (err) {
      setStepError(
        getApiErrorMessage(err, "Unable to load your products or services right now. Please try again.")
      );
    } finally {
      setLoadingStep(false);
    }
  }, [userId]);

  const fetchCountries = useCallback(async () => {
    setLoadingStep(true);
    setStepError("");
    try {
      const { data } = await api.get("/context-builder/geographies");
      setCountries(data.geographies || data || []);
    } catch (err) {
      setStepError(
        getApiErrorMessage(err, "Unable to load geographies right now. Please try again.")
      );
    } finally {
      setLoadingStep(false);
    }
  }, []);

  const fetchIndustries = useCallback(async () => {
    setLoadingStep(true);
    setStepError("");
    try {
      const { data } = await api.get("/context-builder/industries");
      setIndustries(data.industries || data || []);
    } catch (err) {
      setStepError(
        getApiErrorMessage(err, "Unable to load industries right now. Please try again.")
      );
    } finally {
      setLoadingStep(false);
    }
  }, []);

  const fetchCategories = useCallback(async () => {
    if (selectedIndustries.length === 0) {
      setCategories([]);
      return;
    }
    setLoadingStep(true);
    setStepError("");
    try {
      const { data } = await api.post("/context-builder/categories", {
        industries: selectedIndustries,
      });
      setCategories(data.categories || data || []);
    } catch (err) {
      setStepError(
        getApiErrorMessage(err, "Unable to load categories right now. Please try again.")
      );
    } finally {
      setLoadingStep(false);
    }
  }, [selectedIndustries]);

  const fetchDomains = useCallback(async () => {
    if (selectedCategories.length === 0) {
      setDomains([]);
      return;
    }
    setLoadingStep(true);
    setStepError("");
    try {
      const { data } = await api.post("/context-builder/domains", {
        categories: selectedCategories,
      });
      setDomains(data.domains || data || []);
    } catch (err) {
      setStepError(
        getApiErrorMessage(err, "Unable to load target audience options right now. Please try again.")
      );
    } finally {
      setLoadingStep(false);
    }
  }, [selectedCategories]);

  // --------------------------------------------------------------------
  // Effects - fetch data lazily as the user reaches each step
  // --------------------------------------------------------------------

  useEffect(() => {
    if (currentStep === 1) fetchProductItems();
  }, [currentStep, fetchProductItems]);

  useEffect(() => {
    if (currentStep === 2 && countries.length === 0) fetchCountries();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentStep]);

  useEffect(() => {
    if (currentStep === 3 && industries.length === 0) fetchIndustries();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentStep]);

  useEffect(() => {
    if (currentStep === 4) fetchCategories();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentStep]);

  useEffect(() => {
    if (currentStep === 5) fetchDomains();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentStep]);

  // Reset downstream selections when an upstream selection changes
  useEffect(() => {
    setSelectedCategories([]);
    setSelectedDomains([]);
  }, [selectedIndustries]);

  useEffect(() => {
    setSelectedDomains([]);
  }, [selectedCategories]);

  // --------------------------------------------------------------------
  // Toggle helpers for multi-select steps
  // --------------------------------------------------------------------

  const toggleValue = (list, setList) => (value) => {
    setList((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]
    );
  };

  const toggleGeography = toggleValue(selectedGeographies, setSelectedGeographies);
  const toggleIndustry = toggleValue(selectedIndustries, setSelectedIndustries);
  const toggleCategory = toggleValue(selectedCategories, setSelectedCategories);
  const toggleDomain = toggleValue(selectedDomains, setSelectedDomains);

  // --------------------------------------------------------------------
  // Step validation
  // --------------------------------------------------------------------

  const isStepValid = useMemo(() => {
    switch (currentStep) {
      case 1:
        return Boolean(selectedItem);
      case 2:
        return selectedGeographies.length > 0;
      case 3:
        return selectedIndustries.length > 0;
      case 4:
        return selectedCategories.length > 0;
      case 5:
        return selectedDomains.length > 0;
      default:
        return false;
    }
  }, [
    currentStep,
    selectedItem,
    selectedGeographies,
    selectedIndustries,
    selectedCategories,
    selectedDomains,
  ]);

  // --------------------------------------------------------------------
  // Navigation
  // --------------------------------------------------------------------

  /**
   * Advances the wizard. On the final step this triggers the save; the
   * actual redirect to the dashboard happens inside handleFinish, only
   * after the save succeeds - never directly from a click handler, since
   * we need to await the API call first.
   */
  const goNext = () => {
    if (!isStepValid) return;
    if (currentStep < TOTAL_STEPS) {
      setCurrentStep((s) => s + 1);
    } else {
      handleFinish();
    }
  };

  const goPrevious = () => {
    setStepError("");
    if (currentStep > 1) setCurrentStep((s) => s - 1);
  };

  const handleFinish = async () => {
    setSubmitting(true);
    setSubmitError("");
    try {
      const payload = {
        user_id: userId,
        selected_product: isServiceBased ? null : selectedItem,
        selected_service: isServiceBased ? selectedItem : null,
        geographies: selectedGeographies,
        industries: selectedIndustries,
        categories: selectedCategories,
        domains: selectedDomains,
      };
      await api.post("/context-builder/save", payload);
      if (typeof onComplete === "function") {
        onComplete(payload);
      }
      // Only redirect after the save has actually succeeded.
      navigate("/Dashboard");
    } catch (err) {
      setSubmitError(
        getApiErrorMessage(err, "We couldn't save your preferences. Please try again.")
      );
    } finally {
      setSubmitting(false);
    }
  };

  // --------------------------------------------------------------------
  // Retry handler - re-fetches data for the current step
  // --------------------------------------------------------------------

  const retryCurrentStep = () => {
    switch (currentStep) {
      case 1:
        return fetchProductItems();
      case 2:
        return fetchCountries();
      case 3:
        return fetchIndustries();
      case 4:
        return fetchCategories();
      case 5:
        return fetchDomains();
      default:
        return null;
    }
  };

  // --------------------------------------------------------------------
  // Step content renderer
  // --------------------------------------------------------------------

  const renderStepContent = () => {
    if (loadingStep) {
      return <LoadingState label="Fetching your data..." />;
    }

    switch (currentStep) {
      case 1:
        return (
          <SingleSelectCards
            items={productItems}
            selected={selectedItem}
            onSelect={setSelectedItem}
          />
        );

      case 2:
        return (
          <SearchableMultiSelect
            items={countries}
            selectedItems={selectedGeographies}
            onToggle={toggleGeography}
            placeholder="Search countries..."
            emptyMessage="No countries match your search."
            labelKey="Location_desc"
            valueKey="Location_id"
          />
        );

      case 3:
        return (
          <SearchableMultiSelect
            items={industries}
            selectedItems={selectedIndustries}
            onToggle={toggleIndustry}
            placeholder="Search industries..."
            emptyMessage="No industries match your search."
          />
        );

      case 4:
        return (
          <SearchableMultiSelect
            items={categories}
            selectedItems={selectedCategories}
            onToggle={toggleCategory}
            placeholder="Search categories..."
            emptyMessage="No categories available for the selected industries."
            labelKey="category"
            valueKey="category"
          />
        );

      case 5:
        return (
          <SearchableMultiSelect
            items={domains}
            selectedItems={selectedDomains}
            onToggle={toggleDomain}
            placeholder="Search target audience..."
            emptyMessage="No target audience options available for the selected categories."
            labelKey="domain"
            valueKey="domain"
          />
        );

      default:
        return null;
    }
  };

  const stepTitles = {
    1: "Choose what you want Delphi to analyze",
    2: `Which geography are you targeting for ${selectedItem || "your selection"}?`,
    3: `Which industries do you want to target for ${selectedItem || "your selection"}?`,
    4: `Which category of customers do you want to target for ${selectedItem || "your selection"}?`,
    5: `Do you have any preferred target domain audience for ${selectedItem || "your selection"}?`,
  };

  const stepDescriptions = {
    1: "Select one product, brand, or service for which you want to generate insights and recommendations.",
    2: "Choose one or more countries where you want to focus your outreach.",
    3: "Choose the industries that best represent your ideal customers.",
    4: "Narrow down to specific customer categories within your chosen industries.",
    5: "Pick the domain you'd most like to reach.",
  };

  return (
    <div className="cb-page">
      <div className="cb-container">
        <ProgressHeader currentStep={currentStep} />

        <div className="cb-card">
          <div className="cb-card-header">
            <h1 className="cb-title">{stepTitles[currentStep]}</h1>
            <p className="cb-description">{stepDescriptions[currentStep]}</p>
          </div>

          <ErrorBanner message={stepError} onRetry={retryCurrentStep} />
          <ErrorBanner message={submitError} onRetry={handleFinish} />

          <div className="cb-card-body">{renderStepContent()}</div>

          <div className="cb-card-footer">
            <button
              type="button"
              className="cb-btn cb-btn-secondary"
              onClick={goPrevious}
              disabled={currentStep === 1 || submitting}
            >
              <ChevronLeft size={18} />
              Previous
            </button>

            <button
              type="button"
              className="cb-btn cb-btn-primary"
              onClick={goNext}
              disabled={!isStepValid || submitting}
            >
              {submitting ? (
                <>
                  <Loader2 className="cb-spin" size={18} />
                  Saving...
                </>
              ) : currentStep === TOTAL_STEPS ? (
                "Finish"
              ) : (
                <>
                  Continue
                  <ChevronRight size={18} />
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}