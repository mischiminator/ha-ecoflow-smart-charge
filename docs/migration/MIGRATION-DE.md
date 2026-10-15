# Sichere Migration und Rollback

Diese Anleitung beschreibt den verpflichtenden Ablauf für eine spätere freigegebene Version. Der aktuelle parallele Entwicklungsstand ist keine Installations- oder Cutover-Freigabe. Die Integrationsabnahme muss Import, Vergleichsprotokoll, exklusive Recovery und Kartenanpassung gegen echten Code prüfen. Fehlt ein Schritt in der ausgelieferten Oberfläche, STOPP: nicht durch versteckte Optionen, direkte Serviceaufrufe oder Speichermanipulation umgehen.

## 1. Privates Übergabeprotokoll und Backup

- HA-Vollbackup über die unterstützte Backup-Funktion erstellen und Wiederherstellungsweg kennen. Zusätzlich die vier relevanten Automationskonfigurationen, Parameter-/Lern-/Sitzungswerte und beide betroffenen Karteninstanzen über unterstützte UI/API sichern. Ein API-Snapshot ist KEIN HA-Vollbackup.
- Backup-Vollständigkeit und Prüfsumme lokal verifizieren. Referenzwerte und Zeitstempel privat aufbewahren, nie ins Git-Repo oder in öffentliche Issues kopieren.
- Die vier Rollen getrennt notieren: Preisplanung, Reserve-Steuerung, tägliche PV-Probe und PV-Lernen. Die tatsächlich befehlsschreibenden Automationen anhand ihres Inhalts bestimmen. Nicht pauschal alle EcoFlow-Automationen sperren: Verbindungs-Watchdogs gehören nicht zum Preisladeregler.
- Bestehende Einstellungen vollständig erfassen: Master, Preisobergrenze, Gesamtwirkungsgrad, Verschleiß, Mindestnettoersparnis, Mindestpreisvorteil, Kapazität pro Batterie; nicht auf Generator- oder Neuinstallationswerte zurücksetzen. Insbesondere ist 20% nur der Neuinstallationsdefault.
- Je Batterieslot Originalreserve, SOC, Reserve-Number, Mode-Select, Self-powered-Switch, Lade-/Entlade-Energiequelle und deren Zuordnung festhalten. Reihenfolge muss in allen Listen identisch sein. Werte nie aus einer temporären 100%-Reserve als vermeintliche Originalwerte neu erfassen.
- Lernzustand vollständig erfassen: Korrekturfaktor, maximal 14 gültige Ratios, Probe-Tag/-kWh, ausgewerteter Tag und Volladungsmarker. Eine unevaluierte Probe darf durch einen Neustart nicht verloren gehen.

## 2. In Shadow konfigurieren, niemals Geräte testen

Legacy bleibt zunächst zuständig; der native Eintrag ist ausschließlich in Shadow. Auch Recovery, Restart und Unload dürfen in Shadow keinerlei Geräte-Service senden. Keine Reserve erhöhen, keinen künstlichen Volladezyklus starten. Konfiguration wählt existierende Entitäten, keine neuen Cloud-Zugangsdaten.

Genau den vom Betreiber verbindlich festgelegten Netz-Saldo-Zähler verwenden. Den bisherigen anderen Zähler NICHT als Fallback auswählen. Dessen Historie nicht mit der neuen vermischen und fehlende Daten nicht erfinden. Statistik-ID, Vorzeichen, Wh/kWh-Einheit, Zählerresets und ausreichende Recorder-Historie der neuen Quelle unabhängig prüfen. Fehlende Historie bedeutet Shadow beibehalten, bis reale valide Daten vorliegen.

Erforderlich sind die letzten 14 vollständig abgeschlossenen lokalen Tage, heute ausgeschlossen; mindestens drei valide Messungen für jede der 24 Stundenklassen. UTC-Zuordnung und lokale 23-/25-Stunden-Tage müssen korrekt sein. Die Rekonstruktion verwendet genau die ausgewählte Netzquelle plus PV minus drei Ladeenergien plus drei Entladeenergien. Signierter Export ist nicht automatisch ein negativer Haushaltsverbrauch.

