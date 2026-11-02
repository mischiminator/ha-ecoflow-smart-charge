/* EcoFlow Smart Charge: dashboard card bundled with the integration.
 * Finds its entities through the integration's service device (translation keys), so it
 * needs no entity mapping; writes only the integration's own switch, select and numbers. */
const EFS_DOMAIN = 'ecoflow_smart_charge';
const EFS_CARD = 'ecoflow-smart-charge-card';

const EFS_TEXT = {
  de: {
    title: 'EcoFlow Preisladung',
    subtitle: n => `Solargeführt · ${n} ${n === 1 ? 'Akku' : 'Akkus'}`,
    shadowSubtitle: 'Shadow-Modus · keine Gerätebefehle',
    notFound: 'Keine EcoFlow-Smart-Charge-Instanz gefunden.',
    pickDevice: 'Mehrere Instanzen gefunden – bitte in der Kartenkonfiguration ein Gerät wählen.',
    loading: 'Wird geladen',
    unavailable: 'Nicht verfügbar',
    status: {
      shadow: 'Shadow-Modus', off: 'Ausgeschaltet', waiting: 'Aktiv · wartet', allowed: 'Ladung freigegeben',
      charging: 'Netzladung läuft', charge_pending: 'Reserve wird gesetzt', charge_blocked: 'Ladung gesperrt',
      restore_pending: 'Reserve wird zurückgestellt', restored: 'Reserve wiederhergestellt',
      recovery_pending: 'Wiederherstellung offen', recovery_blocked: 'Wiederherstellung blockiert',
    },
    masterOff: 'Die automatische Netzladung ist ausgeschaltet. Solarladung bleibt davon unberührt.',
    noPlan: 'Warte auf eine gültige Planung.',
    dataMissing: 'Es fehlen gültige Preis-, Solar- oder Verbrauchsdaten.',
    selfPoweredHint: 'Für den aktiven Modus müssen alle Akkus auf Self-powered stehen.',
    reasons: {
      eligible: 'Solar reicht nicht aus; Preis und erwartete Ersparnis passen.',
      target_reached: 'Netzanteil geladen – die Reserve wird bis zum Ende des Bestpreisfensters gehalten.',
      already_full_for_solar_day: 'Für diesen Solartag wurden die Akkus bereits vollgeladen.',
      batteries_full: 'Alle Akkus sind vollgeladen.',
      price_above_ceiling: 'Der Strompreis liegt über deiner Ladepreisgrenze.',
      solar_surplus_sufficient: 'Der erwartete Solarüberschuss reicht zum Volladen.',
      outside_best_price_window: 'Netzladung wartet auf das nächste Bestpreisfenster.',
      price_gap: 'Im Preisausblick fehlen veröffentlichte Preise.',
      insufficient_priced_consumption: 'Im bekannten Preisausblick ist kein zusätzlicher Akku-Verbrauch prognostiziert.',
      nonpositive_reference_price: 'Der spätere Bezugspreis ist null oder negativ; der Preisvergleich sperrt die Netzladung.',
      price_advantage_too_low: 'Der Preisvorteil gegenüber dem späteren Netzbezug liegt unter deinem Mindestwert.',
      price_advantage_invalid: 'Der eingestellte Mindest-Preisvorteil ist ungültig.',
      net_saving_too_low: 'Die erwartete Nettoersparnis ist zu gering.',
      protection_mode_required: 'Alle Akkus müssen im Eigenverbrauchsmodus (Self-powered) sein.',
      profile_invalid: 'Das Verbrauchsprofil hat noch zu wenig Verlauf (mindestens 3 Werte je Stunde).',
    },
    goal: v => `Ladeziel ${v} %`,
    noGoal: 'Kein Netzladeziel',
    price: 'Strompreis jetzt',
    priceDetail: (c, a, m) => `Ladegrenze ${c} ct/kWh · Preisvorteil ${a} % / min. ${m} %`,
    solar: 'Solar-Ladeüberschuss',
    solarDetail: 'Nach erwartetem Haushaltsverbrauch',
    saving: 'Nettoersparnis · Prognose',
    savingDetail: m => `Mindestens ${m} ct/kWh erforderlich`,
    grid: 'Netzladung geplant',
    gridDetail: (need, forecast) => `Fehlend ${need} kWh · PV-Prognose ${forecast} kWh`,
    window: 'Bestpreisfenster',
    windowNow: 'Jetzt aktiv',
    windowNext: 'Anstehend',
    windowEnd: 'Ende',
    noWindow: 'Kein anstehendes Fenster veröffentlicht.',
    windowUnavailable: 'Fensterdaten nicht verfügbar.',
    total: 'Batteriestand gesamt',
    totalDetail: 'Kapazitätsgewichtet über alle Akkus',
    totalUnavailable: 'Gesamtstand nicht verfügbar.',
    reserve: 'Reserve',
    showHistory: 'Verlauf anzeigen',
    footer: (s, f) => `Profil ${s} Werte/Stunde · PV-Faktor ${f}`,
    planned: t => `Planung ${t}`,
    notPlanned: 'Noch keine Planung',
    toggleOn: 'Automatische Preisladung einschalten',
    toggleOff: 'Automatische Preisladung ausschalten',
    settings: 'Konfiguration',
    dialogTitle: 'Preisladung konfigurieren',
    close: 'Schließen',
    intro: 'Änderungen werden erst mit „Speichern“ übernommen. Die Solar- und Wirtschaftlichkeitsprüfung bleibt immer aktiv.',
    master: 'Automatische Preisladung',
    mode: 'Controller-Modus',
    modes: { shadow: 'Shadow – nur planen', active: 'Aktiv – Reserven steuern' },
    fields: {
      charge_ceiling_ct: ['Maximaler Ladepreis', 'Endpreis inklusive variabler Preisbestandteile'],
      minimum_net_saving_ct: ['Mindest-Nettoersparnis', 'Je abgegebener kWh, nach Verlusten und Verschleiß'],
      minimum_price_advantage: ['Mindest-Preisvorteil', 'Ladepreis gegenüber dem verbrauchsgewichteten späteren Bezugspreis'],
      efficiency: ['Gesamtwirkungsgrad', 'Netz → Akku → Haushalt; Rechenannahme'],
      wear_cost_ct: ['Verschleiß-Aufschlag', 'Je abgegebener kWh; Rechenannahme'],
      capacity_kwh: ['Rückfall-Kapazität', 'Nur für Akkus, deren Modell keine bekannte Kapazität hat'],
    },
    info: f => `PV-Faktor ${f} · wird anhand gemessener Erzeugung selbstständig weitergelernt. Aus dem Netz wird nur geladen, was der erwartete Solarüberschuss nicht schafft. Bei zu hohem Preis, fehlender Ersparnis oder ungültigen Daten wird die vorherige Backup-Reserve wiederhergestellt. Der EcoFlow-Betriebsmodus wird nie verändert.`,
    cancel: 'Abbrechen',
    save: 'Speichern',
    savingProgress: 'Speichert …',
    saved: 'Gespeichert und von Home Assistant bestätigt.',
    noChanges: 'Keine Änderungen – die aktuellen Einstellungen bleiben erhalten.',
    invalidNumbers: 'Bitte gültige Zahlen eingeben.',
    changedOutside: 'Ein Wert wurde zwischenzeitlich außerhalb dieses Dialogs geändert. Bitte schließen und erneut öffnen.',
    partlyApplied: n => `${n} Änderung(en) wurden bereits übernommen. `,
    notConfirmed: e => `Home Assistant hat den neuen Wert nicht bestätigt: ${e}`,
    settingsUnavailable: e => `Konfiguration nicht verfügbar: ${e}`,
    editorTitle: 'Titel',
    editorDevice: 'EcoFlow-Smart-Charge-Instanz',
  },
  en: {
    title: 'EcoFlow Smart Charge',
    subtitle: n => `Solar-led · ${n} ${n === 1 ? 'battery' : 'batteries'}`,
    shadowSubtitle: 'Shadow mode · no device commands',
    notFound: 'No EcoFlow Smart Charge instance found.',
    pickDevice: 'Several instances found – choose a device in the card configuration.',
    loading: 'Loading',
    unavailable: 'Unavailable',
    status: {
      shadow: 'Shadow mode', off: 'Switched off', waiting: 'Active · waiting', allowed: 'Charging allowed',
      charging: 'Grid charging', charge_pending: 'Setting reserve', charge_blocked: 'Charging blocked',
      restore_pending: 'Restoring reserve', restored: 'Reserve restored',
      recovery_pending: 'Recovery pending', recovery_blocked: 'Recovery blocked',
    },
    masterOff: 'Automatic grid charging is switched off. Solar charging is not affected.',
    noPlan: 'Waiting for a valid plan.',
    dataMissing: 'Valid price, solar or consumption data are missing.',
    selfPoweredHint: 'Active mode needs every battery in Self-powered mode.',
    reasons: {
      eligible: 'Solar is not enough; price and expected saving fit.',
      target_reached: 'Grid share charged – the reserve is held until the best-price window ends.',
      already_full_for_solar_day: 'The batteries were already full for this solar day.',
      batteries_full: 'All batteries are full.',
      price_above_ceiling: 'The price is above your charge price ceiling.',
      solar_surplus_sufficient: 'The expected solar surplus is enough to fill the batteries.',
      outside_best_price_window: 'Grid charging waits for the next best-price window.',
      price_gap: 'Published prices are missing in the outlook.',
      insufficient_priced_consumption: 'No additional battery consumption is forecast within the known prices.',
      nonpositive_reference_price: 'The later grid price is zero or negative; the price comparison blocks charging.',
      price_advantage_too_low: 'The price advantage is below your minimum.',
      price_advantage_invalid: 'The configured minimum price advantage is invalid.',
      net_saving_too_low: 'The expected net saving is too low.',
      protection_mode_required: 'All batteries must be in Self-powered mode.',
      profile_invalid: 'The consumption profile needs more history (at least 3 values per hour).',
    },
    goal: v => `Charge target ${v} %`,
    noGoal: 'No grid target',
    price: 'Price now',
    priceDetail: (c, a, m) => `Ceiling ${c} ct/kWh · advantage ${a} % / min. ${m} %`,
    solar: 'Solar charge surplus',
    solarDetail: 'After expected household load',
    saving: 'Net saving · forecast',
    savingDetail: m => `At least ${m} ct/kWh required`,
    grid: 'Planned grid charge',
    gridDetail: (need, forecast) => `Missing ${need} kWh · PV forecast ${forecast} kWh`,
    window: 'Best-price window',
    windowNow: 'Active now',
    windowNext: 'Upcoming',
    windowEnd: 'ends',
    noWindow: 'No upcoming window published.',
    windowUnavailable: 'Window data unavailable.',
    total: 'Total battery level',
    totalDetail: 'Capacity-weighted over all batteries',
    totalUnavailable: 'Total level unavailable.',
    reserve: 'Reserve',
    showHistory: 'show history',
    footer: (s, f) => `Profile ${s} values/hour · PV factor ${f}`,
    planned: t => `Planned ${t}`,
    notPlanned: 'Not planned yet',
    toggleOn: 'Switch automatic price charging on',
    toggleOff: 'Switch automatic price charging off',
    settings: 'Settings',
    dialogTitle: 'Configure price charging',
    close: 'Close',
    intro: 'Changes apply only after “Save”. The solar and economic checks always stay active.',
    master: 'Automatic price charging',
    mode: 'Controller mode',
    modes: { shadow: 'Shadow – plan only', active: 'Active – control reserves' },
    fields: {
      charge_ceiling_ct: ['Charge price ceiling', 'Final price including variable components'],
      minimum_net_saving_ct: ['Minimum net saving', 'Per delivered kWh, after losses and wear'],
      minimum_price_advantage: ['Minimum price advantage', 'Charge price versus the consumption-weighted later price'],
      efficiency: ['Total efficiency', 'Grid → battery → house; model assumption'],
      wear_cost_ct: ['Wear surcharge', 'Per delivered kWh; model assumption'],
      capacity_kwh: ['Fallback capacity', 'Only for batteries whose model has no known capacity'],
    },
    info: f => `PV factor ${f} · learned automatically from measured generation. The grid only charges what the expected solar surplus cannot fill. On a high price, missing saving or invalid data the previous backup reserve is restored. The EcoFlow operating mode is never changed.`,
    cancel: 'Cancel',
    save: 'Save',
    savingProgress: 'Saving …',
    saved: 'Saved and confirmed by Home Assistant.',
    noChanges: 'No changes – the current settings stay as they are.',
    invalidNumbers: 'Please enter valid numbers.',
    changedOutside: 'A value was changed outside this dialog. Please close and open it again.',
    partlyApplied: n => `${n} change(s) were already applied. `,
    notConfirmed: e => `Home Assistant did not confirm the new value: ${e}`,
    settingsUnavailable: e => `Settings unavailable: ${e}`,
    editorTitle: 'Title',
    editorDevice: 'EcoFlow Smart Charge instance',
  },
};

