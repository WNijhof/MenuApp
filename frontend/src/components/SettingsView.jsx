import { useEffect, useState } from "react";
import { api } from "../api.js";
import { applyTheme, DEFAULT_ACCENT_COLOR, DEFAULT_BACKGROUND_COLOR } from "../theme.js";
import { SUPPORTED_LANGUAGES, useTranslation } from "../i18n.jsx";

const DAYS_PER_WEEK = 7;

export default function SettingsView() {
  const { t, language, setLanguage } = useTranslation();
  const [counts, setCounts] = useState({ hoofdgerecht: 7, voorgerecht: 0, nagerecht: 0 });
  const [colors, setColors] = useState({ background_color: null, accent_color: null });
  const [selectedLanguage, setSelectedLanguage] = useState(language);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const settings = await api.getSettings();
        setCounts({
          hoofdgerecht: settings.default_hoofdgerecht,
          voorgerecht: settings.default_voorgerecht,
          nagerecht: settings.default_nagerecht,
        });
        setColors({
          background_color: settings.background_color,
          accent_color: settings.accent_color,
        });
        setSelectedLanguage(settings.language);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const total = counts.hoofdgerecht + counts.voorgerecht + counts.nagerecht;
  const valid = total <= DAYS_PER_WEEK;

  const handleChange = (course, value) => {
    const n = Math.max(0, parseInt(value, 10) || 0);
    setCounts((prev) => ({ ...prev, [course]: n }));
    setSaved(false);
  };

  const handleColorChange = (field, value) => {
    const updated = { ...colors, [field]: value };
    setColors(updated);
    applyTheme(updated); // live preview, persisted only on Save
    setSaved(false);
  };

  const handleResetColors = () => {
    const updated = { background_color: null, accent_color: null };
    setColors(updated);
    applyTheme(updated);
    setSaved(false);
  };

  const handleLanguageChange = (value) => {
    setSelectedLanguage(value);
    setLanguage(value); // live switch, persisted only on Save
    setSaved(false);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    if (!valid) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await api.updateSettings({
        default_hoofdgerecht: counts.hoofdgerecht,
        default_voorgerecht: counts.voorgerecht,
        default_nagerecht: counts.nagerecht,
        background_color: colors.background_color,
        accent_color: colors.accent_color,
        language: selectedLanguage,
      });
      applyTheme(updated);
      setLanguage(updated.language);
      setSaved(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <p className="status-text">{t("settings.loading")}</p>;

  return (
    <div>
      <p className="help-text">{t("settings.courseCountsHelp")}</p>

      {error && <p className="error-text">{error}</p>}

      <form onSubmit={handleSave}>
        <div className="toolbar course-count-toolbar">
          <label>
            {t("course.mains")}:{" "}
            <input
              type="number"
              min="0"
              max={DAYS_PER_WEEK}
              value={counts.hoofdgerecht}
              onChange={(e) => handleChange("hoofdgerecht", e.target.value)}
            />
          </label>
          <label>
            {t("course.starters")}:{" "}
            <input
              type="number"
              min="0"
              max={DAYS_PER_WEEK}
              value={counts.voorgerecht}
              onChange={(e) => handleChange("voorgerecht", e.target.value)}
            />
          </label>
          <label>
            {t("course.desserts")}:{" "}
            <input
              type="number"
              min="0"
              max={DAYS_PER_WEEK}
              value={counts.nagerecht}
              onChange={(e) => handleChange("nagerecht", e.target.value)}
            />
          </label>
        </div>
        {!valid && (
          <p className="error-text">{t("course.countTooHigh", { max: DAYS_PER_WEEK, count: total })}</p>
        )}

        <h3>{t("settings.colorsHeading")}</h3>
        <p className="help-text">{t("settings.colorsHelp")}</p>
        <div className="toolbar course-count-toolbar">
          <label>
            {t("settings.backgroundColorLabel")}{" "}
            <input
              type="color"
              value={colors.background_color || DEFAULT_BACKGROUND_COLOR}
              onChange={(e) => handleColorChange("background_color", e.target.value)}
            />
          </label>
          <label>
            {t("settings.accentColorLabel")}{" "}
            <input
              type="color"
              value={colors.accent_color || DEFAULT_ACCENT_COLOR}
              onChange={(e) => handleColorChange("accent_color", e.target.value)}
            />
          </label>
          <button type="button" onClick={handleResetColors}>
            {t("settings.resetColors")}
          </button>
        </div>

        <h3>{t("settings.languageHeading")}</h3>
        <p className="help-text">{t("settings.languageHelp")}</p>
        <div className="toolbar course-count-toolbar">
          <label>
            {t("settings.languageLabel")}{" "}
            <select value={selectedLanguage} onChange={(e) => handleLanguageChange(e.target.value)}>
              {SUPPORTED_LANGUAGES.map((code) => (
                <option key={code} value={code}>
                  {code === "en" ? t("settings.languageEnglish") : t("settings.languageDutch")}
                </option>
              ))}
            </select>
          </label>
        </div>

        <button type="submit" disabled={saving || !valid} style={{ marginTop: "1rem" }}>
          {saving ? t("common.busy") : saved ? t("common.saved") : t("common.save")}
        </button>
      </form>
    </div>
  );
}