Preisreihe des explizit ausgewählten Tarifs/Haushalts heute und veröffentlichter Folgetag, aktueller Preis und Bestpreisfenster prüfen. Keine nicht veröffentlichten Preise ergänzen. PV heute verbleibend, morgen gesamt, Sonnenzustand sowie alle drei Schutzmodi prüfen. Die Integration darf Schutzmodi nicht selbst einschalten. Frische, Einheiten und unbekannte Zustände müssen tatsächlich geprüft werden, nicht durch manuelles Setzen eines Statussensors simuliert.

## 3. Unterstützter Import: Vorschau vor Persistenz

Nur den abschließend dokumentierten, versionierten Import-Flow/-Dienst der Integration verwenden. Ein Rohsnapshot oder ein HA-Store-Dokument ist kein Importformat. Der aktuelle Adapter stellt `import_state` mit `payload` und standardmäßig `apply:false` bereit; [ACTIONS-IMPORT.md](ACTIONS-IMPORT.md) erläutert den exakt geprüften Umschlag mit rein synthetischem inaktivem Beispiel. `docs/adapter/ENTITY-SERVICE-CONTRACT.md` bleibt die Schnittstellenquelle; abschließende Integrationsabnahme ist Pflicht. Wenn der validierte Import in der installierten Version nicht verfügbar ist, ist Migration gesperrt.

1. In Shadow zuerst Vorschau erzeugen. Quelle, Schemaversion, Slot-Reihenfolge und alle Werte/Ranges prüfen. Nicht-endliche Zahlen, boolesche Zahlenersatzwerte, ungültige Datumsfelder, doppelte Reserven und fehlende Einzelwerte müssen abgewiesen werden.
2. Vorschau mit dem privaten Übergabeprotokoll vergleichen: kein Default darf einen importierten Wert ersetzen. Journal und unabhängiger Volladungsmarker bleiben getrennt. Keine vorhandene native Sitzung überschreiben.
3. Bei einer laufenden Legacy-Sitzung NICHT parallel native Recovery starten und NICHT den alten Writer abschalten, bevor der Zuständigkeitswechsel sicher geplant ist. Bevorzugt Legacy unter dessen exklusiver Zuständigkeit beenden lassen und alle Originalreserven zurücklesen. Falls das nicht möglich ist, braucht es einen gesondert freigegebenen Transfer der vollständigen Originalwerte und Writer-Zuordnung unter Sperre beider Ladepfade; unvollständige Originalwerte sind ein Blocker.
4. Erst nach geprüfter Vorschau Import bestätigen. Ein Import darf nur integrationseigene validierte Daten über HA-Manager-/Store-APIs speichern, niemals Geräte kommandieren. Einstellungen, Lernwerte, Marker und ggf. Sitzung müssen nach Reload über die unterstützte Oberfläche wieder lesbar sein.
5. Ein importierter offener Vorgang bleibt `recovery_pending`/gesperrt. Shadow stellt ihn nicht automatisch wieder her. Explizit freigegebene exklusive Recovery außerhalb von Shadow ist vor Cutover erforderlich (Abschnitt 6).

Direkte Änderungen an `.storage`, RestoreEntity-Daten oder fremden Config Entries sind in keinem Schritt zulässig. Kein Copy/Paste privater Dumps ins Repository.

## 4. Überprüfbare Shadow-Abnahme

Private Vergleichstabelle über mehrere tatsächlich beobachtete Preis-/PV-Zyklen führen: Zeit, Quellenfrische, Profilvalidität, Solartag, Ladebedarf, Solarüberschuss, vermiedener Bezugspreis, ungerundeter Preisvorteil, Nettoersparnis, Erlaubnis und Sperrgrund. Wechsel des Bestpreisfensters, Preise ohne Folgetag, Datenlücken und Neustart abdecken; Grenzfälle ohne Hardware über Tests nachweisen.