// [translation key, unit, display scale]; efficiency is stored as a fraction.
const EFS_FIELDS = [
  ['charge_ceiling_ct', 'ct/kWh', 1],
  ['minimum_net_saving_ct', 'ct/kWh', 1],
  ['minimum_price_advantage', '%', 1],
  ['efficiency', '%', 100],
  ['wear_cost_ct', 'ct/kWh', 1],
  ['capacity_kwh', 'kWh', 1],
];
const EFS_GENERIC_REASONS = new Set([
  'source_missing', 'sources_stale', 'prices_stale', 'current_price_mismatch', 'time_invalid',
  'sunset_invalid', 'required_state_invalid', 'battery_data_invalid', 'parameters_invalid',
  'forecast_profile_invalid', 'projection_invalid', 'price_data_invalid',
]);

const efsIcon = path => `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${path}"></path></svg>`;
const EFS_GEAR = efsIcon('M19.4 13a7.8 7.8 0 0 0 0-2l2-1.5-2-3.5-2.3.9a8 8 0 0 0-1.7-1L15 3h-4l-.4 2.9a8 8 0 0 0-1.7 1L6.6 6l-2 3.5 2 1.5a7.8 7.8 0 0 0 0 2l-2 1.5 2 3.5 2.3-.9a8 8 0 0 0 1.7 1L11 21h4l.4-2.9a8 8 0 0 0 1.7-1l2.3.9 2-3.5-2-1.5ZM13 15.5a3.5 3.5 0 1 1 0-7 3.5 3.5 0 0 1 0 7Z');
const EFS_BOLT = efsIcon('M13 2 4 14h7l-1 8 10-12h-7l1-8Z');
const EFS_POWER = efsIcon('M11 2h2v10h-2V2Zm6.7 3.3-1.4 1.4a7 7 0 1 1-8.6 0L6.3 5.3a9 9 0 1 0 11.4 0Z');
const EFS_CLOSE = efsIcon('m6.4 5 5.6 5.6L17.6 5 19 6.4 13.4 12l5.6 5.6-1.4 1.4-5.6-5.6L6.4 19 5 17.6l5.6-5.6L5 6.4 6.4 5Z');

// The current window, else the next published one (Tibber Prices exposes `periods`).
function efsSelectedWindow(entity, t, timeZone, now = new Date()) {
  if (!entity || !['on', 'off'].includes(entity.state)) return { available: false, window: null };
  const attrs = entity.attributes || {};
  const periods = Array.isArray(attrs.periods) && attrs.periods.length ? attrs.periods : [attrs];
  const rows = periods.map(p => ({ start: Date.parse(p.start), end: Date.parse(p.end) }))
    .filter(p => Number.isFinite(p.start) && Number.isFinite(p.end) && p.end > p.start)
    .sort((a, b) => a.start - b.start);
  const stamp = now.getTime();
  const active = entity.state === 'on' ? rows.find(p => p.start <= stamp && stamp < p.end) : null;
  const selected = active || rows.find(p => p.start > stamp);
  if (!selected) return { available: true, window: null };
  const time = new Intl.DateTimeFormat('de-DE', { timeZone, hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });
  const day = new Intl.DateTimeFormat('en-CA', { timeZone, year: 'numeric', month: '2-digit', day: '2-digit' });
  const date = new Intl.DateTimeFormat('de-DE', { timeZone, day: '2-digit', month: '2-digit' });
  const start = new Date(selected.start), end = new Date(selected.end);
  const startNote = day.format(start) !== day.format(now) ? ' · ' + date.format(start) : '';
  const endNote = day.format(start) !== day.format(end) ? ` · ${t.windowEnd} ${date.format(end)}` : '';
  return {
    available: true,
    window: { start: time.format(start), end: time.format(end), detail: (active ? t.windowNow : t.windowNext) + startNote + endNote },
  };
}

class EcoFlowSmartChargeCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._saving = false;
    this._toggling = false;
    this._batterySignature = null;
  }

  setConfig(config) {
    if (config.device_id !== undefined && typeof config.device_id !== 'string') throw new Error('device_id must be a device ID.');
    this._config = { ...config };
    this._render();
    this._update();
  }

  set hass(hass) {
    const language = (hass.locale?.language || hass.language || 'en').startsWith('de') ? 'de' : 'en';
    const relocalize = language !== this._language;
    this._hass = hass;
    this._language = language;
    if (relocalize) this._render();
    this._update();
  }

  getCardSize() { return 11; }
  getGridOptions() { return { columns: 12, rows: 'auto', min_rows: 6 }; }
  static getStubConfig() { return {}; }
  static getConfigForm() {
    return {
      schema: [
        { name: 'title', selector: { text: {} } },
        { name: 'device_id', selector: { device: { integration: EFS_DOMAIN } } },
      ],
      computeLabel: s => {
        const t = EFS_TEXT[(document.documentElement.lang || 'en').startsWith('de') ? 'de' : 'en'];
        return s.name === 'title' ? t.editorTitle : t.editorDevice;
      },
    };
  }

  connectedCallback() {
    if (!this._timer) this._timer = setInterval(() => this._update(), 60000);
    this._update();
  }

  disconnectedCallback() {
    clearInterval(this._timer);
    this._timer = null;
    if (this._refs?.dialog?.open) this._refs.dialog.close();
  }

  get _t() { return EFS_TEXT[this._language || 'de']; }

  _render() {
    if (!this._config) return;
    const t = this._t;
    this._batterySignature = null;
    this.shadowRoot.innerHTML = `<style>
      :host{display:block;min-width:0;font-family:var(--ha-font-family,Roboto,Arial,sans-serif);color:var(--primary-text-color,#202124)}
      *{box-sizing:border-box}ha-card{display:block;overflow:hidden;background:var(--ha-card-background,var(--card-background-color,#fff));border:var(--ha-card-border-width,1px) solid var(--ha-card-border-color,var(--divider-color,#ddd));border-radius:var(--ha-card-border-radius,16px);box-shadow:var(--ha-card-box-shadow,none)}
      .body{padding:20px}.header{display:flex;align-items:center;gap:12px}.brand{display:grid;place-items:center;width:44px;height:44px;border-radius:14px;background:color-mix(in srgb,var(--primary-color,#03a9f4) 13%,transparent);color:var(--primary-color,#03a9f4);flex-shrink:0}svg{width:22px;height:22px;fill:currentColor}.brand svg{width:26px;height:26px}
      .heading{flex:1;min-width:0}.title{font-weight:650;font-size:17px;line-height:1.3}.subtitle{font-size:12px;color:var(--secondary-text-color,#687078);margin-top:3px}.subtitle[data-shadow=true]{color:var(--warning-color,#a56a00)}
      .icon-button{border:0;background:transparent;color:var(--secondary-text-color,#687078);height:40px;width:40px;border-radius:50%;display:grid;place-items:center;cursor:pointer;flex-shrink:0}.icon-button:hover{background:var(--secondary-background-color,#f1f3f5)}.icon-button[aria-pressed=true]{color:var(--primary-color,#03a9f4);background:color-mix(in srgb,var(--primary-color,#03a9f4) 10%,transparent)}
      button:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid var(--primary-color,#03a9f4);outline-offset:3px}button:disabled{opacity:.55;cursor:wait}
      .state-line{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:20px}.badge{display:inline-flex;align-items:center;gap:7px;font-size:12px;font-weight:600;line-height:1.3;padding:7px 10px;border-radius:999px;background:var(--secondary-background-color,#f1f3f5);color:var(--secondary-text-color,#687078)}.badge:before{content:'';width:7px;height:7px;border-radius:50%;background:currentColor;flex-shrink:0}.badge[data-tone=good]{color:var(--success-color,#268b59);background:color-mix(in srgb,var(--success-color,#268b59) 12%,transparent)}.badge[data-tone=warn]{color:var(--warning-color,#a56a00);background:color-mix(in srgb,var(--warning-color,#a56a00) 12%,transparent)}
      .goal{font-size:12px;color:var(--secondary-text-color,#687078);white-space:nowrap}.reason{font-size:13px;line-height:1.5;margin:10px 0 18px;min-height:20px;color:var(--secondary-text-color,#687078)}
      .metrics{display:grid;grid-template-columns:1fr 1fr;gap:10px}.metric{padding:12px;border-radius:12px;background:var(--secondary-background-color,#f6f7f8);min-width:0}.label{font-size:11px;line-height:1.3;color:var(--secondary-text-color,#687078)}.value{font-size:22px;line-height:1.3;font-weight:600;font-variant-numeric:tabular-nums;margin:5px 0 3px;white-space:nowrap}.value small{font-weight:400;font-size:11px;margin-left:4px}.detail{font-size:11px;line-height:1.4;color:var(--secondary-text-color,#687078)}.value[data-tone=bad]{color:var(--error-color,#c64646)}.value[data-tone=good]{color:var(--success-color,#268b59)}
      .window-range{display:flex;flex-wrap:wrap;gap:0 2px;white-space:normal}.window-range span{white-space:nowrap}
      .history{display:block;width:100%;min-width:0;min-height:44px;margin:0;border:0;color:inherit;font:inherit;text-align:left;cursor:pointer;appearance:none}.history:hover{background:color-mix(in srgb,var(--primary-color,#03a9f4) 9%,var(--secondary-background-color,#f6f7f8))}.history:focus-visible{outline:3px solid var(--primary-color,#03a9f4);outline-offset:3px}
      .batteries{display:grid;grid-template-columns:repeat(var(--columns,3),1fr);gap:10px;margin-top:10px}.track{height:5px;margin:10px 0;border-radius:6px;background:var(--divider-color,#e0e3e5);overflow:hidden}.fill{height:100%;width:0;background:var(--primary-color,#03a9f4);border-radius:inherit;transition:width .3s}
      .footer{border-top:1px solid var(--divider-color,#ddd);padding:12px 20px;display:flex;justify-content:space-between;gap:10px;font-size:10px;line-height:1.4;color:var(--secondary-text-color,#687078)}.error{font-size:12px;color:var(--error-color,#c64646);margin-top:10px}.error:empty{display:none}.empty{padding:20px;font-size:13px;line-height:1.5;color:var(--secondary-text-color,#687078)}
      dialog{color:var(--primary-text-color,#202124);background:var(--card-background-color,#fff);border:1px solid var(--divider-color,#ddd);border-radius:20px;padding:0;width:min(560px,calc(100vw - 32px));max-width:calc(100vw - 32px);max-height:calc(100dvh - 32px);box-shadow:0 18px 80px #0005;overflow:auto}dialog::backdrop{background:#0007;backdrop-filter:blur(3px)}
      .dialog-header{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:20px 22px 14px;position:sticky;top:0;background:var(--card-background-color,#fff);z-index:1}.dialog-header h2{font-size:19px;margin:0;line-height:1.3}.dialog-body{padding:0 22px 20px}.intro{font-size:13px;line-height:1.5;color:var(--secondary-text-color,#687078);margin:0 0 18px}
      .row{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:14px;background:var(--secondary-background-color,#f5f6f7);border-radius:12px;margin-bottom:12px}.row span{font-size:14px;font-weight:600}.row input{width:22px;height:22px;accent-color:var(--primary-color,#03a9f4);cursor:pointer}.row select{min-height:36px;border:1px solid var(--divider-color,#ddd);border-radius:8px;background:var(--card-background-color,#fff);color:inherit;font:inherit;padding:4px 8px}
      .fields{display:grid;grid-template-columns:1fr 1fr;gap:18px 16px;margin-top:18px}.field label{display:block;font-size:13px;font-weight:550;margin-bottom:7px}.input-wrap{display:flex;align-items:center;gap:8px;border:1px solid var(--divider-color,#ddd);border-radius:10px;padding:3px 10px;background:var(--secondary-background-color,#f5f6f7)}.input-wrap input{width:100%;min-width:0;border:0;background:transparent;color:inherit;font:inherit;font-size:17px;padding:9px 0;font-variant-numeric:tabular-nums}.input-wrap span{font-size:12px;color:var(--secondary-text-color,#687078);white-space:nowrap}.hint{font-size:11px;color:var(--secondary-text-color,#687078);line-height:1.5;margin-top:6px}
      .info{font-size:12px;line-height:1.6;margin-top:20px;padding-top:14px;border-top:1px solid var(--divider-color,#ddd);color:var(--secondary-text-color,#687078)}.dialog-footer{display:flex;justify-content:flex-end;gap:10px;padding:14px 22px;background:var(--card-background-color,#fff);border-top:1px solid var(--divider-color,#ddd);position:sticky;bottom:0;z-index:1}.action{min-height:40px;padding:9px 18px;border:1px solid var(--divider-color,#ddd);border-radius:10px;background:transparent;color:inherit;font:inherit;font-size:13px;font-weight:600;cursor:pointer}.primary{background:var(--primary-color,#03a9f4);border-color:var(--primary-color,#03a9f4);color:var(--text-primary-color,#fff)}.feedback{font-size:12px;line-height:1.5;margin-top:14px;min-height:18px}.feedback[data-error=true]{color:var(--error-color,#c64646)}.feedback[data-error=false]{color:var(--success-color,#268b59)}
      @media(max-width:450px){.fields{grid-template-columns:1fr}.batteries .value{font-size:19px}.dialog-header{padding:18px}.dialog-body{padding:0 18px 18px}.dialog-footer{padding:12px 18px}.body{padding:16px}.title{font-size:16px}.header{gap:8px}.brand{width:38px;height:38px}.icon-button{width:36px;height:36px}.value{font-size:21px}.footer{padding:12px 16px}.subtitle{font-size:11px}}
    </style>
    <ha-card><div class="empty" id="empty" hidden></div><div id="content"><div class="body"><div class="header"><div class="brand">${EFS_BOLT}</div><div class="heading"><div class="title" id="title"></div><div class="subtitle" id="subtitle"></div></div><button class="icon-button" id="toggle" aria-pressed="false">${EFS_POWER}</button><button class="icon-button" id="settings" aria-label="${t.settings}" title="${t.settings}">${EFS_GEAR}</button></div>
    <div class="state-line"><span class="badge" id="status">${t.loading}</span><span class="goal" id="goal"></span></div><p class="reason" id="reason"></p>
    <div class="metrics">
      <button type="button" class="metric history" id="price-tile"><div class="label">${t.price}</div><div class="value" id="price"></div><div class="detail" id="price-detail"></div></button>
      <div class="metric"><div class="label">${t.solar}</div><div class="value" id="solar"></div><div class="detail">${t.solarDetail}</div></div>
      <div class="metric"><div class="label">${t.saving}</div><div class="value" id="saving"></div><div class="detail" id="saving-detail"></div></div>
      <div class="metric"><div class="label">${t.grid}</div><div class="value" id="grid"></div><div class="detail" id="grid-detail"></div></div>
      <div class="metric" id="window-tile"><div class="label">${t.window}</div><div class="value window-range" id="window"></div><div class="detail" id="window-detail"></div></div>
      <div class="metric"><div class="label">${t.total}</div><div class="value" id="total"></div><div class="detail" id="total-detail"></div></div>
    </div>
    <div class="batteries" id="batteries"></div><div class="error" id="card-error" role="alert"></div></div><div class="footer"><span id="footer-profile"></span><span id="footer-updated"></span></div></div></ha-card>
    <dialog id="dialog" aria-labelledby="dialog-title"><form id="form"><div class="dialog-header"><h2 id="dialog-title">${t.dialogTitle}</h2><button type="button" class="icon-button" id="close" aria-label="${t.close}">${EFS_CLOSE}</button></div><div class="dialog-body"><p class="intro">${t.intro}</p>
      <label class="row" for="enabled"><span>${t.master}</span><input type="checkbox" id="enabled"></label>
      <label class="row" for="mode"><span>${t.mode}</span><select id="mode">${Object.entries(t.modes).map(([value, label]) => `<option value="${value}">${label}</option>`).join('')}</select></label>
      <div class="fields">${EFS_FIELDS.map(([key, unit]) => `<div class="field"><label for="field-${key}">${t.fields[key][0]}</label><div class="input-wrap"><input id="field-${key}" type="number" inputmode="decimal" required><span>${unit}</span></div><div class="hint">${t.fields[key][1]}</div></div>`).join('')}</div>
      <div class="info" id="info"></div><div class="feedback" id="feedback" role="status" aria-live="polite"></div></div>
      <div class="dialog-footer"><button type="button" class="action" id="cancel">${t.cancel}</button><button type="submit" class="action primary" id="save">${t.save}</button></div></form></dialog>`;
    this._refs = Object.fromEntries([...this.shadowRoot.querySelectorAll('[id]')].map(n => [n.id, n]));
    this._refs.settings.addEventListener('click', () => this._open());
    this._refs.toggle.addEventListener('click', () => this._toggle());
    this._refs['price-tile'].addEventListener('click', () => this._history(this._sources().price_entity));
    for (const id of ['close', 'cancel']) this._refs[id].addEventListener('click', () => this._close());
    this._refs.dialog.addEventListener('cancel', e => { if (this._saving) e.preventDefault(); });
    this._refs.form.addEventListener('submit', e => { e.preventDefault(); this._save(); });
    this._refs.form.addEventListener('input', () => this._feedback(''));
    this._refs.dialog.addEventListener('click', e => {
      const r = this._refs.dialog.getBoundingClientRect();
      if (e.target === this._refs.dialog && (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom)) this._close();
    });
  }

  // Map "domain.translation_key" to entity IDs of this integration's service device.
  _resolve() {
    const all = Object.values(this._hass?.entities || {}).filter(e => e.platform === EFS_DOMAIN);
    let device = this._config.device_id;
    if (!device) {
      const devices = [...new Set(all.map(e => e.device_id).filter(Boolean))];
      if (devices.length !== 1) return { error: devices.length ? 'pickDevice' : 'notFound' };
      device = devices[0];
    }
    const map = {};
    for (const e of all) if (e.device_id === device && e.translation_key) map[`${e.entity_id.split('.')[0]}.${e.translation_key}`] = e.entity_id;
    return map['sensor.status'] ? { map } : { error: 'notFound' };
  }

  _id(key) { return this._entities?.[key]; }
  _state(entityOrKey) { return this._hass?.states?.[this._id(entityOrKey) || entityOrKey]; }
  _number(entityOrKey) {
    const value = this._state(entityOrKey)?.state;
    if (value == null || value === '' || ['unknown', 'unavailable'].includes(value)) return null;
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  }
  _sources() { return this._state('sensor.status')?.attributes || {}; }
  _format(value, digits = 2) {
    return value === null || value === undefined ? '—' : new Intl.NumberFormat(this._language === 'de' ? 'de-DE' : 'en-GB', { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(value);
  }
  _metric(id, value, unit, digits = 2) {
    const el = this._refs[id];
    el.replaceChildren(document.createTextNode(this._format(value, digits)));
    const small = document.createElement('small');
    small.textContent = unit;
    el.append(small);
  }
  _history(entityId) {
    if (!entityId) return;
    this.dispatchEvent(new CustomEvent('hass-more-info', { detail: { entityId, view: 'history' }, bubbles: true, composed: true }));
  }

  _update() {
    if (!this._hass || !this._config || !this._refs) return;
    const t = this._t;
    const resolved = this._resolve();
    this._refs.empty.hidden = !resolved.error;
    this._refs.content.hidden = Boolean(resolved.error);
    if (resolved.error) { this._refs.empty.textContent = t[resolved.error]; return; }
    this._entities = resolved.map;
    const sources = this._sources();
    const batteries = Array.isArray(sources.batteries) ? sources.batteries : [];
    const status = this._state('sensor.status')?.state;
    const master = this._state('switch.master');
    const available = master && !['unknown', 'unavailable'].includes(master.state);
    const on = master?.state === 'on';
    const shadow = this._state('select.mode')?.state === 'shadow';
    const allowed = this._state('binary_sensor.permission')?.state === 'on';
    const session = this._state('binary_sensor.session_active')?.state === 'on';
    const reason = this._state('sensor.reason')?.state;
    const detail = this._state('sensor.reason')?.attributes?.detail;
    const selfPowered = this._state('sensor.reason')?.attributes?.self_powered;

    this._refs.title.textContent = this._config.title || t.title;
    this._refs.subtitle.textContent = shadow ? t.shadowSubtitle : t.subtitle(batteries.length);
    this._refs.subtitle.dataset.shadow = String(shadow);
    const busy = ['charging', 'charge_pending', 'charge_blocked', 'restore_pending', 'recovery_pending', 'recovery_blocked'].includes(status);
    this._refs.status.textContent = !available ? t.unavailable : busy ? t.status[status] : shadow ? t.status.shadow : !on ? t.status.off : allowed ? t.status.allowed : t.status.waiting;
    this._refs.status.dataset.tone = ['charging', 'charge_pending'].includes(status) ? 'good' : !available || ['restore_pending', 'recovery_pending', 'recovery_blocked', 'charge_blocked'].includes(status) || reason === 'protection_mode_required' ? 'warn' : 'neutral';
    this._refs.reason.textContent = !on && !session ? t.masterOff : t.reasons[reason] || (!reason || ['unknown', 'unavailable'].includes(reason) ? t.noPlan : EFS_GENERIC_REASONS.has(reason) ? t.dataMissing + (detail ? ` (${detail.replace(/^\w+: /, '')})` : '') : reason);
    // Shadow plans without Self-powered; say what active mode would still need.
    if (shadow && selfPowered === false) this._refs.reason.textContent += ' ' + t.selfPoweredHint;
    this._refs.toggle.setAttribute('aria-pressed', String(on));
    this._refs.toggle.disabled = !available || this._toggling;
    this._refs.toggle.title = on ? t.toggleOff : t.toggleOn;
    this._refs.toggle.setAttribute('aria-label', this._refs.toggle.title);

    const target = this._number('sensor.target_soc'), grid = this._number('sensor.grid_kwh');
    this._refs.goal.textContent = target !== null && grid !== null && grid > 0 ? t.goal(this._format(target, 0)) : t.noGoal;

    const priceState = this._state(sources.price_entity);
    let price = this._number(sources.price_entity);
    if (price !== null && /eur|€/i.test(priceState?.attributes?.unit_of_measurement || '')) price *= 100;
    const ceiling = this._number('number.charge_ceiling_ct'), saving = this._number('sensor.net_saving_ct'), margin = this._number('number.minimum_net_saving_ct');
    this._metric('price', price, 'ct/kWh');
    this._refs.price.dataset.tone = price !== null && ceiling !== null && price > ceiling ? 'bad' : 'neutral';
    this._refs['price-detail'].textContent = t.priceDetail(this._format(ceiling, 1), this._format(this._number('sensor.price_advantage_percent'), 1), this._format(this._number('number.minimum_price_advantage'), 0));
    this._refs['price-tile'].title = `${t.price} – ${t.showHistory}`;
    this._metric('solar', this._number('sensor.solar_surplus_kwh'), 'kWh');
    this._metric('saving', saving, 'ct/kWh');
    this._refs.saving.dataset.tone = saving !== null && margin !== null && saving >= margin ? 'good' : saving !== null && saving < 0 ? 'bad' : 'neutral';
    this._refs['saving-detail'].textContent = t.savingDetail(this._format(margin, 1));
    this._metric('grid', grid, 'kWh');
    this._refs['grid-detail'].textContent = t.gridDetail(this._format(this._number('sensor.missing_energy_kwh')), this._format(this._number('sensor.corrected_forecast_kwh')));

    const timeZone = this._hass.config?.time_zone || 'Europe/Berlin';
    const selected = efsSelectedWindow(this._state(sources.price_window_entity), t, timeZone);
    this._refs.window.replaceChildren();
    if (selected.window) {
      for (const text of [selected.window.start + '–', selected.window.end]) {
        const span = document.createElement('span');
        span.textContent = text;
        this._refs.window.append(span);
      }
      this._refs['window-detail'].textContent = selected.window.detail;
    } else {
      this._refs.window.textContent = '—';
      this._refs['window-detail'].textContent = selected.available ? t.noWindow : t.windowUnavailable;
    }
    this._refs['window-tile'].setAttribute('aria-label', `${t.window}: ${this._refs.window.textContent}. ${this._refs['window-detail'].textContent}`);

    this._updateBatteries(batteries);
    const fallback = this._number('number.capacity_kwh');
    let stored = 0, capacity = 0, complete = batteries.length > 0;
    batteries.forEach((battery, index) => {
      const soc = this._number(battery.soc_entity), kwh = battery.capacity_kwh ?? fallback;
      if (soc === null || !kwh) complete = false; else { stored += soc * kwh; capacity += kwh; }
      this._refs[`soc-${index}`].replaceChildren(document.createTextNode(this._format(soc, 1)));
      const unit = document.createElement('small');
      unit.textContent = '%';
      this._refs[`soc-${index}`].append(unit);
      this._refs[`fill-${index}`].style.width = (soc === null ? 0 : Math.min(100, Math.max(0, soc))) + '%';
      this._refs[`reserve-${index}`].textContent = `${t.reserve} ${this._format(this._number(battery.reserve_entity), 0)} %`;
    });
    this._metric('total', complete && capacity ? stored / capacity : null, '%', 1);
    this._refs['total-detail'].textContent = complete ? t.totalDetail : t.totalUnavailable;

    this._refs['footer-profile'].textContent = t.footer(this._format(this._number('sensor.profile_samples'), 0), this._format(this._number('sensor.pv_correction')));
    const planned = Date.parse(this._state('sensor.plan_updated')?.state);
    this._refs['footer-updated'].textContent = Number.isFinite(planned)
      ? t.planned(new Intl.DateTimeFormat('de-DE', { hour: '2-digit', minute: '2-digit', timeZone }).format(new Date(planned)))
      : t.notPlanned;
  }

  // Rebuild battery tiles only when the configured batteries change.
  _updateBatteries(batteries) {
    const signature = JSON.stringify(batteries.map(b => [b.name, b.soc_entity, b.reserve_entity]));
    if (signature === this._batterySignature) return;
    this._batterySignature = signature;
    const container = this._refs.batteries;
    container.style.setProperty('--columns', String(Math.min(Math.max(batteries.length, 1), 3)));
    container.replaceChildren();
    batteries.forEach((battery, index) => {
      const tile = document.createElement('button');
      tile.type = 'button';
      tile.className = 'metric history';
      tile.title = `${battery.name} – ${this._t.showHistory}`;
      tile.setAttribute('aria-label', tile.title);
      tile.addEventListener('click', () => this._history(battery.soc_entity));
      tile.innerHTML = `<div class="label"></div><div class="value" id="soc-${index}"></div><div class="track"><div class="fill" id="fill-${index}"></div></div><div class="detail" id="reserve-${index}"></div>`;
      tile.querySelector('.label').textContent = battery.name;
      container.append(tile);
      for (const id of [`soc-${index}`, `fill-${index}`, `reserve-${index}`]) this._refs[id] = tile.querySelector('#' + id);
    });
  }

  _feedback(message, error = false) {
    this._refs.feedback.textContent = message;
    this._refs.feedback.dataset.error = String(error);
  }

  _open() {
    if (!this._hass || this._saving || !this._entities) return;
    const t = this._t;
    this._snapshot = {};
    for (const [key, , scale] of EFS_FIELDS) {
      const id = this._id('number.' + key), state = this._state(id), value = this._number(id), input = this._refs[`field-${key}`];
      if (value === null) { this._refs['card-error'].textContent = t.settingsUnavailable(id || key); return; }
      const scaled = v => String(+(Number(v) * scale).toFixed(6));
      input.min = scaled(state.attributes.min);
      input.max = scaled(state.attributes.max);
      input.step = scaled(state.attributes.step || 0.01);
      input.value = scaled(value);
      this._snapshot[key] = value;
    }
    const enabled = this._state('switch.master')?.state, mode = this._state('select.mode')?.state;
    if (!['on', 'off'].includes(enabled) || !['shadow', 'active'].includes(mode)) { this._refs['card-error'].textContent = t.settingsUnavailable('switch/select'); return; }
    this._snapshot.enabled = enabled === 'on';
    this._snapshot.mode = mode;
    this._refs.enabled.checked = this._snapshot.enabled;
    this._refs.mode.value = mode;
    this._refs.info.textContent = t.info(this._format(this._number('sensor.pv_correction')));
    this._refs['card-error'].textContent = '';
    this._feedback('');
    this._refs.cancel.textContent = t.cancel;
    this._refs.dialog.showModal();
    this._refs.enabled.focus();
  }

  _close() { if (!this._saving) this._refs.dialog.close(); }

  // A service acknowledgement is not enough: read the state back from Home Assistant.
  async _confirmed(domain, service, entity, data, expected) {
    await this._hass.callService(domain, service, { entity_id: entity, ...data });
    const readback = await this._hass.callApi('GET', 'states/' + entity);
    const ok = typeof expected === 'number'
      ? Number.isFinite(Number(readback.state)) && Math.abs(Number(readback.state) - expected) <= 1e-7
      : readback.state === expected;
    if (!ok) throw new Error(this._t.notConfirmed(entity));
  }

  async _toggle() {
    const id = this._id('switch.master'), current = this._state(id)?.state;
    if (this._toggling || !['on', 'off'].includes(current)) return;
    this._toggling = true;
    this._refs['card-error'].textContent = '';
    this._update();
    try {
      await this._confirmed('switch', current === 'on' ? 'turn_off' : 'turn_on', id, {}, current === 'on' ? 'off' : 'on');
    } catch (e) {
      this._refs['card-error'].textContent = e.message || String(e);
    } finally {
      this._toggling = false;
      this._update();
    }
  }

  async _save() {
    const t = this._t;
    if (this._saving || !this._refs.form.reportValidity()) return;
    const edits = [];
    for (const [key, , scale] of EFS_FIELDS) {
      const value = Number(this._refs[`field-${key}`].value) / scale;
      if (!Number.isFinite(value)) { this._feedback(t.invalidNumbers, true); return; }
      if (Math.abs(value - this._snapshot[key]) > 1e-9) {
        if (this._number('number.' + key) !== this._snapshot[key]) { this._feedback(t.changedOutside, true); return; }
        edits.push([key, +value.toFixed(6)]);
      }
    }
    const enabled = this._refs.enabled.checked, mode = this._refs.mode.value;
    if ((this._state('switch.master')?.state === 'on') !== this._snapshot.enabled || this._state('select.mode')?.state !== this._snapshot.mode) {
      this._feedback(t.changedOutside, true);
      return;
    }
    this._saving = true;
    let applied = 0;
    this._refs.save.textContent = t.savingProgress;
    this._feedback('');
    this.shadowRoot.querySelectorAll('dialog button,dialog input,dialog select').forEach(e => { e.disabled = true; });
    try {
      // Stopping comes first and starting last, so no intermediate state widens permission.
      if (enabled !== this._snapshot.enabled && !enabled) { await this._confirmed('switch', 'turn_off', this._id('switch.master'), {}, 'off'); this._snapshot.enabled = false; applied++; }
      if (mode !== this._snapshot.mode && mode === 'shadow') { await this._confirmed('select', 'select_option', this._id('select.mode'), { option: mode }, mode); this._snapshot.mode = mode; applied++; }
      for (const [key, value] of edits) { await this._confirmed('number', 'set_value', this._id('number.' + key), { value }, value); this._snapshot[key] = value; applied++; }
      if (mode !== this._snapshot.mode) { await this._confirmed('select', 'select_option', this._id('select.mode'), { option: mode }, mode); this._snapshot.mode = mode; applied++; }
      if (enabled !== this._snapshot.enabled) { await this._confirmed('switch', 'turn_on', this._id('switch.master'), {}, 'on'); this._snapshot.enabled = true; applied++; }
      this._feedback(applied ? t.saved : t.noChanges);
      this._refs.cancel.textContent = t.close;
    } catch (e) {
      this._feedback((applied ? t.partlyApplied(applied) : '') + (e.message || String(e)), true);
    } finally {
      this._saving = false;
      this._refs.save.textContent = t.save;
      this.shadowRoot.querySelectorAll('dialog button,dialog input,dialog select').forEach(e => { e.disabled = false; });
      this._update();
    }
  }
}

if (!customElements.get(EFS_CARD)) customElements.define(EFS_CARD, EcoFlowSmartChargeCard);
window.customCards = window.customCards || [];
if (!window.customCards.some(c => c.type === EFS_CARD)) {
  window.customCards.push({
    type: EFS_CARD,
    name: 'EcoFlow Smart Charge',
    description: 'Solar- und preisgeführte Akku-Ladung der Integration EcoFlow Smart Charge.',
    preview: true,
    documentationURL: 'https://github.com/mischiminator/ha-ecoflow-smart-charge',
  });
}