Entscheidungsabweichungen aufgrund des verpflichtenden neuen Netz-Zählers separat begründen. Ein abweichender, aber korrekter neuer Messwert ist kein Grund, auf die falsche Legacy-Quelle zurückzugehen. Eine rein identische Anzeige ist kein Paritätsnachweis.

HA-Traces/Testinstrumentierung und Service-/Geräteprotokolle müssen null native Gerätebefehle während ALLER Shadow-Routen belegen. Das alleinige Ausbleiben sichtbarer Reserveänderungen reicht nicht: ein geschickter Serviceaufruf kann denselben Wert schreiben. Erfolgreichen Vergleich mit identifizierbarer Konfiguration protokollieren; eine nicht validierte oder veraltete Vergleichsfreigabe darf nicht genügen.

## 5. Cutover-Gate: alles gleichzeitig erfüllt

- Vollständige Code-/Testabnahme einschließlich Crash-, Readback-, Shadow-, Recorder-/DST- und Importfällen; keine offenen Safety-Gates.
- Betreiber bestätigt ausdrücklich ein beaufsichtigtes Übernahmefenster. Kein automatischer Wechsel durch Installation, Options-Reload, Master-Schalter oder Import.
- Frisches privates Backup von Automationen, Werten und beiden Karten; klarer Rollback-Zuständiger.
- Quellen aktuell/gültig, echte veröffentlichte Preisreihe, valide Historie, Schutzmodi aller drei Geräte korrekt; keine offene oder korrupte Sitzung.
- Jede Originalreserve separat frisch zurückgelesen und dem richtigen Slot zugeordnet. Eine Service-Quittung oder ein alter identischer State genügt nicht.
- Nur ausdrücklich erfasste alte Preisladungs-Writer über unterstützte HA UI/API ausschalten und deren Zustand als OFF zurücklesen. Fehlend/unknown/unavailable ist NICHT OFF. Keine automatische Abschaltung fremder Automationen durch die neue Integration.
- Probe-/Lern-Automationen bewusst stilllegen bzw. eindeutig in Verantwortung trennen, damit keine doppelten Lernschreiber entstehen. Verbindungs-Watchdogs unverändert lassen.
- Nach jeder Konfigurations-/Mappingänderung Vergleich und Reserveprüfung erneuern. Unbekannte weitere externe Writer können softwareseitig nicht vollständig ausgeschlossen werden; Betreiber muss deren Abwesenheit prüfen. Konfliktcheck vor JEDEM Gerätebefehl bleibt Pflicht.

Erst dann den endgültigen entry-zielbaren `request_cutover`-Dienst über HA ausführen. Freigabe ist kein Erfolg: Modus und Sperrgründe zurücklesen. Erste reale Aktion nur bei natürlich erfüllten Gates beaufsichtigen; keine künstliche Preislücke/Reserveänderung erzwingen. Bei Teilfehler, unerwartetem Writer oder fehlendem Readback: neue Ladung sperren, Journal erhalten, Recovery/Rollback.

## 6. Stop, Recovery und Rollback in richtiger Reihenfolge

1. Neue Ladeanforderungen sperren. Nicht vorschnell Integration löschen, HACS deinstallieren, Store entfernen oder Legacy einschalten. Originalwerte und Journal müssen erhalten bleiben.
2. Bei aktiver Zuständigkeit den unterstützten Stop-/Master-aus-Pfad verwenden. Er muss Starts verhindern und Rückstellung unter exklusiver aktiver Zuständigkeit anstoßen. Liegt die Integration bereits in Shadow, darf sie NICHT selbst restaurieren: für eine offene Sitzung braucht es ausdrückliche Freigabe der exklusiven Recovery außerhalb von Shadow.
3. Vor Recovery erneut alte Writer OFF und bekannte unveränderte Slot-/Originalreserve-Zuordnung prüfen. Preis-/Ladefreigabefehler blockieren neue Ladung, dürfen aber sichere Rückstellung der bekannten Originalwerte nicht verhindern. Die Integration wechselt dafür nicht den Gerätebetriebsmodus.
4. `confirm_recovery` ausschließlich auf den richtigen Integrationseintrag richten und die endgültigen Bestätigungsanforderungen beachten. Dienst-/HTTP-Erfolg ist keine Wiederherstellung. Alle drei tatsächlichen Reserve-Number unabhängig frisch zurücklesen; jeder muss seinem individuellen gesicherten Originalwert entsprechen. Nur fehlgeschlagene/unbestätigte Slots erneut versuchen; nie Originalwerte neu aus 100% erfassen.
5. Bei Gerät offline, Timeout, altem State, beschädigtem Journal oder Mappingwechsel bleibt Recovery offen/gesperrt. Beide Lade-Writer aus lassen, Diagnose privat prüfen und mit den gesicherten Originalwerten eine beaufsichtigte Wiederherstellung planen. Niemals `restored` manuell setzen oder Journal löschen. Falls die Integration nicht läuft: HA-Backup/unterstützte Wiederherstellung oder dokumentierte Bedienung über die vorhandenen Geräte-Entities durch den Betreiber, mit beiden Reglern gesperrt und anschließendem Einzel-Readback; kein blindes Raten.
6. Erst nach ALLEN bestätigten Rückstellungen und sauberem inaktivem Journal zurück in Shadow wechseln, Timer/Listener der neuen aktiven Steuerung stoppen bzw. Eintrag sicher entladen. Ein fehlgeschlagener Unload ist kein Erfolg und kein Beweis für entfallene Writer.
7. Exakte gesicherte Legacy-Konfigurationen über unterstützte UI/API wiederherstellen, falls geändert. Nur zuvor aktive Preisladungs-Automationen mit geklärter Zuständigkeit wieder einschalten und ihren Zustand zurücklesen. Nicht blind vier zuvor deaktivierte Automationen aktivieren. Bei Rückkehr vollständig zu Legacy die vier ursprünglichen Rollen wie zuvor herstellen; Watchdogs nicht ändern.
8. Geänderte Karteninstanzen und Ressource auf die gesicherte Version zurückstellen; Einstellungen und Werte nochmals prüfen. HACS erst nach bestätigter sicherer Entladung entfernen. Privates Protokoll und Backups behalten.

Nach Crash/Restart niemals automatisch wieder aktiv laden. Offener Store bedeutet Recovery, nicht eine neue Sitzung. Ein Volladungsmarker bleibt nach Session-Löschung erhalten und verhindert sofortiges Nachladen bei geringer Entladung am selben Solartag.

## 7. Karte

Siehe [CARD-COMPATIBILITY.md](CARD-COMPATIBILITY.md). Kein reines Entity-Remapping auf native Switches/Numbers als kompatibel ausgeben. Native Standardkarten sind der sichere Übergang; bestehendes Dashboard und Ressource unverändert aufbewahren, bis der separate opt-in Kartenadapter fertig geprüft ist.

## Independent commissioning is an external gate

`record_shadow_comparison` checks operator-supplied values against native output;
it cannot authenticate their origin or prove legacy parity. Copying native values
back is NOT independent evidence. Before activation, a separately authorized
operator must retain a same-input legacy/reference comparison, required meter
history/unit/sign/reset checks and supervised individual device readback and
rollback evidence outside this public repository. Unresolved or differing results
block activation. This work has NOT performed those physical checks.

`request_cutover` now requires BOTH `confirmed: true` and
`commissioning_confirmed: true`. The latter is an explicit human attestation of
that external gate, not an automated test result or a safe default. Missing/false
attestation is rejected; even an attested comparison expires after 20 minutes and
is rejected if any recorded value differs from the refreshed native plan. No
service automatically authorizes itself from native output. All writer, reserve,
journal and freshness checks remain mandatory. Restart/reload remains shadow.
